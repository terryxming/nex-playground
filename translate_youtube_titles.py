"""
translate_youtube_titles.py
用 deep_translator (免费 Google 翻译) 把 YouTube 标题翻译成中文
结果写入 youtube_nex_videos.json 的 zh 字段
已有 zh 的条目跳过，可重复运行
"""
import json, time, os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from deep_translator import GoogleTranslator

JSON_FILE = 'youtube_nex_videos.json'

with open(JSON_FILE, encoding='utf-8') as f:
    videos = json.load(f)

to_translate = [(i, v) for i, v in enumerate(videos) if not v.get('zh')]
print(f'已有翻译: {len(videos) - len(to_translate)}  待翻译: {len(to_translate)}')

if not to_translate:
    print('全部已有缓存，无需重新翻译')
else:
    translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate_one(text):
        return translator.translate(text[:500])

    success = 0
    for i, (idx, v) in enumerate(to_translate):
        title = v.get('title', '')
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(translate_one, title)
                result = future.result(timeout=8)
            videos[idx]['zh'] = result or ''
            success += 1
            try:
                print(f'  [{i+1}/{len(to_translate)}] {title[:40]} -> {result[:40]}')
            except UnicodeEncodeError:
                print(f'  [{i+1}/{len(to_translate)}] OK (含特殊字符)')
        except FuturesTimeout:
            print(f'  [{i+1}/{len(to_translate)}] 超时跳过: {title[:40]}')
            videos[idx]['zh'] = ''
            time.sleep(2)
        except Exception as e:
            print(f'  [{i+1}/{len(to_translate)}] 失败: {e}')
            videos[idx]['zh'] = ''
            time.sleep(1)

        # 每 20 条保存一次
        if (i + 1) % 20 == 0:
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(videos, f, ensure_ascii=False, indent=2)
            print(f'  -- 已保存进度 --')

        time.sleep(0.4)

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    print(f'\n完成！成功翻译 {success} / {len(to_translate)} 条')
