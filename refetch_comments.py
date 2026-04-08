"""
用 TikTok Scraper (clockworks/tiktok-scraper) 重新抓取每个视频的评论。

每批 N 个视频一起发给 actor，结果放在同一个 dataset，
用 videoWebUrl 区分后分别保存到 comments/{video_id}.json。

用法：
  python refetch_comments.py                   # 抓全部 549 个，每批 50，每视频 200 条
  python refetch_comments.py --limit 10        # 只抓前 10 个（测试）
  python refetch_comments.py --batch-size 30   # 每批 30 个视频
  python refetch_comments.py --comments 50     # 每视频 50 条评论
  python refetch_comments.py --force           # 强制重新下载（即使已有数据）
"""

import json
import os
import sys
import time
import argparse
import datetime
import glob
import requests

sys.stdout.reconfigure(encoding="utf-8")

# ─── 配置 ──────────────────────────────────────────────────────────────────────

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
ACTOR_ID = "GdWCkxBtKWOsKjdch"  # clockworks/tiktok-scraper

HEADERS = {
    "Authorization": f"Bearer {APIFY_TOKEN}",
    "Content-Type": "application/json",
}

# 之前错误数据的标志：评论 videoWebUrl 指向这个视频说明是旧数据
WRONG_URL_MARKER = "7517426238970006839"

# ─── 参数 ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--batch-size", type=int, default=50, help="每批视频数量（默认 50）")
parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个视频（0=全部）")
parser.add_argument("--comments", type=int, default=200, help="每视频最多评论数（默认 200）")
parser.add_argument("--force", action="store_true", help="强制重新抓，忽略已有文件")
parser.add_argument("--run-timeout", type=int, default=1800,
                    help="等待单次 actor run 完成的最长秒数（默认 1800=30 分钟）")
args = parser.parse_args()

# ─── 工具函数 ──────────────────────────────────────────────────────────────────

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")

def log(msg):
    print(f"[{ts()}] {msg}", flush=True)

def api_get(url, retries=5, timeout=30):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            wait = min(2 ** i, 30)
            log(f"  GET 超时: {url[:60]}... 等 {wait}s 重试 ({i+1}/{retries})")
            time.sleep(wait)
        except Exception as e:
            wait = min(2 ** i, 30)
            log(f"  GET 失败: {e} 等 {wait}s 重试 ({i+1}/{retries})")
            time.sleep(wait)
    raise RuntimeError(f"GET 失败（重试 {retries} 次）: {url[:80]}")

