---
paths:
  - "*.html"
  - "*.json"
---

# 数据格式规则

## HTML 报告
- 所有 HTML 文件使用 UTF-8 编码，带 `<meta charset="UTF-8">`
- 数据表需支持实时搜索/筛选（JavaScript 实现）
- 表格行用 `data-type` 和 `data-tag` 属性支持筛选逻辑
- 中文界面，标题/按钮/提示文字均为中文

## Amazon Affiliate Tag 格式
- Tag 格式：`xxx-20`（Amazon Associates 标准后缀）
- 推断的 tag 用虚线边框样式标注（`tag-inferred` class）
- 已确认的 tag 用实线边框（`tag-pill` class）

## JSON 输出
- 统一结构：`{ total, scraped_at, videos: [...] }`
- 时间戳用 ISO 8601 格式（`datetime.now().isoformat()`）
- 文件用 `ensure_ascii=False` + `indent=2` 保存
