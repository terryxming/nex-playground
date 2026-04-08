"""
使用 Gemini API (gemini-2.5-flash-lite) 对 comments/*.json 中的评论进行中文翻译
翻译结果写入每条评论的 text_zh 字段，缓存保存到 gemini_translation_cache.json
"""

import json
import glob
import os
import sys
import time
import re

sys.stdout.reconfigure(encoding="utf-8")

from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash-lite"
WRONG_URL_MARKER = "7517426238970006839"
CACHE_FILE = "gemini_translation_cache.json"
BATCH_SIZE = 50  # 每批翻译条数

client = genai.Client(api_key=GEMINI_API_KEY)

# ─── 加载缓存 ────────────────────────────────────────────────────────────────

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = json.load(f)
    print(f"加载翻译缓存：{len(cache)} 条")
else:
    cache = {}
    print("无缓存，从头开始")

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# ─── 翻译函数 ─────────────────────────────────────────────────────────────────

def translate_batch(texts):
    """批量翻译，返回 {原文: 译文} dict"""
    input_json = json.dumps(texts, ensure_ascii=False)
    prompt = (
        "将以下英文 TikTok 评论翻译成中文，保持口语化自然风格，"
        "输出纯 JSON 数组，不要任何其他内容、不要 markdown 代码块：\n\n"
        f"输入：\n{input_json}\n\n"
        "要求：\n"
        "- 输出一个 JSON 数组，长度与输入完全一致\n"
        "- 每个元素是对应评论的中文翻译\n"
        "- 保持口语化，不要过于正式\n"
        "- emoji 和特殊符号保留原样\n"
        "- 只输出 JSON 数组，不要解释"
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            text = response.text.strip()
            # 去掉可能的 markdown 代码块
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            translations = json.loads(text)
            if isinstance(translations, list) and len(translations) == len(texts):
                return dict(zip(texts, translations))
            print(f"  ⚠ 数量不匹配 ({len(translations)} vs {len(texts)})，重试...")
        except Exception as e:
            wait = 2 ** attempt
            print(f"  失败: {e}，等 {wait}s 重试 ({attempt+1}/3)...")
            time.sleep(wait)

    # 全部失败则返回原文（不丢数据）
    print("  ⚠ 翻译失败，该批保留原文")
    return {t: t for t in texts}

# ─── 收集需要翻译的文本 ──────────────────────────────────────────────────────

print("\n扫描评论文件...")
files = sorted(glob.glob("comments/*.json"))
valid_files = []   # [(fpath, data), ...]
all_texts = set()

for fpath in files:
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        continue
    url = data[0].get("videoWebUrl", "")
    if not url or WRONG_URL_MARKER in url:
        continue
    valid_files.append((fpath, data))
    for c in data:
        t = c.get("text", "").strip()
        if t:
            all_texts.add(t)

print(f"有效文件：{len(valid_files)} 个 | 唯一评论文本：{len(all_texts)} 条")

to_translate = [t for t in all_texts if t not in cache]
print(f"已缓存：{len(cache)} 条 | 需要新翻译：{len(to_translate)} 条")

# ─── 批量翻译 ─────────────────────────────────────────────────────────────────

if to_translate:
    batches = [to_translate[i:i + BATCH_SIZE] for i in range(0, len(to_translate), BATCH_SIZE)]
    print(f"\n开始翻译，共 {len(batches)} 批（每批 {BATCH_SIZE} 条）...\n")
    start = time.time()

    for i, batch in enumerate(batches):
        print(f"  批次 {i+1}/{len(batches)} ({len(batch)} 条)...", end=" ", flush=True)
        result = translate_batch(batch)
        cache.update(result)
        elapsed = int(time.time() - start)
        done = sum(len(b) for b in batches[:i+1])
        print(f"✓  总进度 {done}/{len(to_translate)} | 已用 {elapsed}s")

        # 每 5 批保存一次缓存
        if (i + 1) % 5 == 0:
            save_cache()

        # 避免触发限速
        if i < len(batches) - 1:
            time.sleep(0.3)

    save_cache()
    print(f"\n翻译完成！缓存共 {len(cache)} 条")
else:
    print("全部命中缓存，无需调用 API")

# ─── 写回评论文件 ─────────────────────────────────────────────────────────────

print("\n将 text_zh 写入评论文件...")
updated_files = 0
updated_comments = 0
skipped_comments = 0

for fpath, data in valid_files:
    changed = False
    for c in data:
        t = c.get("text", "").strip()
        if not t:
            continue
        if "text_zh" in c:
            skipped_comments += 1
            continue
        if t in cache:
            c["text_zh"] = cache[t]
            changed = True
            updated_comments += 1

    if changed:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        updated_files += 1

print(f"已更新 {updated_files} 个文件")
print(f"新增 text_zh：{updated_comments} 条 | 已有 text_zh 跳过：{skipped_comments} 条")
print("\n完成！")
