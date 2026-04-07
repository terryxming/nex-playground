import json, os
from datetime import datetime

with open('tiktok_raw_new.json', encoding='utf-8') as f:
    raw = json.load(f)

cache_file = 'translations_cache.json'
if os.path.exists(cache_file):
    with open(cache_file, encoding='utf-8') as f:
        translations = json.load(f)
else:
    translations = {}

# ── 去重（按视频 ID）──────────────────────────────────────
seen = {}
for v in raw:
    vid = v.get('id')
    if vid and vid not in seen:
        seen[vid] = v
deduped = list(seen.values())
print(f'Raw: {len(raw)} → After dedup: {len(deduped)}')

# ── 相关性过滤 ────────────────────────────────────────────
# 必须包含以下任一关键词（文案 + 话题标签合并检查）
def is_relevant(v):
    text = (v.get('text') or '').lower()
    hashtags = ' '.join(h.get('name', '').lower() for h in v.get('hashtags', []))
    combined = text + ' ' + hashtags

    # 最强信号：直接包含产品名（无歧义）
    if 'nex playground' in combined or 'nexplayground' in combined:
        return True

    # nexpartner / nex partner 话题标签：必须同时出现 playground 才算
    # （防止泰国明星 Nex、Nexxus 护发、NexCard 等污染）
    if ('nexpartner' in combined or 'nex partner' in combined):
        if 'playground' in combined:
            return True
        return False

    return False

relevant = [v for v in deduped if is_relevant(v)]
removed = [v for v in deduped if not is_relevant(v)]
print(f'Relevant: {len(relevant)}  |  Removed (irrelevant): {len(removed)}')

# 打印被移除的样本（用于验证，ASCII safe）
print('\n── 移除的视频（前20条）──')
for v in removed[:20]:
    text = (v.get('text') or '').encode('ascii', errors='replace').decode()[:80]
    tags = [h.get('name','').encode('ascii','replace').decode() for h in v.get('hashtags', [])][:5]
    q = v.get('searchQuery', '')
    print(f'  [{q}] {text}  tags={tags}')

# ── 按播放量排序 ───────────────────────────────────────────
relevant.sort(key=lambda v: v.get('playCount', 0), reverse=True)

# ── 统计 ──────────────────────────────────────────────────
total_plays    = sum(v.get('playCount', 0)   for v in relevant)
total_likes    = sum(v.get('diggCount', 0)   for v in relevant)
total_collects = sum(v.get('collectCount', 0) for v in relevant)
total_shares   = sum(v.get('shareCount', 0)  for v in relevant)
verified_count    = sum(1 for v in relevant if v.get('authorMeta', {}).get('verified'))
nexpartner_count  = sum(1 for v in relevant if any(
    h.get('name', '').lower() in ['nexpartner', 'nex partner']
    for h in v.get('hashtags', [])
))

from collections import Counter
query_counts = Counter(v.get('searchQuery') for v in relevant)

def fmt(n):
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}K'
    return str(n)

print(f'\n── 过滤后统计 ──')
print(f'视频数: {len(relevant)}')
print(f'总播放: {fmt(total_plays)}')
print(f'总点赞: {fmt(total_likes)}')
print(f'总分享: {fmt(total_shares)}')
print(f'认证账号: {verified_count}')
print(f'#nexpartner: {nexpartner_count}')
print(f'各关键词分布: {dict(query_counts)}')
print(f'\nTop 10:')
for v in relevant[:10]:
    a = v.get('authorMeta', {})
    name = (a.get('name') or '').encode('ascii','replace').decode()
    txt  = (v.get('text') or '').encode('ascii','replace').decode()[:55]
    print(f'  {fmt(v.get("playCount",0)):>8}  @{name:25s}  {txt}')

# ── 保存过滤后 JSON ────────────────────────────────────────
with open('tiktok_nex_videos.json', 'w', encoding='utf-8') as f:
    json.dump(relevant, f, ensure_ascii=False, indent=2)
print('\nSaved tiktok_nex_videos.json')

