# Nex Playground — 项目说明

> **IMPORTANT — 每次会话开始、接收任何指令前，必须先读完"工作流偏好"章节再行动。**

针对 Amazon ASIN **B0D2JGYX3F**（Nex Playground 体感游戏主机）的 PR 传播与联盟链接调研项目。

## 环境设置

```bash
pip install -r requirements.txt
playwright install chromium
```

## 脚本使用

| 场景 | 命令 |
|------|------|
| 关键词搜索 + 官方账号抓取 | `python scrape_tiktok_nex.py` |
| 需要登录才能访问（推荐） | `python scrape_tiktok_persistent.py` |

`scrape_tiktok_persistent.py` 会在 `browser_data/` 保存登录状态，下次运行无需重新登录。

## 数据管道

```
抓取脚本 → tiktok_nex_videos.json → tiktok_nex_videos.html (自动生成)
```

PR 数据已整合在 `nex_playground_pr_research_v2.html`，无需重新生成。

## 输出规范

- 所有输出文件保存至项目根目录
- 日期格式统一用 `YYYY-MM-DD`
- 网页用中文界面，数据表支持筛选和搜索
- 不生成 CSV，使用 HTML 网页呈现数据

## TikTok 抓取注意事项

- TikTok 有登录墙，用 `scrape_tiktok_persistent.py` 而非 `scrape_tiktok_nex.py`
- 首次运行会打开可见浏览器，需手动完成登录，之后自动保存
- `browser_data/` 目录不可提交 git（已加入 .gitignore）
- 翻译功能已移除（googletrans 不稳定），如需翻译使用 DeepL API

---

## 工作流偏好

### 1. 任务理解确认

在开始任何实质性操作前，先用 1-3 句话复述对任务的理解（目标、范围、预期输出），再开始执行。让用户有机会纠偏，避免方向错误后再返工。

### 2. 代码自检

写完代码后，执行自检清单：
- 是否偏离了原始任务？
- 是否引入了新的 bug 或边界问题？
- 是否有多余改动（超出任务范围）？
- 逻辑是否自洽？

如有问题，主动指出并修正，而不是等用户发现。

### 3. 打补丁 vs 重构判断框架

- 如果问题是局部孤立的 → 打补丁
- 如果根因在设计层（重复代码 / 错误抽象 / 耦合过深）→ 重构
- 重构前必须先说明理由，获得认可再动手
- 禁止以"顺手改了"为由扩大改动范围

### 4. 问题 → 解决 → 验证闭环

- 遇到问题先定位根因，不打症状补丁
- 修复后必须说明如何验证（运行什么命令 / 看什么输出）
- 如有测试，运行测试后才算完成

### 5. 自学习机制

- 每当用户纠正了我的行为或判断，主动将该反馈存入 `memory/feedback_*.md`
- 如果是通用的（跨项目适用的）错误，提示用户将其加入 `~/.claude/CLAUDE.md`
