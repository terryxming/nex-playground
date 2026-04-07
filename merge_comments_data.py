"""
下载评论+转录数据集，合并进 tiktok_nex_videos.json
评论单独保存到 comments/ 目录（每个视频一个文件）
"""
import json, os, time, urllib.request

APIFY_TOKEN = os.environ.get('APIFY_TOKEN', '')
HEADERS = {'Authorization': f'Bearer {APIFY_TOKEN}'}
DATASET_ID = 'qkFXeShEwQOjN4GDg'

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2)

# ── 1. 下载新数据集全部 549 条 ─────────────────────────────
print('下载视频数据（含评论链接）...')
all_new = []
offset = 0
while True:
    data = fetch(f'https://api.apify.com/v2/datasets/{DATASET_ID}/items?limit=500&offset={offset}')
    if not data:
        break
    all_new.extend(data)
    print(f'  已下载: {len(all_new)}')
    if len(data) < 500:
        break
    offset += 500

# 建索引
new_by_id = {str(v['id']): v for v in all_new}
print(f'新数据: {len(new_by_id)} 条')

# ── 2. 合并进原 JSON ───────────────────────────────────────
with open('tiktok_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)

for v in videos:
    vid = str(v.get('id'))
    if vid in new_by_id:
        nv = new_by_id[vid]
        # 更新封面（用 Apify 永久链接替换原来会过期的 TikTok CDN 链接）
        if nv.get('videoMeta', {}).get('coverUrl'):
            v.setdefault('videoMeta', {})['coverUrl'] = nv['videoMeta']['coverUrl']
        # 写入评论数据集链接
        v['commentsDatasetUrl'] = nv.get('commentsDatasetUrl')
        # 写入字幕/转录链接
        v['subtitleLinks'] = nv.get('videoMeta', {}).get('subtitleLinks', [])
        v['transcriptionLink'] = nv.get('videoMeta', {}).get('transcriptionLink')
        v['isSponsored'] = nv.get('isSponsored', False)
        v['locationCreated'] = nv.get('locationCreated', '')

with open('tiktok_nex_videos.json', 'w', encoding='utf-8') as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)
print('tiktok_nex_videos.json 已更新')

# ── 3. 下载评论（每条视频最多 100 条）─────────────────────
os.makedirs('comments', exist_ok=True)
has_comments_url = [v for v in videos if v.get('commentsDatasetUrl')]
print(f'\n开始下载评论，共 {len(has_comments_url)} 条视频有评论链接...')

done = 0
for i, v in enumerate(has_comments_url):
    vid = str(v['id'])
    out_file = f'comments/{vid}.json'
    if os.path.exists(out_file):
        done += 1
        continue
    try:
        url = v['commentsDatasetUrl'] + '&limit=100'
        comments = fetch(url)
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False)
        done += 1
        if done % 50 == 0 or done == len(has_comments_url):
            print(f'  [{done}/{len(has_comments_url)}] 完成')
        time.sleep(0.2)
    except Exception as e:
        print(f'  [{i+1}] 失败 {vid}: {e}')

print(f'\n完成！评论文件保存在 comments/ 目录')

# ── 4. 统计评论数据 ────────────────────────────────────────
total_comments = 0
for fname in os.listdir('comments'):
    try:
        with open(f'comments/{fname}', encoding='utf-8') as f:
            data = json.load(f)
        total_comments += len(data)
    except:
        pass
print(f'总评论条数: {total_comments}')
