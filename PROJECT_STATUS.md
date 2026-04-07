# Nex Playground 项目进度报告
**更新时间**: 2026-04-07

## 当前状态
🟡 **PR 数据已完成，待抓取 TikTok / YouTube / Amazon Live 数据**

## 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| PR 文章数据 | ✅ | 181 条记录，已整合至 v2 报告 |
| V2 报告框架 | ✅ | 四模块（PR/TikTok/YouTube/Amazon Live），筛选/搜索已实现 |
| TikTok 抓取脚本 | ✅ | `scrape_tiktok_persistent.py`（支持持久化登录） |
| 代码清理 | ✅ | 删除死代码，修复重复逻辑，提取常量 |
| 项目规范 | ✅ | CLAUDE.md、rules/、.gitignore、requirements.txt |

## 待办（按优先级）

### 1. TikTok 数据抓取
- 运行 `python scrape_tiktok_persistent.py`
- 首次需手动登录，之后自动保存状态
- 目标：@nexplayground 官方账号 50+ 视频

### 2. TikTok 数据填入 V2 报告
- 将抓取结果 `tiktok_nex_videos.json` 的数据迁移至 `nex_playground_pr_research_v2.html` 的 TikTok 模块

### 3. YouTube 数据抓取
- YouTube Data API v3 或 Playwright
- 目标：100+ 视频

### 4. Amazon Live 补充
- 当前 V2 已有 8 条，目标扩展至 20-30 条

## 核心文件

| 文件 | 说明 |
|------|------|
| `nex_playground_pr_research_v2.html` | 主报告（PR 181条已填入，其余模块待填充） |
| `scrape_tiktok_nex.py` | TikTok 抓取（关键词搜索 + 账号，无需登录） |
| `scrape_tiktok_persistent.py` | TikTok 抓取（持久化登录，推荐用这个） |
| `requirements.txt` | 依赖：`playwright>=1.40.0` |
