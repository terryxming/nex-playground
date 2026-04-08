"""
Patch nex_playground_pr_research_v2.html TikTok module
- Data stored as JS array (not static HTML rows)
- Pagination: 50 rows per page
- Filter/sort on JS array, re-render only current page
"""
import json, re
from collections import Counter

QUERY_COLORS = {
    'nex playground unboxing': '#e74c3c',
    'nex playground review':   '#9b59b6',
    'nex playground kids':     '#f39c12',
    'nex playground game':     '#1abc9c',
    'nexplayground':           '#2ecc71',
    'nex playground':          '#3498db',
    'nexpartner':              '#e67e22',
}

def fmt_num(n):
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}K'
    return str(n) if n else '0'

def clean(s):
    """Remove control characters that break JSON-in-JS embedding."""
    return ''.join(c if ord(c) >= 32 else ' ' for c in s).strip()

# Load data
with open('tiktok_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)
with open('translations_cache.json', encoding='utf-8') as f:
    translations = json.load(f)

videos.sort(key=lambda v: v.get('playCount', 0), reverse=True)

total = len(videos)
query_counts = Counter(v.get('searchQuery', '') for v in videos)

# Build compact JS data array
def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ').replace('\r', '')

data_items = []
for v in videos:
    a        = v.get('authorMeta', {})
    vid_id   = str(v.get('id', ''))
    hashtags = [h.get('name', '') for h in v.get('hashtags', []) if h.get('name')]
    query    = v.get('searchQuery', '')
    zh       = translations.get(vid_id, '')
    cover    = v.get('videoMeta', {}).get('coverUrl', '')

    item = {
        'url':      v.get('webVideoUrl', ''),
        'cover':    cover,
        'author':   a.get('name', ''),
        'profile':  a.get('profileUrl', ''),
        'fans':     a.get('fans', 0),
        'verified': 1 if a.get('verified') else 0,
        'text':     clean(v.get('text', ''))[:120],
        'zh':       clean(zh)[:120] if zh else '',
        'tags':     hashtags[:8],
        'plays':    v.get('playCount', 0),
        'likes':    v.get('diggCount', 0),
        'collect':  v.get('collectCount', 0),
        'shares':   v.get('shareCount', 0),
        'comments': v.get('commentCount', 0),
        'date':     v.get('createTimeISO', '')[:10],
        'query':    query,
        'color':    QUERY_COLORS.get(query, '#888'),
    }
    data_items.append(item)

tt_data_json = json.dumps(data_items, ensure_ascii=False, separators=(',', ':'))

# Filter buttons HTML
filter_btns = f'<button class="tt-filter-btn tt-active" onclick="ttSetQuery(\'all\',this)">全部 ({total})</button>\n'
for q, color in QUERY_COLORS.items():
    if q in query_counts:
        filter_btns += f'      <button class="tt-filter-btn" onclick="ttSetQuery(\'{q}\',this)">{q} ({query_counts[q]})</button>\n'

# Module content HTML (empty tbody — filled by JS)
new_module_content = f'''    <div class="tt-controls">
      <input type="text" id="tt-search" placeholder="搜索作者、文案、标签…" oninput="ttFilter()">
      {filter_btns}      <div class="tt-range-row">
        <span>播放量</span>
        <input type="number" id="tt-min-plays" placeholder="最小" oninput="ttFilter()">
        <span class="tt-range-sep">~</span>
        <input type="number" id="tt-max-plays" placeholder="最大" oninput="ttFilter()">
      </div>
    </div>
    <div class="tt-status-bar">
      <span id="tt-rowCount">共 {total} 条</span>
      <span id="tt-pagination"></span>
    </div>
    <div class="tt-table-wrap">
      <table id="tt-table">
        <thead>
          <tr>
            <th>封面</th>
            <th onclick="ttSort(1)">作者</th>
            <th>文案 &amp; 标签</th>
            <th onclick="ttSort(3)" id="tt-th-3" class="tt-sort-desc">播放</th>
            <th onclick="ttSort(4)">点赞</th>
            <th onclick="ttSort(5)">收藏</th>
            <th onclick="ttSort(6)">分享</th>
            <th onclick="ttSort(7)">评论</th>
            <th onclick="ttSort(8)">日期</th>
            <th>搜索词</th>
          </tr>
        </thead>
        <tbody id="tt-tableBody"></tbody>
      </table>
    </div>'''

# CSS
new_css = '''
  /* ===== TikTok Module Styles ===== */
  .tt-controls { margin: 12px 0 0; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .tt-controls input[type="text"] { width: 200px; padding: 6px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; }
  .tt-controls input[type="text"]:focus { border-color: #0f3460; }
  .tt-range-row { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #666; background: #f5f5f5; border: 1px solid #ddd; border-radius: 6px; padding: 4px 10px; white-space: nowrap; }
  .tt-range-row input[type="number"] { width: 100px; padding: 2px 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px; outline: none; background: white; }
  .tt-range-row input[type="number"]:focus { border-color: #0f3460; }
  .tt-range-sep { color: #bbb; }
  .tt-filter-btn { padding: 6px 12px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.15s; white-space: nowrap; }
  .tt-filter-btn:hover, .tt-filter-btn.tt-active { background: #0f3460; color: white; border-color: #0f3460; }
  .tt-status-bar { display: flex; justify-content: space-between; align-items: center; margin: 6px 0; font-size: 13px; color: #888; }
  .tt-page-btn { padding: 3px 10px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; font-size: 12px; margin: 0 2px; }
  .tt-page-btn:hover, .tt-page-btn.tt-page-active { background: #0f3460; color: white; border-color: #0f3460; }
  .tt-table-wrap { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; margin-top: 4px; }
  #tt-table { width: 100%; border-collapse: collapse; }
  #tt-table thead tr { background: #1a1a2e; color: white; }
  #tt-table thead th { padding: 12px 14px; text-align: left; font-size: 12px; font-weight: 600; letter-spacing: 0.4px; white-space: nowrap; cursor: pointer; user-select: none; }
  #tt-table thead th:hover { background: #16213e; }
  #tt-table thead th.tt-sort-asc::after { content: ' ↑'; }
  #tt-table thead th.tt-sort-desc::after { content: ' ↓'; }
  #tt-table tbody tr { border-bottom: 1px solid #f0f0f0; transition: background 0.1s; }
  #tt-table tbody tr:hover { background: #f8f9ff; }
  #tt-table td { padding: 10px 14px; vertical-align: top; }
  .tt-thumb-cell { width: 70px; padding: 8px; vertical-align: middle; }
  .tt-thumb { width: 60px; height: 80px; object-fit: cover; border-radius: 4px; display: block; background: #eee; }
  .tt-author { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
  .tt-author a { font-weight: 600; color: #0f3460; text-decoration: none; font-size: 13px; }
  .tt-author a:hover { text-decoration: underline; }
  .tt-fans { font-size: 12px; color: #888; margin-top: 3px; }
  .tt-video-text { color: #1a1a2e; text-decoration: none; font-size: 13px; line-height: 1.45; display: block; }
  .tt-video-text:hover { color: #0f3460; }
  .tt-text-zh { font-size: 12px; color: #666; margin-top: 3px; line-height: 1.4; }
  .tt-hashtags { margin-top: 5px; display: flex; flex-wrap: wrap; gap: 4px; }
  .tt-tag { background: #eef2ff; color: #3d5af1; border-radius: 3px; padding: 1px 6px; font-size: 11px; }
  .tt-num-cell { text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; white-space: nowrap; }
  .tt-date-cell { color: #888; font-size: 12px; white-space: nowrap; }
  .tt-badge-verified { background: #3498db; color: white; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: 700; display: inline-block; }
  .tt-query-badge { display: inline-block; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 500; }
  /* ===== End TikTok Module Styles ===== */'''

# JS (data array + pagination renderer)
new_js = f'''
  // ===== TikTok Module JS =====
  const TT_DATA = {tt_data_json};

  let ttFiltered = TT_DATA.slice();
  let ttPage = 0;
  const TT_PAGE_SIZE = 50;
  let ttSortCol = 3, ttSortDir = -1;
  let ttQuery = 'all', ttSearch = '';
  let ttInitialized = false;

  function ttFmtNum(n) {{
    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
    return n ? String(n) : '0';
  }}

  function ttEsc(s) {{
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}

  function ttRenderPage() {{
    const start = ttPage * TT_PAGE_SIZE;
    const slice = ttFiltered.slice(start, start + TT_PAGE_SIZE);
    const tbody = document.getElementById('tt-tableBody');

    tbody.innerHTML = slice.map(v => {{
      const cover = v.cover
        ? `<a href="${{ttEsc(v.url)}}" target="_blank"><img src="${{ttEsc(v.cover)}}" class="tt-thumb" loading="lazy" onerror="this.style.display='none'"></a>`
        : '';
      const verified = v.verified ? '<span class="tt-badge-verified">✓</span> ' : '';
      const fans = v.fans ? `<div class="tt-fans">${{ttFmtNum(v.fans)}} 粉</div>` : '';
      const zh   = v.zh  ? `<div class="tt-text-zh">${{ttEsc(v.zh)}}</div>` : '';
      const tags  = v.tags.map(t => `<span class="tt-tag">${{ttEsc(t)}}</span>`).join('');
      const tagsDiv = tags ? `<div class="tt-hashtags">${{tags}}</div>` : '';
      return `<tr>
        <td class="tt-thumb-cell">${{cover}}</td>
        <td><div class="tt-author">${{verified}}<a href="${{ttEsc(v.profile)}}" target="_blank">@${{ttEsc(v.author)}}</a></div>${{fans}}</td>
        <td><a href="${{ttEsc(v.url)}}" target="_blank" class="tt-video-text">${{ttEsc(v.text)}}</a>${{zh}}${{tagsDiv}}</td>
        <td class="tt-num-cell">${{ttFmtNum(v.plays)}}</td>
        <td class="tt-num-cell">${{ttFmtNum(v.likes)}}</td>
        <td class="tt-num-cell">${{ttFmtNum(v.collect)}}</td>
        <td class="tt-num-cell">${{ttFmtNum(v.shares)}}</td>
        <td class="tt-num-cell">${{v.comments}}</td>
        <td class="tt-date-cell">${{v.date}}</td>
        <td><span class="tt-query-badge" style="background:${{v.color}}">${{v.query}}</span></td>
      </tr>`;
    }}).join('');

    // Update count and pagination
    const total = ttFiltered.length;
    const totalPages = Math.ceil(total / TT_PAGE_SIZE);
    document.getElementById('tt-rowCount').textContent = `共 ${{total}} 条`;

    let pgHtml = '';
    if (totalPages > 1) {{
      pgHtml += ttPage > 0 ? `<button class="tt-page-btn" onclick="ttGoPage(${{ttPage-1}})">‹ 上一页</button>` : '';
      // Show up to 7 page buttons around current
      const lo = Math.max(0, ttPage - 3), hi = Math.min(totalPages - 1, ttPage + 3);
      for (let i = lo; i <= hi; i++) {{
        pgHtml += `<button class="tt-page-btn${{i===ttPage?' tt-page-active':''}}" onclick="ttGoPage(${{i}})">${{i+1}}</button>`;
      }}
      pgHtml += ttPage < totalPages - 1 ? `<button class="tt-page-btn" onclick="ttGoPage(${{ttPage+1}})">下一页 ›</button>` : '';
    }}
    document.getElementById('tt-pagination').innerHTML = pgHtml;
  }}

  function ttApplyFilters() {{
    const s = ttSearch.toLowerCase();
    const minP = parseInt(document.getElementById('tt-min-plays').value) || 0;
    const maxP = parseInt(document.getElementById('tt-max-plays').value) || Infinity;
    ttFiltered = TT_DATA.filter(v => {{
      if (ttQuery !== 'all' && v.query !== ttQuery) return false;
      if (s && !(v.author+v.text+v.zh+v.tags.join(' ')).toLowerCase().includes(s)) return false;
      if (v.plays < minP) return false;
      if (v.plays > maxP) return false;
      return true;
    }});
    // Re-apply sort
    ttApplySort();
  }}

  function ttApplySort() {{
    const cols = [null,'author','text','plays','likes','collect','shares','comments','date','query'];
    const key = cols[ttSortCol];
    if (key) {{
      ttFiltered.sort((a, b) => {{
        const av = a[key], bv = b[key];
        if (typeof av === 'number') return (av - bv) * ttSortDir;
        return String(av).localeCompare(String(bv)) * ttSortDir;
      }});
    }}
    ttPage = 0;
    ttRenderPage();
  }}

  function ttFilter() {{
    ttSearch = document.getElementById('tt-search').value;
    ttApplyFilters();
  }}

  function ttSetQuery(q, btn) {{
    ttQuery = q;
    document.querySelectorAll('.tt-filter-btn').forEach(b => b.classList.remove('tt-active'));
    btn.classList.add('tt-active');
    ttApplyFilters();
  }}

  function ttSort(col) {{
    if (ttSortCol === col) ttSortDir *= -1; else {{ ttSortCol = col; ttSortDir = -1; }}
    document.querySelectorAll('#tt-table thead th').forEach(t => t.classList.remove('tt-sort-asc','tt-sort-desc'));
    document.querySelectorAll('#tt-table thead th')[col].classList.add(ttSortDir===1?'tt-sort-asc':'tt-sort-desc');
    ttApplySort();
  }}

  function ttGoPage(p) {{
    ttPage = p;
    ttRenderPage();
    document.getElementById('content-tiktok').scrollIntoView({{behavior:'smooth', block:'start'}});
  }}

  // 懒加载：首次展开模块时由 toggleModule 触发 ttApplySort()
  // ===== End TikTok Module JS ====='''

# ---- Patch the V2 HTML ----
with open('nex_playground_pr_research_v2.html', encoding='utf-8') as f:
    html = f.read()

# 1. Replace entire content-tiktok div inner HTML
html = re.sub(
    r'(<div class="module-content" id="content-tiktok">).*?(</div>\n</div>\n\n<!-- 模块 3)',
    r'\1\n' + new_module_content + r'\n  </div>\n</div>\n\n<!-- 模块 3',
    html,
    flags=re.DOTALL
)

# 2. Fix counts
html = re.sub(r'(<div class="num" id="tiktok-count">)\d+(</div>)', rf'\g<1>{total}\2', html)
html = re.sub(r'(<span class="module-count" id="tiktok-module-count">)\d+ 条(</span>)', rf'\g<1>{total} 条\2', html)

# 3. Replace CSS block (always replace to keep it fresh)
html = re.sub(
    r'/\* ===== TikTok Module Styles =====.*?===== End TikTok Module Styles ===== \*/',
    new_css.strip(),
    html, flags=re.DOTALL
)
# If no existing block, inject before </style>
if '/* ===== TikTok Module Styles =====' not in html:
    html = html.replace('</style>', new_css + '\n</style>', 1)

# 4. Replace JS block (always replace to keep it fresh)
html = re.sub(
    r'// ===== TikTok Module JS =====.*?// ===== End TikTok Module JS =====',
    new_js.strip(),
    html, flags=re.DOTALL
)
# If no existing block, inject before last </script>
if '// ===== TikTok Module JS =====' not in html:
    last_script_close = html.rfind('</script>')
    html = html[:last_script_close] + new_js + '\n' + html[last_script_close:]

# 5. Remove any stale old TikTok JS referencing deleted elements
for stale in ['getElementById(\'search-tiktok\')', 'getElementById(\'tiktok-table\')']:
    if stale in html:
        print(f'WARNING: stale reference found: {stale}')

with open('nex_playground_pr_research_v2.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done! Videos: {total}, Pages: {-(-total//50)}")
print(f"Plays: {fmt_num(sum(v.get('playCount',0) for v in videos))}")
