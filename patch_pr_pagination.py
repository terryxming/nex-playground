"""
patch_pr_pagination.py
1. 把 PR 模块改为懒加载 + JS 分页
2. 给 PR 模块加 rowCount / pagination div
3. TikTok/YouTube/PR 三个模块默认折叠
4. 重新注入 pr-title-zh 翻译（因为 patch 脚本可能清除过）
"""
import re, json, os

HTML_FILE = 'nex_playground_pr_research_v2.html'

with open(HTML_FILE, encoding='utf-8') as f:
    html = f.read()

# ============================
# 1. 替换 applyPRFilters + 注入 PR 分页 JS
# ============================
old_pr_filter = (
    "  document.getElementById('search-pr').addEventListener('input', applyPRFilters);\n"
    "\n"
    "  function applyPRFilters() {\n"
    "    const activeBtn = document.querySelector('.filter-btn.active[data-filter]');\n"
    "    const filter = activeBtn ? activeBtn.dataset.filter : 'all';\n"
    "    const query = document.getElementById('search-pr').value.toLowerCase();\n"
    "\n"
    "    document.querySelectorAll('#pr-table tbody tr').forEach(row => {\n"
    "      const type = row.dataset.type || '';\n"
    "      const hasTag = row.dataset.tag === 'yes';\n"
    "      const text = row.textContent.toLowerCase();\n"
    "\n"
    "      let show = true;\n"
    "      if (filter === 'has-tag' && !hasTag) show = false;\n"
    "      else if (filter !== 'all' && filter !== 'has-tag' && !type.includes(filter)) show = false;\n"
    "      if (query && !text.includes(query)) show = false;\n"
    "\n"
    "      row.classList.toggle('hidden', !show);\n"
    "    });\n"
    "  }"
)

new_pr_filter = r"""  document.getElementById('search-pr').addEventListener('input', applyPRFilters);

  // ===== PR 分页 =====
  const PR_PAGE_SIZE = 40;
  let prPage = 0;
  let prFiltered = [];
  let prPageInited = false;

  function prRenderPage() {
    const allRows = Array.from(document.querySelectorAll('#pr-table tbody tr'));
    allRows.forEach(r => r.style.display = 'none');
    prFiltered.slice(prPage * PR_PAGE_SIZE, (prPage + 1) * PR_PAGE_SIZE).forEach(r => r.style.display = '');
    const total = prFiltered.length;
    const totalPages = Math.ceil(total / PR_PAGE_SIZE);
    document.getElementById('pr-rowCount').textContent = '共 ' + total + ' 条';
    let pg = '';
    if (totalPages > 1) {
      if (prPage > 0) pg += '<button class="pr-page-btn" onclick="prGoPage(' + (prPage-1) + ')">\u2039 上一页</button>';
      const lo = Math.max(0, prPage-3), hi = Math.min(totalPages-1, prPage+3);
      for (let i = lo; i <= hi; i++)
        pg += '<button class="pr-page-btn' + (i===prPage?' pr-page-active':'') + '" onclick="prGoPage(' + i + ')">' + (i+1) + '</button>';
      if (prPage < totalPages-1) pg += '<button class="pr-page-btn" onclick="prGoPage(' + (prPage+1) + ')">下一页 \u203a</button>';
    }
    document.getElementById('pr-pagination').innerHTML = pg;
  }

  function prGoPage(p) {
    prPage = p;
    prRenderPage();
    document.getElementById('content-pr').scrollIntoView({behavior:'smooth', block:'start'});
  }

  function applyPRFilters() {
    const activeBtn = document.querySelector('.filter-btn.active[data-filter]');
    const filter = activeBtn ? activeBtn.dataset.filter : 'all';
    const query = document.getElementById('search-pr').value.toLowerCase();
    prFiltered = Array.from(document.querySelectorAll('#pr-table tbody tr')).filter(row => {
      const type = row.dataset.type || '';
      const hasTag = row.dataset.tag === 'yes';
      const text = row.textContent.toLowerCase();
      if (filter === 'has-tag' && !hasTag) return false;
      if (filter !== 'all' && filter !== 'has-tag' && !type.includes(filter)) return false;
      if (query && !text.includes(query)) return false;
      return true;
    });
    prPage = 0;
    if (prPageInited) prRenderPage();
  }"""

