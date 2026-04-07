#!/usr/bin/env python3
"""
TikTok 持久化登录状态抓取脚本
通过保持浏览器会话绕过 TikTok 登录墙，登录状态自动保存到 browser_data/
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from scrape_tiktok_nex import TikTokScraper, generate_html_report, _JS_GET_VIDEO_LINKS

# --- 配置常量 ---
OUTPUT_DIR = Path(__file__).parent
BROWSER_DATA_DIR = OUTPUT_DIR / "browser_data"
LOGIN_WAIT = 30    # 初始等待登录秒数
RETRY_WAIT = 60    # 未发现视频时的重试等待秒数
SCROLL_COUNT = 10
SCROLL_DELAY = 2


class TikTokPersistentScraper(TikTokScraper):
    """继承 TikTokScraper，使用持久化浏览器上下文保留登录状态"""

    async def scrape_with_login(self, username="nexplayground"):
        """通过持久化登录状态抓取账号视频"""
        BROWSER_DATA_DIR.mkdir(exist_ok=True)

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                str(BROWSER_DATA_DIR),
                headless=False,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            )
            page = context.pages[0] if context.pages else await context.new_page()

            print(f"[1/4] 正在访问 @{username}...")
            print("      如遇登录/验证码请手动完成，浏览器将保持开启")
            await page.goto(f'https://www.tiktok.com/@{username}')

            print(f"\n[等待] 等待 {LOGIN_WAIT} 秒让页面加载/完成登录...")
            await asyncio.sleep(LOGIN_WAIT)

            print("\n[2/4] 检查视频列表...")
            await page.screenshot(path=str(OUTPUT_DIR / 'after_login.png'))
            video_links = await page.evaluate(_JS_GET_VIDEO_LINKS)
            print(f"      找到 {len(video_links)} 个视频链接")

            if not video_links:
                print(f"\n[!] 未找到视频，等待 {RETRY_WAIT} 秒后重试...")
                print("    可能原因: 1.需要登录  2.账号无视频  3.页面结构变更")
                await asyncio.sleep(RETRY_WAIT)
                video_links = await page.evaluate(_JS_GET_VIDEO_LINKS)
                print(f"      重试结果: {len(video_links)} 个视频")

            if video_links:
                print(f"\n[3/4] 滚动加载更多视频...")
                for i in range(SCROLL_COUNT):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(SCROLL_DELAY)
                    video_links = await page.evaluate(_JS_GET_VIDEO_LINKS)
                    print(f"      滚动 {i+1}/{SCROLL_COUNT}: {len(video_links)} 个视频")

                print(f"\n[4/4] 抓取 {len(video_links)} 个视频详情...")
                await self._scrape_videos(page, video_links)

            print("\n[完成] 10 秒后关闭浏览器...")
            await asyncio.sleep(10)
            await context.close()


async def main():
    scraper = TikTokPersistentScraper()

    print("=" * 70)
    print("TikTok 持久化登录抓取脚本")
    print("浏览器将保持开启，如有登录提示请手动完成")
    print("登录状态会被保存到 browser_data/，下次运行无需重新登录")
    print("=" * 70)

    await scraper.scrape_with_login("nexplayground")

    if scraper.videos:
        videos = scraper.save_results()
        generate_html_report(videos)
    else:
        print("\n[!] 未抓取到视频，请检查:")
        print("    1. 在浏览器中登录 TikTok")
        print("    2. 确认 @nexplayground 账号存在且有视频")
        print("    3. 重新运行脚本（登录状态已保存）")


if __name__ == "__main__":
    asyncio.run(main())
