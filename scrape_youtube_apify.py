"""
scrape_youtube_apify.py
用 Apify YouTube Scraper (streamers/youtube-scraper) 抓取 nex playground 相关视频
输出：youtube_nex_videos.json
"""

import requests
import json
import time

API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")  # 通过环境变量传入，不硬编码
ACTOR_ID = "streamers~youtube-scraper"
OUTPUT_FILE = "youtube_nex_videos.json"
MAX_RESULTS_PER_QUERY = 100

SEARCH_QUERIES = [
    "nex playground",
    "nex playground review",
    "nex playground unboxing",
    "nex playground game",
    "nex playground kids",
]


def start_run(search_query: str, max_results: int) -> str:
    resp = requests.post(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
        params={"token": API_TOKEN},
        json={"searchKeywords": search_query, "maxResults": max_results, "type": "SEARCH"},
    )
    resp.raise_for_status()
    run_id = resp.json()["data"]["id"]
    print(f"  → Run ID: {run_id}", flush=True)
    return run_id


def wait_for_run(run_id: str, timeout: int = 600) -> str:
    url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    start = time.time()
    while time.time() - start < timeout:
        data = requests.get(url, params={"token": API_TOKEN}).json()["data"]
        status = data["status"]
        elapsed = int(time.time() - start)
        print(f"  [{elapsed:3d}s] status: {status}", flush=True)
        if status == "SUCCEEDED":
            return data["defaultDatasetId"]
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Run {run_id} ended with {status}")
        time.sleep(10)
    raise TimeoutError(f"Run {run_id} timed out after {timeout}s")


def fetch_items(dataset_id: str) -> list:
    resp = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
        params={"token": API_TOKEN, "format": "json", "limit": 500},
    )
    resp.raise_for_status()
    return resp.json()


def main():
    all_videos = []
    seen_ids: set = set()

    for query in SEARCH_QUERIES:
        print(f"\n搜索: {query!r}")
        try:
            run_id = start_run(query, MAX_RESULTS_PER_QUERY)
            dataset_id = wait_for_run(run_id)
            items = fetch_items(dataset_id)

            new_count = 0
            for item in items:
                vid_id = item.get("id", "")
                if vid_id and vid_id not in seen_ids:
                    seen_ids.add(vid_id)
                    # 用 searchQuery 字段存搜索词，与 TikTok 保持一致
                    item["searchQuery"] = item.get("input", query)
                    all_videos.append(item)
                    new_count += 1

            print(f"  新增 {new_count} 条（去重后），累计 {len(all_videos)} 条", flush=True)

        except Exception as e:
            print(f"  错误: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)

    print(f"\n[done] 已保存至 {OUTPUT_FILE}，共 {len(all_videos)} 条视频", flush=True)


if __name__ == "__main__":
    main()