if old_pr_filter in html:
    html = html.replace(old_pr_filter, new_pr_filter, 1)
    print('OK: applyPRFilters replaced with paginated version')
else:
    print('ERROR: applyPRFilters block not found')

# ============================
# 2. 在 PR controls 区域加 rowCount + pagination div
# ============================
old_controls_end = '    <div class="table-wrap">'
new_controls_end = (
    '    <div class="pr-status-bar">\n'
    '      <span id="pr-rowCount">共 181 条</span>\n'
    '      <span id="pr-pagination"></span>\n'
    '    </div>\n'
    '    <div class="table-wrap">'
)
if old_controls_end in html and 'pr-rowCount' not in html:
    # Only inject once, in the PR section (first occurrence)
    html = html.replace(old_controls_end, new_controls_end, 1)
    print('OK: PR status bar injected')
elif 'pr-rowCount' in html:
    print('SKIP: pr-rowCount already exists')
else:
    print('ERROR: table-wrap not found in PR section')

# ============================
# 3. PR status bar + page btn CSS
# ============================
pr_css = (
    '  .pr-status-bar { display: flex; justify-content: space-between; align-items: center;'
    ' margin: 6px 0 4px; font-size: 13px; color: #888; }\n'
    '  .pr-page-btn { padding: 3px 10px; border: 1px solid #ddd; background: white;'
    ' border-radius: 4px; cursor: pointer; font-size: 12px; margin: 0 2px; }\n'
    '  .pr-page-btn:hover, .pr-page-btn.pr-page-active { background: #0f3460; color: white;'
    ' border-color: #0f3460; }'
)
if '.pr-status-bar' not in html:
    html = html.replace('</style>', pr_css + '\n</style>', 1)
    print('OK: PR pagination CSS injected')
else:
    print('SKIP: PR pagination CSS already exists')

# ============================
# 4. 三个模块默认折叠（在 </script> 前注入初始化代码）
# ============================
init_code = """
  // ===== 初始化：模块默认折叠，懒加载 =====
  (function() {
    ['tiktok','youtube','pr'].forEach(function(id) {
      var c = document.getElementById('content-' + id);
      var t = document.getElementById('toggle-' + id);
      if (c) c.classList.add('collapsed');
      if (t) t.classList.add('collapsed');
    });
    // PR 初始化 filtered list（折叠状态，不渲染，等首次展开）
    applyPRFilters();
  })();
  // ===== End 初始化 ====="""

if '===== 初始化：模块默认折叠' not in html:
    html = html.replace('</script>\n</body>', init_code + '\n</script>\n</body>', 1)
    print('OK: 初始化折叠代码注入')
else:
    print('SKIP: 初始化代码已存在')

# ============================
# 5. 重新注入 PR 标题中文翻译（确保 pr-title-zh 存在）
# ============================
cache_file = 'pr_titles_cache.json'
if os.path.exists(cache_file):
    with open(cache_file, encoding='utf-8') as f:
        cache = json.load(f)

    PATTERN = re.compile(
        r'(<span class="title-text"><a [^>]+>)(.*?)(</a></span>)',
        re.DOTALL
    )
    # 先清除已有的 pr-title-zh
    html = re.sub(r'\s*<div class="pr-title-zh">[^<]*</div>', '', html)

    def replace_title(m):
        open_tag, title_html, close_tag = m.group(1), m.group(2), m.group(3)
        title_text = re.sub(r'<[^>]+>', '', title_html).strip()
        zh = cache.get(title_text, '')
        zh_div = f'\n          <div class="pr-title-zh">{zh}</div>' if zh else ''
        return f'{open_tag}{title_html}{close_tag}{zh_div}'

    html = PATTERN.sub(replace_title, html)
    injected = len(re.findall(r'class="pr-title-zh"', html))
    print(f'OK: PR 中文标题重新注入 {injected} 条')

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n所有改动已写入 HTML')
