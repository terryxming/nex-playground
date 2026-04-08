"""
translate_pr_titles.py
1. 从 HTML 里提取 PR 文章标题
2. 用 deep_translator 翻译成中文
3. 在每个 <span class="title-text"> 后插入 <div class="pr-title-zh">中文</div>
4. 把 .pr-title-zh CSS 注入 HTML
可重复运行：已有翻译的跳过
"""
import re, json, time, os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from deep_translator import GoogleTranslator

HTML_FILE = 'nex_playground_pr_research_v2.html'
CACHE_FILE = 'pr_titles_cache.json'

with open(HTML_FILE, encoding='utf-8') as f:
    html = f.read()

# 加载缓存
cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, encoding='utf-8') as f:
        cache = json.load(f)

# 匹配所有 title-text span（标题可能含 HTML 实体，用宽松匹配）
PATTERN = re.compile(
    r'(<span class="title-text"><a [^>]+>)(.*?)(</a></span>)',
    re.DOTALL
)

matches = PATTERN.findall(html)
print(f'找到标题: {len(matches)} 条  已缓存: {len(cache)} 条')

# 提取需翻译的（以原始英文标题为 key）
to_translate = []
for open_tag, title_html, close_tag in matches:
    title_text = re.sub(r'<[^>]+>', '', title_html).strip()  # 去掉可能的内嵌标签
    if title_text and title_text not in cache:
        to_translate.append(title_text)

# 去重
to_translate = list(dict.fromkeys(to_translate))
print(f'需翻译: {len(to_translate)} 条')

if to_translate:
    translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate_one(text):
        return translator.translate(text[:500])

    success = 0
    for i, title in enumerate(to_translate):
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(translate_one, title)
                result = future.result(timeout=8)
            cache[title] = result or ''
            success += 1
            try:
                print(f'  [{i+1}/{len(to_translate)}] {title[:50]} -> {result[:40]}')
            except UnicodeEncodeError:
                print(f'  [{i+1}/{len(to_translate)}] OK (含特殊字符)')
        except FuturesTimeout:
            print(f'  [{i+1}/{len(to_translate)}] 超时跳过')
            cache[title] = ''
            time.sleep(2)
        except Exception as e:
            print(f'  [{i+1}/{len(to_translate)}] 失败: {e}')
            cache[title] = ''
            time.sleep(1)

        if (i + 1) % 20 == 0:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            print('  -- 已保存进度 --')

        time.sleep(0.4)

    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f'\n翻译完成: {success} / {len(to_translate)} 条')

# ---- 把中文注入 HTML ----
# 先移除已有的 pr-title-zh div（防止重复注入）
html = re.sub(r'\s*<div class="pr-title-zh">[^<]*</div>', '', html)

def replace_title(m):
    open_tag, title_html, close_tag = m.group(1), m.group(2), m.group(3)
    title_text = re.sub(r'<[^>]+>', '', title_html).strip()
    zh = cache.get(title_text, '')
    zh_div = f'\n          <div class="pr-title-zh">{zh}</div>' if zh else ''
    return f'{open_tag}{title_html}{close_tag}{zh_div}'

html = PATTERN.sub(replace_title, html)

# ---- 注入 CSS（在现有 PR 样式区域或 </style> 前）----
PR_ZH_CSS = '  .pr-title-zh { font-size: 12px; color: #666; margin-top: 3px; line-height: 1.4; }'
if '.pr-title-zh' not in html:
    # 插在 .title { 样式之后，或 </style> 前
    if '.title {' in html or '.title{' in html:
        html = re.sub(r'(\.title\s*\{[^}]+\})', r'\1\n' + PR_ZH_CSS, html, count=1)
    else:
        html = html.replace('</style>', PR_ZH_CSS + '\n</style>', 1)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

# ---- 验证 ----
injected = len(re.findall(r'class="pr-title-zh"', html))
print(f'\nHTML 已更新: 注入 {injected} 条中文标题')
