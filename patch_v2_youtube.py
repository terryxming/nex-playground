"""
patch_v2_youtube.py
替换 V2 HTML 中静态 YouTube 模块 → 动态 JS 数据数组版本
新增：zh 标题翻译显示 + 观看量区间筛选
"""
import json, re
from collections import Counter

QUERY_COLORS = {
    'nex playground':          '#3498db',
    'nex playground review':   '#9b59b6',
    'nex playground unboxing': '#e74c3c',
    'nex playground game':     '#1abc9c',
    'nex playground kids':     '#f39c12',
}

def clean(s):
    return ''.join(c if ord(c) >= 32 else ' ' for c in (s or '')).strip()

# ---- Load data ----
with open('youtube_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)

videos.sort(key=lambda v: v.get('viewCount') or 0, reverse=True)

total = len(videos)
query_counts = Counter(v.get('searchQuery', '') for v in videos)

# ---- Build JS data array ----
data_items = []
for v in videos:
    query = v.get('searchQuery', '')
    item = {
        'url':        v.get('url', ''),
        'thumb':      (v.get('thumbnailUrl', '') or '').split('?')[0],
        'title':      clean(v.get('title', ''))[:120],
        'zh':         clean(v.get('zh', ''))[:120],
        'channel':    clean(v.get('channelName', '')),
        'channelUrl': v.get('channelUrl', ''),
        'subs':       v.get('numberOfSubscribers') or 0,
        'views':      v.get('viewCount') or 0,
        'likes':      v.get('likes') or 0,
        'comments':   v.get('commentsCount') or 0,
        'duration':   v.get('duration', ''),
        'date':       (v.get('date', '') or '')[:10],
        'query':      query,
        'color':      QUERY_COLORS.get(query, '#888'),
    }
    data_items.append(item)

yt_data_json = json.dumps(data_items, ensure_ascii=False, separators=(',', ':'))

# ---- Filter buttons ----
filter_btns = f'<button class="yt-filter-btn yt-active" onclick="ytSetQuery(\'all\',this)">全部 ({total})</button>\n'
for q, color in QUERY_COLORS.items():
    if q in query_counts:
        filter_btns += f'      <button class="yt-filter-btn" onclick="ytSetQuery(\'{q}\',this)">{q} ({query_counts[q]})</button>\n'

# ---- Module content HTML ----
new_module_content = f'''    <div class="yt-controls">
      <input type="text" id="yt-search" placeholder="搜索频道、标题…" oninput="ytFilter()">
      {filter_btns}      <div class="yt-range-row">
        <span>观看量</span>
        <input type="number" id="yt-min-views" placeholder="最小" oninput="ytFilter()">
        <span class="yt-range-sep">~</span>
        <input type="number" id="yt-max-views" placeholder="最大" oninput="ytFilter()">
      </div>
    </div>
    <div class="yt-status-bar">
      <span id="yt-rowCount">共 {total} 条</span>
      <span id="yt-pagination"></span>
    </div>
    <div class="yt-table-wrap">
      <table id="yt-table">
        <thead>
          <tr>
            <th>封面</th>
            <th onclick="ytSort(1)">频道</th>
            <th>标题</th>
            <th onclick="ytSort(3)" id="yt-th-3" class="yt-sort-desc">观看</th>
            <th onclick="ytSort(4)">点赞</th>
            <th onclick="ytSort(5)">评论</th>
            <th onclick="ytSort(6)">时长</th>
            <th onclick="ytSort(7)">日期</th>
            <th>搜索词</th>
          </tr>
        </thead>
        <tbody id="yt-tableBody"></tbody>
      </table>
    </div>'''

# ---- CSS ----
new_css = '''
  /* ===== YouTube Module Styles ===== */
  .yt-controls { margin: 12px 0 0; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .yt-controls input[type="text"] { width: 200px; padding: 6px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; }
  .yt-controls input[type="text"]:focus { border-color: #c4302b; }
  .yt-filter-btn { padding: 6px 12px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.15s; white-space: nowrap; }
  .yt-filter-btn:hover, .yt-filter-btn.yt-active { background: #c4302b; color: white; border-color: #c4302b; }
  .yt-range-row { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #666; background: #f5f5f5; border: 1px solid #ddd; border-radius: 6px; padding: 4px 10px; white-space: nowrap; }
  .yt-range-row input[type="number"] { width: 100px; padding: 2px 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px; outline: none; background: white; }
  .yt-range-row input[type="number"]:focus { border-color: #c4302b; }
  .yt-range-sep { color: #bbb; }
  .yt-status-bar { display: flex; justify-content: space-between; align-items: center; margin: 6px 0; font-size: 13px; color: #888; }
  .yt-page-btn { padding: 3px 10px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; font-size: 12px; margin: 0 2px; }
  .yt-page-btn:hover, .yt-page-btn.yt-page-active { background: #c4302b; color: white; border-color: #c4302b; }
  .yt-table-wrap { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; margin-top: 4px; }
  #yt-table { width: 100%; border-collapse: collapse; }
  #yt-table thead tr { background: #1a1a2e; color: white; }
  #yt-table thead th { padding: 12px 14px; text-align: left; font-size: 12px; font-weight: 600; letter-spacing: 0.4px; white-space: nowrap; cursor: pointer; user-select: none; }
  #yt-table thead th:hover { background: #16213e; }
  #yt-table thead th.yt-sort-asc::after { content: ' \u2191'; }
  #yt-table thead th.yt-sort-desc::after { content: ' \u2193'; }
  #yt-table tbody tr { border-bottom: 1px solid #f0f0f0; transition: background 0.1s; }
  #yt-table tbody tr:hover { background: #fff8f8; }
  #yt-table td { padding: 10px 14px; vertical-align: top; }
  .yt-thumb-cell { width: 120px; padding: 8px; vertical-align: middle; }
  .yt-thumb { width: 110px; height: 62px; object-fit: cover; border-radius: 4px; display: block; background: #eee; }
  .yt-channel a { font-weight: 600; color: #c4302b; text-decoration: none; font-size: 13px; }
  .yt-channel a:hover { text-decoration: underline; }
  .yt-subs { font-size: 12px; color: #888; margin-top: 3px; }
  .yt-title a { color: #1a1a2e; text-decoration: none; font-size: 13px; line-height: 1.45; display: block; }
  .yt-title a:hover { color: #c4302b; }
  .yt-title-zh { font-size: 12px; color: #666; margin-top: 3px; line-height: 1.4; }
  .yt-num-cell { text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; white-space: nowrap; }
  .yt-date-cell { color: #888; font-size: 12px; white-space: nowrap; }
  .yt-duration { color: #555; font-size: 12px; white-space: nowrap; }
  .yt-query-badge { display: inline-block; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 500; }
  /* ===== End YouTube Module Styles ===== */'''

# ---- JS ----
new_js = f'''
  // ===== YouTube Module JS =====
  const YT_DATA = {yt_data_json};

  let ytFiltered = YT_DATA.slice();
  let ytPage = 0;
  const YT_PAGE_SIZE = 50;
  let ytSortCol = 3, ytSortDir = -1;
  let ytQuery = 'all', ytSearch = '';
  let ytInitialized = false;

  function ytFmtNum(n) {{
    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
    return n ? String(n) : '0';
  }}

  function ytEsc(s) {{
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}

  function ytRenderPage() {{
    const start = ytPage * YT_PAGE_SIZE;
    const slice = ytFiltered.slice(start, start + YT_PAGE_SIZE);
    const tbody = document.getElementById('yt-tableBody');

    tbody.innerHTML = slice.map(v => {{
      const thumb = v.thumb
        ? `<a href="${{ytEsc(v.url)}}" target="_blank"><img src="${{ytEsc(v.thumb)}}" class="yt-thumb" loading="lazy" onerror="this.style.display='none'"></a>`
        : '';
      const subs = v.subs ? `<div class="yt-subs">${{ytFmtNum(v.subs)}} 订阅</div>` : '';
      const zh   = v.zh   ? `<div class="yt-title-zh">${{ytEsc(v.zh)}}</div>` : '';
      return `<tr>
        <td class="yt-thumb-cell">${{thumb}}</td>
        <td class="yt-channel"><a href="${{ytEsc(v.channelUrl)}}" target="_blank">${{ytEsc(v.channel)}}</a>${{subs}}</td>
        <td class="yt-title"><a href="${{ytEsc(v.url)}}" target="_blank">${{ytEsc(v.title)}}</a>${{zh}}</td>
        <td class="yt-num-cell">${{ytFmtNum(v.views)}}</td>
        <td class="yt-num-cell">${{ytFmtNum(v.likes)}}</td>
        <td class="yt-num-cell">${{v.comments}}</td>
        <td class="yt-duration">${{ytEsc(v.duration)}}</td>
        <td class="yt-date-cell">${{v.date}}</td>
        <td><span class="yt-query-badge" style="background:${{v.color}}">${{ytEsc(v.query)}}</span></td>
      </tr>`;
    }}).join('');

    const total = ytFiltered.length;
    const totalPages = Math.ceil(total / YT_PAGE_SIZE);
    document.getElementById('yt-rowCount').textContent = `共 ${{total}} 条`;

    let pgHtml = '';
    if (totalPages > 1) {{
      pgHtml += ytPage > 0 ? `<button class="yt-page-btn" onclick="ytGoPage(${{ytPage-1}})">&lsaquo; 上一页</button>` : '';
      const lo = Math.max(0, ytPage - 3), hi = Math.min(totalPages - 1, ytPage + 3);
      for (let i = lo; i <= hi; i++) {{
        pgHtml += `<button class="yt-page-btn${{i===ytPage?' yt-page-active':''}}" onclick="ytGoPage(${{i}})">${{i+1}}</button>`;
      }}
      pgHtml += ytPage < totalPages - 1 ? `<button class="yt-page-btn" onclick="ytGoPage(${{ytPage+1}})">下一页 &rsaquo;</button>` : '';
    }}
    document.getElementById('yt-pagination').innerHTML = pgHtml;
  }}

  function ytApplyFilters() {{
    const s = ytSearch.toLowerCase();
    const minV = parseInt(document.getElementById('yt-min-views').value) || 0;
    const maxV = parseInt(document.getElementById('yt-max-views').value) || Infinity;
    ytFiltered = YT_DATA.filter(v => {{
      if (ytQuery !== 'all' && v.query !== ytQuery) return false;
      if (s && !(v.title + v.channel + v.zh).toLowerCase().includes(s)) return false;
      if (v.views < minV) return false;
      if (v.views > maxV) return false;
      return true;
    }});
    ytApplySort();
  }}

  function ytApplySort() {{
    const cols = [null,'channel','title','views','likes','comments','duration','date','query'];
    const key = cols[ytSortCol];
    if (key) {{
      ytFiltered.sort((a, b) => {{
        const av = a[key], bv = b[key];
        if (typeof av === 'number') return (av - bv) * ytSortDir;
        return String(av).localeCompare(String(bv)) * ytSortDir;
      }});
    }}
    ytPage = 0;
    ytRenderPage();
  }}

  function ytFilter() {{
    ytSearch = document.getElementById('yt-search').value;
    ytApplyFilters();
  }}

  function ytSetQuery(q, btn) {{
    ytQuery = q;
    document.querySelectorAll('.yt-filter-btn').forEach(b => b.classList.remove('yt-active'));
    btn.classList.add('yt-active');
    ytApplyFilters();
  }}

  function ytSort(col) {{
    if (ytSortCol === col) ytSortDir *= -1; else {{ ytSortCol = col; ytSortDir = -1; }}
    document.querySelectorAll('#yt-table thead th').forEach(t => t.classList.remove('yt-sort-asc','yt-sort-desc'));
    document.querySelectorAll('#yt-table thead th')[col].classList.add(ytSortDir===1?'yt-sort-asc':'yt-sort-desc');
    ytApplySort();
  }}

  function ytGoPage(p) {{
    ytPage = p;
    ytRenderPage();
    document.getElementById('content-youtube').scrollIntoView({{behavior:'smooth', block:'start'}});
  }}

  // 懒加载：首次展开模块时由 toggleModule 触发 ytApplySort()
  // ===== End YouTube Module JS ====='''

# ---- Patch HTML ----
with open('nex_playground_pr_research_v2.html', encoding='utf-8') as f:
    html = f.read()

# 1. Replace module-content inner HTML
html = re.sub(
    r'(<div class="module-content" id="content-youtube">).*?(</div>\n</div>\n\n<!-- 模块 4)',
    r'\1\n' + new_module_content + r'\n  </div>\n</div>\n\n<!-- 模块 4',
    html,
    flags=re.DOTALL
)

# 2. Fix youtube-count stat
html = re.sub(r'(<div class="num" id="youtube-count">)\d+(</div>)', rf'\g<1>{total}\2', html)
html = re.sub(
    r'(▶️ YouTube 视频</span>\n\s+<span class="module-count">)\d+ 条(</span>)',
    rf'\g<1>{total} 条\2',
    html
)

# 3. Replace CSS block
html = re.sub(
    r'/\* ===== YouTube Module Styles =====.*?===== End YouTube Module Styles ===== \*/',
    new_css.strip(),
    html, flags=re.DOTALL
)
if '/* ===== YouTube Module Styles =====' not in html:
    html = html.replace('</style>', new_css + '\n</style>', 1)

# 4. Replace JS block
html = re.sub(
    r'// ===== YouTube Module JS =====.*?// ===== End YouTube Module JS =====',
    new_js.strip(),
    html, flags=re.DOTALL
)
if '// ===== YouTube Module JS =====' not in html:
    last_script_close = html.rfind('</script>')
    html = html[:last_script_close] + new_js + '\n' + html[last_script_close:]

with open('nex_playground_pr_research_v2.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'[done] YouTube module patched: {total} videos')
