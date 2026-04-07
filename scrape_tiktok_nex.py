#!/usr/bin/env python3
"""
TikTok Nex Playground 视频数据抓取脚本
使用 Playwright 自动化浏览器抓取 TikTok 视频信息
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# --- 配置常量 ---
OUTPUT_DIR = Path(__file__).parent
MAX_VIDEOS = 50             # 单次抓取最大视频数
SCROLL_COUNT = 10           # 滚动加载次数
SCROLL_DELAY = 2            # 每次滚动后等待秒数
PAGE_LOAD_DELAY = 3         # 页面加载等待秒数
VIDEO_PAGE_TIMEOUT = 15000  # 视频页面超时（毫秒）

# JavaScript: 收集页面内所有视频链接（去重）
_JS_GET_VIDEO_LINKS = '''() => {
    const links = Array.from(document.querySelectorAll('a[href*="/video/"]'));
    return [...new Set(links.map(a => a.href))];
}'''

# JavaScript: 从视频页面提取结构化数据（优先 JSON，备用 DOM）
_JS_EXTRACT_VIDEO_DATA = r'''() => {
    const scripts = Array.from(document.querySelectorAll('script'));
    const dataScript = scripts.find(s => s.textContent.includes('__UNIVERSAL_DATA_FOR_REHYDRATION__'));

    if (dataScript) {
        try {
            const m = dataScript.textContent.match(/__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*({.+?})\s*<\/script>/);
            if (m) {
                const d = JSON.parse(m[1]);
                const v = d?.__DEFAULT_SCOPE__?.['webapp.video-detail']?.itemInfo?.itemStruct;
                if (v) {
                    return {
                        video_id:    v.id,
                        author:      v.author?.uniqueId || '',
                        author_name: v.author?.nickname || '',
                        desc:        v.desc || '',
                        create_time: v.createTime,
                        likes:       v.stats?.diggCount    || 0,
                        comments:    v.stats?.commentCount || 0,
                        shares:      v.stats?.shareCount   || 0,
                        plays:       v.stats?.playCount    || 0,
                        music:       v.music?.title || '',
                        hashtags:    (v.textExtra || []).filter(t => t.hashtagName).map(t => t.hashtagName)
                    };
                }
            }
        } catch (e) {}
    }

    // 备用：DOM 提取
    const getText = sel => { const el = document.querySelector(sel); return el ? el.textContent.trim() : ''; };
    const toNum = text => {
        if (!text) return 0;
        const m = text.match(/[\d.]+/);
        if (!m) return 0;
        const n = parseFloat(m[0]);
        if (text.includes('K')) return Math.floor(n * 1000);
        if (text.includes('M')) return Math.floor(n * 1000000);
        return Math.floor(n);
    };
    return {
        video_id:    window.location.pathname.match(/video\/(\d+)/)?.[1] || '',
        author:      getText('[data-e2e="browse-username"]') || getText('a[href^="/@"]'),
        desc:        getText('[data-e2e="browse-video-desc"]') || getText('h1'),
        likes:       toNum(getText('[data-e2e="like-count"]')),
        comments:    toNum(getText('[data-e2e="comment-count"]')),
        shares:      toNum(getText('[data-e2e="share-count"]')),
        plays:       toNum(getText('[data-e2e="video-views"]')),
        create_time: null
    };
}'''


class TikTokScraper:
    def __init__(self):
        self.videos = []

    async def scrape_account(self, username="nexplayground"):
        """抓取指定账号的视频列表"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            print(f"正在访问 @{username}...")
            await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle')
            await asyncio.sleep(PAGE_LOAD_DELAY)

            video_links = await self._scroll_and_collect(page, SCROLL_COUNT)
            print(f"找到 {len(video_links)} 个视频链接")
            await self._scrape_videos(page, video_links[:MAX_VIDEOS])
            await browser.close()

    async def search_keyword(self, keyword="nex playground"):
        """搜索关键词相关视频"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()

            search_url = f'https://www.tiktok.com/search?q={keyword.replace(" ", "+")}'
            print(f"搜索: {search_url}")
            await page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(PAGE_LOAD_DELAY)

            video_links = await self._scroll_and_collect(page, SCROLL_COUNT // 2)
            print(f"搜索到 {len(video_links)} 个视频")
            await self._scrape_videos(page, video_links[:MAX_VIDEOS])
            await browser.close()

    async def _scroll_and_collect(self, page, scroll_count):
        """滚动页面并收集视频链接"""
        for i in range(scroll_count):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(SCROLL_DELAY)
            print(f"  滚动 {i+1}/{scroll_count}")
        return await page.evaluate(_JS_GET_VIDEO_LINKS)

    async def _scrape_videos(self, page, video_links):
        """逐个抓取视频详情"""
        for idx, video_url in enumerate(video_links, 1):
            print(f"\n[{idx}/{len(video_links)}] 抓取: {video_url}")
            try:
                video_data = await self.scrape_video_page(page, video_url)
                if video_data:
                    self.videos.append(video_data)
                    print(f"  [OK] {video_data['author']} | {video_data['likes']} 赞")
            except Exception as e:
                print(f"  [X] 失败: {e}")
            await asyncio.sleep(1)

    async def scrape_video_page(self, page, url):
        """从单个视频页面提取数据"""
        await page.goto(url, wait_until='domcontentloaded', timeout=VIDEO_PAGE_TIMEOUT)
        await asyncio.sleep(SCROLL_DELAY)

        data = await page.evaluate(_JS_EXTRACT_VIDEO_DATA)
        if data and data.get('video_id'):
            data['url'] = url
            data['scraped_at'] = datetime.now().isoformat()
            return data
        return None

    def save_results(self, filename="tiktok_nex_videos.json"):
        """保存结果为 JSON"""
        sorted_videos = sorted(
            self.videos,
            key=lambda x: x.get('create_time', 0) or 0,
            reverse=True
        )
        output_path = OUTPUT_DIR / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(sorted_videos),
                'scraped_at': datetime.now().isoformat(),
                'videos': sorted_videos
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] 已保存 {len(sorted_videos)} 个视频到 {output_path}")
        return sorted_videos


def generate_html_report(videos, filename="tiktok_nex_videos.html"):
    """生成 TikTok 视频 HTML 可视化报告"""
    rows = ''
    for video in videos:
        create_time = ''
        if video.get('create_time'):
            try:
                create_time = datetime.fromtimestamp(int(video['create_time'])).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                pass
        hashtags = ' '.join(f'#{tag}' for tag in video.get('hashtags', []))
        rows += f'''
        <tr>
            <td><a href="{video.get('url', '')}" target="_blank">🎬 查看</a></td>
            <td class="author">@{video.get('author', 'N/A')}</td>
            <td class="desc">
                <div class="desc-en">{video.get('desc', '')}</div>
                <span class="hashtags">{hashtags}</span>
            </td>
            <td class="date">{create_time}</td>
            <td class="number">{video.get('likes', 0):,}</td>
            <td class="number">{video.get('comments', 0):,}</td>
            <td class="number">{video.get('shares', 0):,}</td>
            <td class="number">{video.get('plays', 0):,}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nex Playground TikTok 视频数据</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #333; margin-bottom: 10px; }}
        .stats {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 30px; }}
        .stat-item {{ text-align: center; }}
        .stat-number {{ font-size: 32px; font-weight: bold; color: #fe2c55; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .filters {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .filters input {{ padding: 10px; border: 1px solid #ddd; border-radius: 4px; width: 300px; font-size: 14px; }}
        table {{ width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-collapse: collapse; }}
        th {{ background: #fe2c55; color: white; padding: 15px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
        tr:hover {{ background: #f9f9f9; }}
        .author {{ font-weight: 600; color: #333; white-space: nowrap; }}
        .desc {{ color: #666; max-width: 400px; }}
        .desc-en {{ color: #333; margin-bottom: 4px; }}
        .number {{ font-weight: 600; color: #fe2c55; text-align: right; }}
        .date {{ color: #999; font-size: 13px; white-space: nowrap; }}
        .hashtags {{ color: #1e90ff; font-size: 12px; }}
        a {{ color: #fe2c55; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Nex Playground TikTok 视频数据</h1>
        <p style="color:#666;margin-bottom:20px;">抓取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <div class="stats">
            <div class="stat-item"><div class="stat-number">{len(videos)}</div><div class="stat-label">视频总数</div></div>
            <div class="stat-item"><div class="stat-number">{sum(v.get('likes', 0) for v in videos):,}</div><div class="stat-label">总点赞数</div></div>
            <div class="stat-item"><div class="stat-number">{sum(v.get('comments', 0) for v in videos):,}</div><div class="stat-label">总评论数</div></div>
            <div class="stat-item"><div class="stat-number">{sum(v.get('plays', 0) for v in videos):,}</div><div class="stat-label">总播放量</div></div>
        </div>
        <div class="filters">
            <input type="text" id="searchInput" placeholder="🔍 搜索作者、描述、标签..." onkeyup="filterTable()">
        </div>
        <table id="videoTable">
            <thead>
                <tr>
                    <th>视频</th><th>作者</th><th>描述</th><th>发布时间</th>
                    <th>❤️ 点赞</th><th>💬 评论</th><th>🔗 分享</th><th>👁️ 播放</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    <script>
        function filterTable() {{
            const filter = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('#videoTable tbody tr').forEach(row => {{
                row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>'''

    output_path = OUTPUT_DIR / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[OK] HTML 报告已生成: {output_path}")


async def main():
    scraper = TikTokScraper()

    print("=" * 60)
    print("步骤 1: 抓取官方账号 @nexplayground")
    print("=" * 60)
    await scraper.scrape_account("nexplayground")

    print("\n" + "=" * 60)
    print("步骤 2: 搜索关键词 'nex playground'")
    print("=" * 60)
    await scraper.search_keyword("nex playground")

    videos = scraper.save_results()
    generate_html_report(videos)


if __name__ == "__main__":
    asyncio.run(main())