# ── 生成 HTML ─────────────────────────────────────────────
rows = []
for v in relevant:
    a = v.get('authorMeta', {})
    hashtags = [h.get('name', '') for h in v.get('hashtags', []) if h.get('name')]
    is_partner = any(h.lower() in ['nexpartner', 'nex partner'] for h in hashtags)
    verified = a.get('verified', False)
    text = (v.get('text') or '').replace('<', '&lt;').replace('>', '&gt;')
    date_str = (v.get('createTimeISO') or '')[:10]
    url = v.get('webVideoUrl', '#')
    profile_url = a.get('profileUrl', '#')
    query = v.get('searchQuery', '')
    query_color = {
        'nex playground':          '#3498db',
        'nexplayground':           '#2ecc71',
        'nexpartner':              '#e67e22',
        'nex playground review':   '#9b59b6',
        'nex playground unboxing': '#e74c3c',
        'nex playground game':     '#1abc9c',
        'nex playground kids':     '#f39c12',
    }.get(query, '#888')

    partner_badge  = '<span class="badge badge-partner">合作</span>'  if is_partner else ''
    verified_badge = '<span class="badge badge-verified">✓</span>'    if verified   else ''
    tag_html = ''.join(f'<span class="tag">{h}</span>' for h in hashtags[:8])
    text_short = text[:120] + ('…' if len(text) > 120 else '')
    zh = translations.get(str(v.get('id')), '')
    zh_html = f'<div class="text-zh">{zh[:120]}{"…" if len(zh)>120 else ""}</div>' if zh else ''

    cover_url = (v.get('videoMeta') or {}).get('coverUrl') or ''
    thumb = f'<a href="{url}" target="_blank"><img src="{cover_url}" class="thumb" loading="lazy" onerror="this.style.display=\'none\'"></a>' if cover_url else ''

    rows.append(f'''<tr data-plays="{v.get('playCount', 0)}" data-query="{query}">
      <td class="thumb-cell">{thumb}</td>
      <td>
        <div class="author">{verified_badge}<a href="{profile_url}" target="_blank">@{a.get('name', '')}</a>{partner_badge}</div>
        <div class="fans">{fmt(a.get('fans', 0))} 粉</div>
      </td>
      <td>
        <a href="{url}" target="_blank" class="video-text">{text_short}</a>
        {zh_html}
        <div class="hashtags">{tag_html}</div>
      </td>
      <td class="num-cell">{fmt(v.get('playCount', 0))}</td>
      <td class="num-cell">{fmt(v.get('diggCount', 0))}</td>
      <td class="num-cell">{fmt(v.get('collectCount', 0))}</td>
      <td class="num-cell">{fmt(v.get('shareCount', 0))}</td>
      <td class="num-cell">{v.get('commentCount', 0)}</td>
      <td class="date-cell">{date_str}</td>
      <td><span class="query-badge" style="background:{query_color}">{query}</span></td>
    </tr>''')

today = datetime.now().strftime('%Y-%m-%d')
rows_html = '\n'.join(rows)

