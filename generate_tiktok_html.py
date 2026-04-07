import json
from datetime import datetime

with open('tiktok_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)

videos.sort(key=lambda v: v.get('playCount', 0), reverse=True)

total_plays = sum(v.get('playCount', 0) for v in videos)
total_likes = sum(v.get('diggCount', 0) for v in videos)
total_shares = sum(v.get('shareCount', 0) for v in videos)
verified_count = sum(1 for v in videos if v.get('authorMeta', {}).get('verified'))
nexpartner_count = sum(1 for v in videos if any(
    h.get('name', '').lower() in ['nexpartner', 'nex partner']
    for h in v.get('hashtags', [])
))

def fmt_num(n):
    if n >= 1_000_000:
        return f'{n/1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n/1_000:.1f}K'
    return str(n)

rows = []
for v in videos:
    a = v.get('authorMeta', {})
    hashtags = [h.get('name', '') for h in v.get('hashtags', []) if h.get('name')]
    is_partner = any(h.lower() in ['nexpartner', 'nex partner'] for h in hashtags)
    verified = a.get('verified', False)
    text = v.get('text', '').replace('<', '&lt;').replace('>', '&gt;')
    date_str = v.get('createTimeISO', '')[:10]
    url = v.get('webVideoUrl', '#')
    profile_url = a.get('profileUrl', '#')
    query = v.get('searchQuery', '')
    query_color = {'nex playground': '#3498db', 'nexplayground': '#2ecc71', 'nex partner': '#e67e22'}.get(query, '#888')

    partner_badge = '<span class="badge badge-partner">合作</span>' if is_partner else ''
    verified_badge = '<span class="badge badge-verified">✓</span>' if verified else ''

    tag_html = ''.join(f'<span class="tag">{h}</span>' for h in hashtags[:8])
    text_short = text[:120] + ('…' if len(text) > 120 else '')

    row = f'''<tr data-plays="{v.get('playCount', 0)}" data-query="{query}">
      <td>
        <div class="author">
          {verified_badge}<a href="{profile_url}" target="_blank">@{a.get('name', '')}</a>{partner_badge}
        </div>
        <div class="fans">{fmt_num(a.get('fans', 0))} 粉</div>
      </td>
      <td>
        <a href="{url}" target="_blank" class="video-text">{text_short}</a>
        <div class="hashtags">{tag_html}</div>
      </td>
      <td class="num-cell">{fmt_num(v.get('playCount', 0))}</td>
      <td class="num-cell">{fmt_num(v.get('diggCount', 0))}</td>
      <td class="num-cell">{fmt_num(v.get('shareCount', 0))}</td>
      <td class="num-cell">{v.get('commentCount', 0)}</td>
      <td class="date-cell">{date_str}</td>
      <td><span class="query-badge" style="background:{query_color}">{query}</span></td>
    </tr>'''
    rows.append(row)

today = datetime.now().strftime('%Y-%m-%d')
rows_html = '\n'.join(rows)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nex Playground TikTok 视频数据库</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      font-size: 14px;
    }}
    header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      color: white;
      padding: 32px 40px;
    }}
    header h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 8px; }}
    header .meta {{ opacity: 0.7; font-size: 13px; margin-top: 6px; }}

    .stats-bar {{
      background: white;
      border-bottom: 1px solid #e0e0e0;
      padding: 16px 40px;
      display: flex;
      gap: 40px;
      flex-wrap: wrap;
    }}
    .stat {{ text-align: center; }}
    .stat .num {{ font-size: 28px; font-weight: 700; color: #0f3460; }}
    .stat .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}

    .controls {{
      margin: 20px 40px 0;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .controls input {{
      flex: 1;
      min-width: 200px;
      padding: 8px 14px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      outline: none;
    }}
    .controls input:focus {{ border-color: #0f3460; }}
    .filter-btn {{
      padding: 8px 16px;
      border: 1px solid #ddd;
      background: white;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      transition: all 0.15s;
    }}
    .filter-btn:hover, .filter-btn.active {{ background: #0f3460; color: white; border-color: #0f3460; }}

    .row-count {{ margin: 8px 40px; font-size: 13px; color: #888; }}

    .table-wrap {{
      margin: 8px 40px 40px;
      background: white;
      border-radius: 10px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      overflow: hidden;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{ background: #1a1a2e; color: white; }}
    thead th {{
      padding: 12px 14px;
      text-align: left;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.4px;
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }}
    thead th:hover {{ background: #16213e; }}
    thead th.sort-asc::after {{ content: ' ↑'; }}
    thead th.sort-desc::after {{ content: ' ↓'; }}
    tbody tr {{ border-bottom: 1px solid #f0f0f0; transition: background 0.1s; }}
    tbody tr:hover {{ background: #f8f9ff; }}
    tbody tr.hidden {{ display: none; }}
    td {{ padding: 10px 14px; vertical-align: top; }}

    .author {{ display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
    .author a {{ font-weight: 600; color: #0f3460; text-decoration: none; font-size: 13px; }}
    .author a:hover {{ text-decoration: underline; }}
    .fans {{ font-size: 12px; color: #888; margin-top: 3px; }}
    .video-text {{ color: #1a1a2e; text-decoration: none; font-size: 13px; line-height: 1.45; display: block; }}
    .video-text:hover {{ color: #0f3460; }}
    .hashtags {{ margin-top: 5px; display: flex; flex-wrap: wrap; gap: 4px; }}
    .tag {{
      background: #eef2ff;
      color: #3d5af1;
      border-radius: 3px;
      padding: 1px 6px;
      font-size: 11px;
    }}
    .num-cell {{ text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; white-space: nowrap; }}
    .date-cell {{ color: #888; font-size: 12px; white-space: nowrap; }}
    .badge {{
      display: inline-block;
      border-radius: 3px;
      padding: 1px 5px;
      font-size: 10px;
      font-weight: 700;
    }}
    .badge-verified {{ background: #3498db; color: white; }}
    .badge-partner {{ background: #e67e22; color: white; }}
    .query-badge {{
      display: inline-block;
      color: white;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 500;
    }}
  </style>
</head>
<body>

<header>
  <h1>🎮 Nex Playground TikTok 视频数据库</h1>
  <div class="meta">ASIN B0D2JGYX3F &nbsp;·&nbsp; 抓取于 {today} &nbsp;·&nbsp; 数据来源 Apify clockworks/tiktok-scraper &nbsp;·&nbsp; 搜索词：nex playground / nexplayground / nex partner</div>
</header>

<div class="stats-bar">
  <div class="stat"><div class="num">{len(videos)}</div><div class="label">视频总数</div></div>
  <div class="stat"><div class="num">{fmt_num(total_plays)}</div><div class="label">总播放量</div></div>
  <div class="stat"><div class="num">{fmt_num(total_likes)}</div><div class="label">总点赞数</div></div>
  <div class="stat"><div class="num">{fmt_num(total_shares)}</div><div class="label">总分享数</div></div>
  <div class="stat"><div class="num">{verified_count}</div><div class="label">认证账号</div></div>
  <div class="stat"><div class="num">{nexpartner_count}</div><div class="label">#nexpartner 合作</div></div>
</div>

<div class="controls">
  <input type="text" id="search" placeholder="搜索作者、文案、话题标签…" oninput="filterTable()">
  <button class="filter-btn active" onclick="setQuery('all', this)">全部 ({len(videos)})</button>
  <button class="filter-btn" onclick="setQuery('nex playground', this)">nex playground</button>
  <button class="filter-btn" onclick="setQuery('nexplayground', this)">nexplayground</button>
  <button class="filter-btn" onclick="setQuery('nex partner', this)">nex partner</button>
</div>
<div class="row-count" id="rowCount">共 {len(videos)} 条</div>

<div class="table-wrap">
  <table id="mainTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">作者</th>
        <th>文案 &amp; 标签</th>
        <th onclick="sortTable(2)" class="sort-desc">播放 ↓</th>
        <th onclick="sortTable(3)">点赞</th>
        <th onclick="sortTable(4)">分享</th>
        <th onclick="sortTable(5)">评论</th>
        <th onclick="sortTable(6)">日期</th>
        <th>搜索词</th>
      </tr>
    </thead>
    <tbody id="tableBody">
{rows_html}
    </tbody>
  </table>
</div>

<script>
let currentQuery = 'all';
let sortCol = 2, sortDir = -1;

function filterTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  const rows = document.querySelectorAll('#tableBody tr');
  let visible = 0;
  rows.forEach(r => {{
    const queryMatch = currentQuery === 'all' || r.dataset.query === currentQuery;
    const textMatch = !q || r.textContent.toLowerCase().includes(q);
    if (queryMatch && textMatch) {{ r.classList.remove('hidden'); visible++; }}
    else r.classList.add('hidden');
  }});
  document.getElementById('rowCount').textContent = '共 ' + visible + ' 条';
}}

function setQuery(q, btn) {{
  currentQuery = q;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterTable();
}}

function parseNum(s) {{
  s = s.trim();
  if (s.endsWith('M')) return parseFloat(s) * 1e6;
  if (s.endsWith('K')) return parseFloat(s) * 1e3;
  return parseFloat(s) || 0;
}}

function sortTable(col) {{
  if (sortCol === col) sortDir *= -1;
  else {{ sortCol = col; sortDir = -1; }}
  const ths = document.querySelectorAll('thead th');
  ths.forEach(t => {{ t.classList.remove('sort-asc', 'sort-desc'); t.textContent = t.textContent.replace(/ [↑↓]$/, ''); }});
  ths[col].classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');

  const tbody = document.getElementById('tableBody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {{
    const av = a.cells[col]?.textContent.trim() || '';
    const bv = b.cells[col]?.textContent.trim() || '';
    const an = parseNum(av), bn = parseNum(bv);
    if (!isNaN(an) && !isNaN(bn) && (an !== 0 || bn !== 0)) return (an - bn) * sortDir;
    return av.localeCompare(bv) * sortDir;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>"""

with open('tiktok_nex_videos.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done! tiktok_nex_videos.html generated")
print(f"Videos: {len(videos)}")
print(f"Total plays: {fmt_num(total_plays)}")
print(f"Verified creators: {verified_count}")
print(f"#nexpartner: {nexpartner_count}")
print(f"\nTop 10 by plays:")
for v in videos[:10]:
    a = v.get('authorMeta', {})
    print(f"  {fmt_num(v.get('playCount',0)):>8}  @{a.get('name',''):25s}  {v.get('text','')[:60]}")
