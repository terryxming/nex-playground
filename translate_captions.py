"""
批量翻译 TikTok 视频文案（非标签部分）→ 中文
结果缓存到 translations_cache.json，重复运行不重复请求
"""
import json, re, time, os

with open('tiktok_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)

# 加载已有缓存
cache_file = 'translations_cache.json'
if os.path.exists(cache_file):
    with open(cache_file, encoding='utf-8') as f:
        cache = json.load(f)
else:
    cache = {}

def strip_hashtags(text):
    """移除 #标签，保留正文"""
    cleaned = re.sub(r'#\S+', '', text or '').strip()
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned

# 收集需要翻译的文本
to_translate = {}
for v in videos:
    vid = v.get('id')
    text = strip_hashtags(v.get('text', ''))
    if text and vid not in cache:
        to_translate[vid] = text

print(f'已缓存: {len(cache)}  待翻译: {len(to_translate)}')

if to_translate:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='auto', target='zh-CN')

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    def translate_one(text):
        return translator.translate(text[:500])

    items = list(to_translate.items())
    success = 0
    for i, (vid, text) in enumerate(items):
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(translate_one, text)
                result = future.result(timeout=8)
            cache[vid] = result  # 先存，再打印，print 失败不影响缓存
            success += 1
            try:
                print(f'  [{i+1}/{len(items)}] OK: {text[:40]} → {result[:40]}')
            except UnicodeEncodeError:
                print(f'  [{i+1}/{len(items)}] OK (含特殊字符)')
        except FuturesTimeout:
            print(f'  [{i+1}/{len(items)}] 超时跳过')
            cache[vid] = ''
            time.sleep(2)
        except Exception as e:
            try:
                print(f'  [{i+1}/{len(items)}] 失败: {e}')
            except Exception:
                print(f'  [{i+1}/{len(items)}] 失败')
            cache[vid] = ''
            time.sleep(1)

        # 每10条保存一次
        if (i + 1) % 10 == 0:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

        time.sleep(0.4)

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f'\n完成！成功翻译 {success} / {len(items)} 条')
else:
    print('全部已有缓存，无需重新翻译')