def api_post(url, payload, retries=5, timeout=30):
    for i in range(retries):
        try:
            r = requests.post(url, headers=HEADERS, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            wait = min(2 ** i, 30)
            log(f"  POST 超时，等 {wait}s 重试 ({i+1}/{retries})")
            time.sleep(wait)
        except Exception as e:
            wait = min(2 ** i, 30)
            log(f"  POST 失败: {e}，等 {wait}s 重试 ({i+1}/{retries})")
            time.sleep(wait)
    raise RuntimeError(f"POST 失败（重试 {retries} 次）")

def wait_for_run(run_id, timeout_sec):
    """轮询 actor run 直到完成或超时。每 2 分钟打印一次进度。"""
    deadline = time.time() + timeout_sec
    poll_interval = 15          # 每 15s 查一次状态
    report_interval = 120       # 每 2 分钟打印一次日志
    last_report = time.time()
    while time.time() < deadline:
        try:
            data = api_get(f"https://api.apify.com/v2/actor-runs/{run_id}")
            status = data.get("data", {}).get("status", "")
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                return data.get("data", {})
        except Exception as e:
            log(f"  轮询异常: {e}，继续等待...")
        now = time.time()
        if now - last_report >= report_interval:
            elapsed = int(now - (deadline - timeout_sec))
            remaining = int(deadline - now)
            log(f"  Run {run_id[:16]}... 已等待 {elapsed}s，剩余超时 {remaining}s")
            last_report = now
        time.sleep(poll_interval)
    raise TimeoutError(f"Run {run_id} 超过 {timeout_sec}s 未完成")

def needs_refetch(video_id):
    """判断这个视频是否需要重新抓评论。"""
    if args.force:
        return True
    fpath = f"comments/{video_id}.json"
    if not os.path.exists(fpath):
        return True
    try:
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        comments = data if isinstance(data, list) else []
        if not comments:
            return True
        # 评论数少于 5 条，大概率是误存了视频对象而非真实评论
        if len(comments) < 5:
            return True
        sample_url = comments[0].get("videoWebUrl", "")
        # videoWebUrl 为空：误存了视频元数据（不是评论）
        if not sample_url:
            return True
        # videoWebUrl 指向已知的错误视频
        if WRONG_URL_MARKER in sample_url:
            return True
        return False
    except Exception:
        return True

def extract_video_id_from_url(url):
    """从 TikTok 视频 URL 提取 video_id。"""
    return url.rstrip("/").split("/")[-1] if url else ""

# ─── 加载数据 ──────────────────────────────────────────────────────────────────

with open("tiktok_nex_videos.json", encoding="utf-8") as f:
    videos = json.load(f)

os.makedirs("comments", exist_ok=True)

target = videos[: args.limit] if args.limit > 0 else videos
pending = [v for v in target if needs_refetch(str(v["id"]))]

log(f"总视频: {len(videos)} | 本次目标: {len(target)} | 需要抓取: {len(pending)} | 已有正确数据: {len(target)-len(pending)}")

if not pending:
    log("所有视频已有正确评论数据，退出。")
    sys.exit(0)

# ─── 主循环 ────────────────────────────────────────────────────────────────────

batches = [pending[i: i + args.batch_size] for i in range(0, len(pending), args.batch_size)]
total_saved = 0
total_failed_vids = []
global_start = time.time()
videos_done = 0  # 已处理视频数（成功+失败）

log(f"分 {len(batches)} 批运行，每批最多 {args.batch_size} 个，每视频 {args.comments} 条评论")
log(f"超时设置: 每批最长等待 {args.run_timeout}s，超时自动跳过继续下一批")
print()

for batch_idx, batch in enumerate(batches):
    batch_video_ids = {str(v["id"]): v for v in batch}
    video_urls = [v["webVideoUrl"] for v in batch]

    log(f"批次 {batch_idx+1}/{len(batches)}: {len(batch)} 个视频")

    # ── 启动 actor run ──
    run_input = {
        "postURLs": video_urls,
        "commentsPerPost": args.comments,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
        "maxRequestRetries": 3,
    }

    try:
        resp = api_post(f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs", run_input)
        run_id = resp.get("data", {}).get("id")
        log(f"  Run 启动: {run_id}")
    except Exception as e:
        log(f"  启动失败: {e}，跳过此批")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    # ── 等待完成（带超时）──
    try:
        run_data = wait_for_run(run_id, args.run_timeout)
    except TimeoutError as e:
        log(f"  超时: {e}，跳过此批")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    status = run_data.get("status")
    dataset_id = run_data.get("defaultDatasetId")
    log(f"  Run 完成: status={status}, dataset={dataset_id}")

    if status != "SUCCEEDED" or not dataset_id:
        log(f"  Run 未成功（{status}），跳过此批")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    # ── Step 1: 下载 defaultDataset（视频对象，含 commentsDatasetUrl）──
    try:
        video_items = api_get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?limit={len(batch)+10}",
            timeout=60,
        )
    except Exception as e:
        log(f"  下载视频 dataset 失败: {e}，跳过此批")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    if not isinstance(video_items, list):
        log(f"  dataset 格式异常: {str(video_items)[:100]}")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    log(f"  视频对象: {len(video_items)} 个")

    # ── Step 2: 从任意视频对象拿 commentsDatasetUrl（所有视频共享同一个评论 dataset）──
    comments_dataset_url = None
    for vi in video_items:
        u = vi.get("commentsDatasetUrl")
        if u:
            comments_dataset_url = u
            break

    if not comments_dataset_url:
        log("  警告: 所有视频对象的 commentsDatasetUrl 均为 null，跳过此批")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    log(f"  评论 dataset URL: {comments_dataset_url[:80]}")

    # ── Step 3: 下载评论 dataset（所有视频的评论在一个 dataset，用 videoWebUrl 区分）──
    download_limit = len(batch) * args.comments + 100
    try:
        items = api_get(
            comments_dataset_url + f"&limit={download_limit}",
            timeout=60,
        )
    except Exception as e:
        log(f"  下载评论 dataset 失败: {e}，跳过此批")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    if not isinstance(items, list):
        log(f"  评论 dataset 格式异常: {str(items)[:100]}")
        total_failed_vids.extend(batch_video_ids.keys())
        continue

    log(f"  下载到 {len(items)} 条评论")

    # ── Step 4: 按 videoWebUrl 分组 ──
    by_video = {}  # video_id -> list of comments
    for item in items:
        video_url = item.get("videoWebUrl", "") or item.get("submittedVideoUrl", "")
        vid = extract_video_id_from_url(video_url)
        if vid:
            by_video.setdefault(vid, []).append(item)

    # ── 保存每个视频的评论 ──
    batch_saved = 0
    for vid, v_meta in batch_video_ids.items():
        comments = by_video.get(vid, [])
        if comments:
            out_path = f"comments/{vid}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False)
            batch_saved += 1
        else:
            log(f"  ⚠ video {vid} 未获取到评论（视频可能已删除或关闭评论）")
            total_failed_vids.append(vid)

    total_saved += batch_saved
    videos_done += len(batch)
    elapsed_total = int(time.time() - global_start)
    speed = videos_done / max(elapsed_total, 1)  # 视频/秒
    remaining_vids = len(pending) - videos_done
    eta_sec = int(remaining_vids / speed) if speed > 0 else 0
    eta_str = f"{eta_sec//60}分{eta_sec%60}秒" if eta_sec > 0 else "即将完成"
    log(f"  已保存: {batch_saved}/{len(batch)} | 总进度: {videos_done}/{len(pending)} 个视频 | "
        f"已用: {elapsed_total//60}分{elapsed_total%60}秒 | 预计剩余: {eta_str}")
    print()

    # 批次间稍作间隔
    if batch_idx < len(batches) - 1:
        time.sleep(2)

# ─── 最终汇总 ──────────────────────────────────────────────────────────────────

log("全部完成！")
log(f"  成功保存: {total_saved} 个视频")
log(f"  失败/无评论: {len(total_failed_vids)} 个视频")

if total_failed_vids:
    log("  失败列表（前 20）: " + ", ".join(total_failed_vids[:20]))

# 验证
all_files = glob.glob("comments/*.json")
correct = wrong = 0
for fpath in all_files:
    try:
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        comments = data if isinstance(data, list) else []
        if comments and WRONG_URL_MARKER not in comments[0].get("videoWebUrl", ""):
            correct += 1
        else:
            wrong += 1
    except Exception:
        wrong += 1

log(f"\n最终验证: 正确={correct} 个视频, 仍有问题={wrong} 个视频")
