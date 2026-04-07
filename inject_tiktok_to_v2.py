"""
将 tiktok_nex_videos.html 的完整表格格式注入 v2 的 TikTok 模块
"""
import re

with open('nex_playground_pr_research_v2.html', encoding='utf-8') as f:
    v2 = f.read()

with open('tiktok_nex_videos.html', encoding='utf-8') as f:
    tiktok = f.read()

# ── 1. 提取 TikTok 专用 CSS（从 .thumb-cell 开始，跳过和 v2 重复的基础样式）
css_match = re.search(r'(\.thumb-cell\s*\{.*?)</style>', tiktok, re.DOTALL)
tiktok_css = css_match.group(1).strip() if css_match else ''

# ── 2. 提取 controls div
controls_match = re.search(r'(<div class="controls">.*?</div>)\s*<div class="row-count"', tiktok, re.DOTALL)
controls_html = controls_match.group(1) if controls_match else ''

# ── 3. 提取 row-count div
rowcount_match = re.search(r'(<div class="row-count"[^>]*>.*?</div>)', tiktok, re.DOTALL)
rowcount_html = rowcount_match.group(1) if rowcount_match else ''

# ── 4. 提取完整表格
table_match = re.search(r'(<table id="mainTable">.*?</table>)', tiktok, re.DOTALL)
table_html = table_match.group(1) if table_match else ''

# ── 5. 提取 pagination div
pagination_match = re.search(r'(<div class="pagination"[^>]*>.*?</div>)', tiktok, re.DOTALL)
pagination_html = pagination_match.group(1) if pagination_match else '<div class="pagination" id="pagination"></div>'

# ── 6. 提取 JS 函数体
js_match = re.search(r'<script>(.*?)</script>', tiktok, re.DOTALL)
tiktok_js_body = js_match.group(1).strip() if js_match else ''

# ── 7. 动态检测所有函数名，统一加 tt_ 前缀（单词边界替换，一次搞定）
fn_names = re.findall(r'\bfunction\s+([a-zA-Z_]\w*)\s*\(', tiktok_js_body)
# 按名称长度倒序，防止短名称误替换长名称的子串
fn_names_sorted = sorted(set(fn_names), key=len, reverse=True)

def add_tt_prefix(text, names):
    for name in names:
        # 只替换尚未加过 tt_ 前缀的（负向回顾断言）
        text = re.sub(r'(?<!\btt_)\b' + re.escape(name) + r'\b(?!\s*:)', 'tt_' + name, text)
    return text

tiktok_js_body = add_tt_prefix(tiktok_js_body, fn_names_sorted)
controls_html  = add_tt_prefix(controls_html,  fn_names_sorted)
table_html     = add_tt_prefix(table_html,     fn_names_sorted)
pagination_html = add_tt_prefix(pagination_html, fn_names_sorted)

# ── 8. 构造注入内容
module_inner = f'''
    {controls_html}
    {rowcount_html}
    <div class="table-wrap" style="margin:8px 0 0 0">
      {table_html}
    </div>
    {pagination_html}
'''

# ── 9. 注入 CSS
tiktok_css_block = f'''
    /* ── TikTok 模块专用样式 ── */
    {tiktok_css}
    /* ─────────────────────── */'''

v2 = v2.replace('  </style>', tiktok_css_block + '\n  </style>', 1)

# ── 10. 替换 content-tiktok div 内容（括号计数匹配）
start_marker = '<div class="module-content" id="content-tiktok">'
start_idx = v2.find(start_marker)
if start_idx == -1:
    raise ValueError('找不到 content-tiktok')

inner_start = start_idx + len(start_marker)
depth = 1
pos = inner_start
inner_end = inner_start
while pos < len(v2) and depth > 0:
    open_pos  = v2.find('<div', pos)
    close_pos = v2.find('</div>', pos)
    if open_pos == -1:
        open_pos = len(v2)
    if close_pos == -1:
        break
    if open_pos < close_pos:
        depth += 1
        pos = open_pos + 4
    else:
        depth -= 1
        if depth == 0:
            inner_end = close_pos
        pos = close_pos + 6

v2 = v2[:inner_start] + '\n' + module_inner + '\n  ' + v2[inner_end:]

# ── 11. 更新模块计数
v2 = re.sub(r'id="tiktok-module-count">[^<]+', 'id="tiktok-module-count">549 条', v2)

# ── 12. 追加 TikTok JS（用 rfind 定位最后一个 </script>，避开注入内容里的假标签）
last_script_end = v2.rfind('</script>')
if last_script_end == -1:
    raise ValueError('找不到 </script> 标签')
v2 = (v2[:last_script_end]
      + '\n\n  // ── TikTok 模块交互 ──\n'
      + tiktok_js_body
      + '\n\n'
      + v2[last_script_end:])

# ── 写回
with open('nex_playground_pr_research_v2.html', 'w', encoding='utf-8') as f:
    f.write(v2)

print(f'Done! 文件大小: {len(v2)/1024:.0f} KB')
print(f'注入函数: {[f"tt_{n}" for n in fn_names_sorted]}')

# 验证
assert '正在抓取' not in v2 and 'agent 动态填充' not in v2, '占位符未清除'
assert 'id="tiktok-module-count">549 条' in v2, '计数未更新'
assert 'tt_' + fn_names_sorted[0] in v2, f'JS 函数 tt_{fn_names_sorted[0]} 未注入'
assert 'function toggleModule' in v2, 'v2 原有 toggleModule 被破坏'
assert 'function applyPRFilters' in v2, 'v2 原有 applyPRFilters 被破坏'
assert 'tt_tt_' not in v2, '双重前缀'
print('验证通过')
