---
paths:
  - "*.py"
  - "scrape_*"
---

# TikTok 抓取规则

## 脚本选择
- 默认用 `scrape_tiktok_persistent.py`（支持登录状态保存）
- `scrape_tiktok_nex.py` 仅用于无需登录的公开数据测试

## 代码约定
- 所有配置常量放在文件顶部（`MAX_VIDEOS`、`SCROLL_COUNT` 等）
- 路径用 `Path(__file__).parent` 而非硬编码绝对路径
- JS 代码提取为模块级常量（`_JS_GET_VIDEO_LINKS` 等），不内联在方法中
- `TikTokPersistentScraper` 继承 `TikTokScraper`，禁止在子类中重复父类方法

## 错误处理
- 不使用裸 `except:`，至少用 `except Exception as e`
- 抓取失败时打印错误但继续下一条，不中断整体流程
