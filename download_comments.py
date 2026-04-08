"""
下载全部 549 条视频的评论（每视频 200 条），每 2 分钟输出进度
"""
import json, os, time, urllib.request, sys, datetime
sys.stdout.reconfigure(encoding='utf-8')

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
HEADERS = {'Authorization': f'Bearer {APIFY_TOKEN}'}
LIMIT = 200

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

with open('tiktok_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)

os.makedirs('comments', exist_ok=True)
targets = [v for v in videos if v.get('commentsDatasetUrl')]
total = len(targets)
print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] 开始下载，共 {total} 条视频，每视频最多 {LIMIT} 条评论', flush=True)

done = 0
failed = 0
start = time.time()
last_report = start

for i, v in enumerate(targets):
    vid = str(v['id'])
    out_file = f'comments/{vid}.json'
    if os.path.exists(out_file):
        done += 1
    else:
        try:
            url = v['commentsDatasetUrl'] + f'&limit={LIMIT}'
            comments = fetch(url)
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(comments, f, ensure_ascii=False)
            done += 1
            time.sleep(0.2)
        except Exception as e:
            failed += 1
            print(f'  失败 {vid}: {e}', flush=True)

    # 每 2 分钟报一次进度
    now = time.time()
    if now - last_report >= 120:
        elapsed = int(now - start)
        mins, secs = divmod(elapsed, 60)
        print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] 进度: {done}/{total} ({done/total*100:.1f}%) | 失败: {failed} | 已用: {mins}分{secs}秒', flush=True)
        last_report = now

elapsed = int(time.time() - start)
mins, secs = divmod(elapsed, 60)
print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] 全部完成！成功 {done}，失败 {failed}，耗时 {mins}分{secs}秒', flush=True)