# 过滤按钮
filter_btns = '<button class="filter-btn active" onclick="setQuery(\'all\', this)">全部 ({total})</button>'.format(total=len(relevant))
for q, c in sorted(query_counts.items(), key=lambda x: -x[1]):
    filter_btns += f'<button class="filter-btn" onclick="setQuery(\'{q}\', this)">{q} ({c})</button>\n  '

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nex Playground TikTok 视频数据库</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #1a1a2e; font-size: 14px; }}
    header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 32px 40px; }}
    header h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 8px; }}
    header .meta {{ opacity: 0.7; font-size: 13px; margin-top: 6px; }}
    .stats-bar {{ background: white; border-bottom: 1px solid #e0e0e0; padding: 16px 40px; display: flex; gap: 40px; flex-wrap: wrap; }}
    .stat .num {{ font-size: 28px; font-weight: 700; color: #0f3460; }}
    .stat .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
    .controls {{ margin: 20px 40px 0; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .controls input {{ flex: 1; min-width: 200px; padding: 8px 14px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; outline: none; }}
    .controls input:focus {{ border-color: #0f3460; }}
    .filter-btn {{ padding: 7px 14px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.15s; white-space: nowrap; }}
    .filter-btn:hover, .filter-btn.active {{ background: #0f3460; color: white; border-color: #0f3460; }}
    .row-count {{ margin: 8px 40px; font-size: 13px; color: #888; }}
    .table-wrap {{ margin: 8px 40px 40px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{ background: #1a1a2e; color: white; }}
    thead th {{ padding: 12px 14px; text-align: left; font-size: 12px; font-weight: 600; letter-spacing: 0.4px; white-space: nowrap; cursor: pointer; user-select: none; }}
    thead th:hover {{ background: #16213e; }}
    tbody tr {{ border-bottom: 1px solid #f0f0f0; transition: background 0.1s; }}
    tbody tr:hover {{ background: #f8f9ff; }}
    tbody tr.hidden {{ display: none; }}
    td {{ padding: 10px 14px; vertical-align: top; }}
    .thumb-cell {{ width: 70px; padding: 8px; vertical-align: middle; }}
    .thumb {{ width: 60px; height: 80px; object-fit: cover; border-radius: 4px; display: block; background: #eee; }}
    .author {{ display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
    .author a {{ font-weight: 600; color: #0f3460; text-decoration: none; font-size: 13px; }}
    .author a:hover {{ text-decoration: underline; }}
    .fans {{ font-size: 12px; color: #888; margin-top: 3px; }}
    .video-text {{ color: #1a1a2e; text-decoration: none; font-size: 13px; line-height: 1.45; display: block; }}
    .video-text:hover {{ color: #0f3460; }}
    .text-zh {{ font-size: 12px; color: #666; margin-top: 3px; line-height: 1.4; }}
    .hashtags {{ margin-top: 5px; display: flex; flex-wrap: wrap; gap: 4px; }}
    .tag {{ background: #eef2ff; color: #3d5af1; border-radius: 3px; padding: 1px 6px; font-size: 11px; }}
    .num-cell {{ text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; white-space: nowrap; }}
    .date-cell {{ color: #888; font-size: 12px; white-space: nowrap; }}
    .badge {{ display: inline-block; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: 700; }}
    .badge-verified {{ background: #3498db; color: white; }}
    .badge-partner {{ background: #e67e22; color: white; }}
    .query-badge {{ display: inline-block; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 500; }}
  </style>
</head>
<body>
<header>
  <h1>🎮 Nex Playground TikTok 视频数据库</h1>
  <div class="meta">ASIN B0D2JGYX3F &nbsp;·&nbsp; 抓取于 {today} &nbsp;·&nbsp; Apify clockworks/tiktok-scraper &nbsp;·&nbsp; 7个关键词 × 500条，过滤后保留相关视频</div>
</header>
<div class="stats-bar">
  <div class="stat"><div class="num">{len(relevant)}</div><div class="label">有效视频</div></div>
  <div class="stat"><div class="num">{fmt(total_plays)}</div><div class="label">总播放量</div></div>
  <div class="stat"><div class="num">{fmt(total_likes)}</div><div class="label">总点赞数</div></div>
  <div class="stat"><div class="num">{fmt(total_collects)}</div><div class="label">总收藏数</div></div>
  <div class="stat"><div class="num">{fmt(total_shares)}</div><div class="label">总分享数</div></div>
  <div class="stat"><div class="num">{verified_count}</div><div class="label">认证账号</div></div>
  <div class="stat"><div class="num">{nexpartner_count}</div><div class="label">#nexpartner 合作</div></div>
</div>
<div class="controls">
  <input type="text" id="search" placeholder="搜索作者、文案、话题标签…" oninput="filterTable()">
  {filter_btns}
</div>
<div class="row-count" id="rowCount">共 {len(relevant)} 条</div>
<div class="table-wrap">
  <table id="mainTable">
    <thead>
      <tr>
        <th>封面</th>
        <th onclick="sortTable(1)">作者</th>
        <th>文案 &amp; 标签</th>
        <th onclick="sortTable(3)" class="sort-desc">播放</th>
        <th onclick="sortTable(4)">点赞</th>
        <th onclick="sortTable(5)">收藏</th>
        <th onclick="sortTable(6)">分享</th>
        <th onclick="sortTable(7)">评论</th>
        <th onclick="sortTable(8)">日期</th>
        <th>搜索词</th>
      </tr>
    </thead>
    <tbody id="tableBody">
{rows_html}
    </tbody>
  </table>
</div>
<script>
let currentQuery = 'all', sortCol = 2, sortDir = -1;
function filterTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  const rows = document.querySelectorAll('#tableBody tr');
  let n = 0;
  rows.forEach(r => {{
    const qm = currentQuery === 'all' || r.dataset.query === currentQuery;
    const tm = !q || r.textContent.toLowerCase().includes(q);
    r.classList.toggle('hidden', !(qm && tm));
    if (qm && tm) n++;
  }});
  document.getElementById('rowCount').textContent = '共 ' + n + ' 条';
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
  if (sortCol === col) sortDir *= -1; else {{ sortCol = col; sortDir = -1; }}
  document.querySelectorAll('thead th').forEach(t => t.classList.remove('sort-asc','sort-desc'));
  document.querySelectorAll('thead th')[col].classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
  const tbody = document.getElementById('tableBody');
  Array.from(tbody.querySelectorAll('tr'))
    .sort((a, b) => {{
      const av = a.cells[col]?.textContent.trim() || '', bv = b.cells[col]?.textContent.trim() || '';
      const an = parseNum(av), bn = parseNum(bv);
      if (an || bn) return (an - bn) * sortDir;
      return av.localeCompare(bv) * sortDir;
    }})
    .forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>"""

with open('tiktok_nex_videos.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Generated tiktok_nex_videos.html')
