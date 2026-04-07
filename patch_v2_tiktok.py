"""
直接改造 V2 的 TikTok 模块：
- 把 549 行 HTML 替换为空 <tbody>
- 视频数据存成 JS 数组，动态渲染
- 分页每页 50 条
"""
import json, os, re

with open('tiktok_nex_videos.json', encoding='utf-8') as f:
    videos = json.load(f)

translations = {}
if os.path.exists('translations_cache.json'):
    with open('translations_cache.json', encoding='utf-8') as f:
        translations = json.load(f)

def fmt(n):
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}K'
    return str(n)

query_color = {
    'nex playground':          '#3498db',
    'nexplayground':           '#2ecc71',
    'nexpartner':              '#e67e22',
    'nex playground review':   '#9b59b6',
    'nex playground unboxing': '#e74c3c',
    'nex playground game':     '#1abc9c',
    'nex playground kids':     '#f39c12',
}

from collections import Counter
query_counts = Counter(v.get('searchQuery') for v in videos)

# ── 构建 JS 数据数组 ──────────────────────────────────────
rows_data = []
for v in videos:
    vid   = str(v.get('id', ''))
    a     = v.get('authorMeta', {})
    tags  = [h.get('name', '') for h in v.get('hashtags', []) if h.get('name')]
    is_partner = any(h.lower() in ['nexpartner', 'nex partner'] for h in tags)
    text  = (v.get('text') or '').replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    zh    = (translations.get(vid) or '').replace('\\', '\\\\').replace('"', '\\"')
    query = v.get('searchQuery', '')
    rows_data.append({
        'vid':     vid,
        'cover':   (v.get('videoMeta') or {}).get('coverUrl', ''),
        'url':     v.get('webVideoUrl', '#'),
        'profile': a.get('profileUrl', '#'),
        'author':  a.get('name', ''),
        'fans':    fmt(a.get('fans', 0)),
        'verified': bool(a.get('verified')),
        'partner':  is_partner,
        'text':    text[:120] + ('…' if len(text) > 120 else ''),
        'zh':      zh[:120]   + ('…' if len(zh)   > 120 else ''),
        'tags':    tags[:8],
        'plays':   v.get('playCount', 0),
        'likes':   v.get('diggCount', 0),
        'collects':v.get('collectCount', 0),
        'shares':  v.get('shareCount', 0),
        'comments':v.get('commentCount', 0),
        'date':    (v.get('createTimeISO') or '')[:10],
        'query':   query,
        'qcolor':  query_color.get(query, '#888'),
    })

rows_js = json.dumps(rows_data, ensure_ascii=False)

# 过滤按钮 HTML
filter_btns = f"<button class='filter-btn active' onclick='tt_setQuery(\"all\",this)'>全部 ({len(videos)})</button>\n  "
for q, c in sorted(query_counts.items(), key=lambda x: -x[1]):
    filter_btns += f"<button class='filter-btn' onclick='tt_setQuery(\"{q}\",this)'>{q} ({c})</button>\n  "

# ── 新的 module-content HTML ──────────────────────────────
new_content = f"""
    <div class="controls" style="margin:16px 0 0 0">
      <input type="text" id="tt-search" placeholder="搜索作者、文案、话题标签…" oninput="tt_onSearch()" style="flex:1;min-width:180px;padding:7px 12px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none">
      {filter_btns}
    </div>
    <div class="row-count" id="tt-rowCount" style="margin:8px 0;font-size:13px;color:#888">共 {len(videos)} 条</div>
    <div class="table-wrap" style="margin:0;overflow:auto">
      <table id="tt-mainTable" style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#1a1a2e;color:white">
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap">封面</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(1)">作者</th>
            <th style="padding:10px 12px;font-size:12px">文案 &amp; 标签</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(3)">播放 ↓</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(4)">点赞</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(5)">收藏</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(6)">分享</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(7)">评论</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap;cursor:pointer" onclick="tt_sortTable(8)">日期</th>
            <th style="padding:10px 12px;font-size:12px;white-space:nowrap">搜索词</th>
          </tr>
        </thead>
        <tbody id="tt-tableBody"></tbody>
      </table>
    </div>
    <div id="tt-pagination" style="margin:10px 0 4px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:13px"></div>
"""

# ── TikTok JS ─────────────────────────────────────────────
tiktok_js = f"""
  // ── TikTok 模块 ──────────────────────────────────────
  const TT_DATA = {rows_js};
  let tt_query = 'all', tt_sortCol = 3, tt_sortDir = -1, tt_page = 0;
  let tt_filtered = TT_DATA.slice();

  function tt_fmt(n) {{
    if (n >= 1e6) return (n/1e6).toFixed(1)+'M';
    if (n >= 1e3) return (n/1e3).toFixed(1)+'K';
    return String(n);
  }}

  function tt_parseNum(s) {{
    s = (s||'').trim();
    if (s.endsWith('M')) return parseFloat(s)*1e6;
    if (s.endsWith('K')) return parseFloat(s)*1e3;
    return parseFloat(s)||0;
  }}

  function tt_makeRow(d) {{
    const thumb = d.cover
      ? `<a href="${{d.url}}" target="_blank"><img src="${{d.cover}}" style="width:56px;height:74px;object-fit:cover;border-radius:4px;display:block;background:#eee" loading="lazy" onerror="this.style.display='none'"></a>`
      : '';
    const vbadge = d.verified ? '<span style="background:#3498db;color:white;border-radius:3px;padding:1px 4px;font-size:10px;font-weight:700;margin-right:3px">✓</span>' : '';
    const pbadge = d.partner  ? '<span style="background:#e67e22;color:white;border-radius:3px;padding:1px 4px;font-size:10px;font-weight:700;margin-left:3px">合作</span>' : '';
    const tags   = d.tags.map(t=>`<span style="background:#eef2ff;color:#3d5af1;border-radius:3px;padding:1px 5px;font-size:11px">${{t}}</span>`).join(' ');
    const zh     = d.zh ? `<div style="font-size:11px;color:#666;margin-top:3px">${{d.zh}}</div>` : '';
    return `<tr style="border-bottom:1px solid #f0f0f0" onmouseover="this.style.background='#f8f9ff'" onmouseout="this.style.background=''">
      <td style="padding:8px;width:66px;vertical-align:middle">${{thumb}}</td>
      <td style="padding:9px 12px;vertical-align:top;min-width:110px">
        <div style="display:flex;align-items:center;flex-wrap:wrap">${{vbadge}}<a href="${{d.profile}}" target="_blank" style="font-weight:600;color:#0f3460;text-decoration:none;font-size:13px">@${{d.author}}</a>${{pbadge}}</div>
        <div style="font-size:12px;color:#888;margin-top:3px">${{d.fans}} 粉</div>
      </td>
      <td style="padding:9px 12px;vertical-align:top">
        <a href="${{d.url}}" target="_blank" style="color:#1a1a2e;text-decoration:none;font-size:13px;line-height:1.4;display:block">${{d.text}}</a>
        ${{zh}}
        <div style="margin-top:5px;display:flex;flex-wrap:wrap;gap:3px">${{tags}}</div>
      </td>
      <td style="padding:9px 12px;text-align:right;font-size:13px;white-space:nowrap;vertical-align:top">${{tt_fmt(d.plays)}}</td>
      <td style="padding:9px 12px;text-align:right;font-size:13px;white-space:nowrap;vertical-align:top">${{tt_fmt(d.likes)}}</td>
      <td style="padding:9px 12px;text-align:right;font-size:13px;white-space:nowrap;vertical-align:top">${{tt_fmt(d.collects)}}</td>
      <td style="padding:9px 12px;text-align:right;font-size:13px;white-space:nowrap;vertical-align:top">${{tt_fmt(d.shares)}}</td>
      <td style="padding:9px 12px;text-align:right;font-size:13px;white-space:nowrap;vertical-align:top">${{d.comments}}</td>
      <td style="padding:9px 12px;font-size:12px;color:#888;white-space:nowrap;vertical-align:top">${{d.date}}</td>
      <td style="padding:9px 12px;vertical-align:top"><span style="background:${{d.qcolor}};color:white;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:500;white-space:nowrap">${{d.query}}</span></td>
    </tr>`;
  }}

  function tt_renderPage() {{
    const tbody = document.getElementById('tt-tableBody');
    if (!tbody) return;
    const PAGE = 50;
    tbody.innerHTML = tt_filtered.slice(tt_page*PAGE, (tt_page+1)*PAGE).map(tt_makeRow).join('');
    tt_renderPagination();
  }}

  function tt_renderPagination() {{
    const el = document.getElementById('tt-pagination');
    if (!el) return;
    const PAGE = 50, total = tt_filtered.length;
    const totalPages = Math.ceil(total / PAGE);
    if (totalPages <= 1) {{ el.innerHTML = `<span style="color:#888;font-size:12px">共 ${{total}} 条</span>`; return; }}
    const btn = (p, label, disabled, active) =>
      `<button onclick="tt_goPage(${{p}})" style="padding:4px 10px;border:1px solid ${{active?'#0f3460':'#ddd'}};background:${{active?'#0f3460':'white'}};color:${{active?'white':'#333'}};border-radius:5px;cursor:pointer;font-size:13px" ${{disabled?'disabled':''}}>
        ${{label}}</button>`;
    let pages = [];
    if (totalPages <= 7) pages = [...Array(totalPages).keys()];
    else {{
      pages = [0];
      let lo = Math.max(1,tt_page-2), hi = Math.min(totalPages-2,tt_page+2);
      if (lo>1) pages.push('…');
      for (let i=lo;i<=hi;i++) pages.push(i);
      if (hi<totalPages-2) pages.push('…');
      pages.push(totalPages-1);
    }}
    let html = btn(tt_page-1,'‹', tt_page===0, false);
    pages.forEach(p => {{
      if (p==='…') {{ html+=`<span style="color:#aaa">…</span>`; return; }}
      html += btn(p, p+1, false, p===tt_page);
    }});
    html += btn(tt_page+1,'›', tt_page>=totalPages-1, false);
    html += `<span style="color:#888;font-size:12px;margin-left:4px">第${{tt_page+1}}/${{totalPages}}页 · ${{total}}条</span>`;
    el.innerHTML = html;
  }}

  function tt_goPage(p) {{
    const totalPages = Math.ceil(tt_filtered.length/50);
    if (p<0||p>=totalPages) return;
    tt_page = p;
    tt_renderPage();
    const tbl = document.getElementById('tt-mainTable');
    if (tbl) tbl.scrollIntoView({{behavior:'smooth',block:'start'}});
  }}

  function tt_applyFilter() {{
    const q = (document.getElementById('tt-search')||{{}}).value||'';
    const ql = q.toLowerCase();
    tt_filtered = TT_DATA.filter(d => {{
      const qm = tt_query==='all' || d.query===tt_query;
      const tm = !ql || (d.author+d.text+d.zh+d.tags.join(' ')).toLowerCase().includes(ql);
      return qm && tm;
    }});
    const rc = document.getElementById('tt-rowCount');
    if (rc) rc.textContent = '共 ' + tt_filtered.length + ' 条';
    tt_page = 0;
    tt_renderPage();
  }}

  function tt_onSearch() {{ tt_applyFilter(); }}

  function tt_setQuery(q, btn) {{
    tt_query = q;
    document.querySelectorAll('#content-tiktok .filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    tt_applyFilter();
  }}

  function tt_sortTable(col) {{
    if (tt_sortCol===col) tt_sortDir*=-1; else {{tt_sortCol=col; tt_sortDir=-1;}}
    const keys = [null,'author',null,'plays','likes','collects','shares','comments','date'];
    tt_filtered.sort((a,b) => {{
      const ak = keys[col], av = a[ak], bv = b[ak];
      if (typeof av==='number') return (av-bv)*tt_sortDir;
      return String(av).localeCompare(String(bv))*tt_sortDir;
    }});
    tt_page = 0;
    tt_renderPage();
  }}

  // 初始渲染
  tt_applyFilter();
  // ── TikTok 模块结束 ──────────────────────────────────
"""

# ── 开始修改 V2 ────────────────────────────────────────────
with open('nex_playground_pr_research_v2.html', encoding='utf-8') as f:
    v2 = f.read()

# 1. 替换 module-content 内容
mc_marker = '<div class="module-content" id="content-tiktok">'
mc_start = v2.find(mc_marker)
if mc_start == -1:
    raise ValueError('找不到 content-tiktok')
inner_start = mc_start + len(mc_marker)

# 括号计数找 module-content 的闭合 </div>
depth, pos, inner_end = 1, inner_start, inner_start
while pos < len(v2) and depth > 0:
    op = v2.find('<div', pos)
    cl = v2.find('</div>', pos)
    if op == -1: op = len(v2)
    if cl == -1: break
    if op < cl:
        depth += 1; pos = op + 4
    else:
        depth -= 1
        if depth == 0: inner_end = cl
        pos = cl + 6

v2 = v2[:inner_start] + '\n' + new_content + '\n  ' + v2[inner_end:]

# 2. 更新模块计数
v2 = re.sub(r'id="tiktok-module-count">[^<]+', 'id="tiktok-module-count">549 条', v2)

# 3. TikTok JS 放独立 <script> 标签，紧接在 </body> 前
#    完全独立，不和 V2 原有 JS 共用作用域，避免变量冲突和执行顺序问题
tt_script_block = f'<script>\n{tiktok_js}\n</script>\n'

# 移除已有的 TikTok 独立脚本块（如果重复运行）
v2 = re.sub(r'<script>\s*// ── TikTok 模块.*?</script>\n', '', v2, flags=re.DOTALL)

v2 = v2.replace('</body>', tt_script_block + '</body>', 1)

# 4. 写回
with open('nex_playground_pr_research_v2.html', 'w', encoding='utf-8') as f:
    f.write(v2)

print(f'Done! V2 大小: {len(v2)/1024:.0f} KB')

# 验证
assert 'id="tt-tableBody"' in v2, 'tbody 未替换'
assert 'const TT_DATA' in v2, 'JS 数据未注入'
assert 'tt_renderPage' in v2, 'JS 函数未注入'
assert 'function toggleModule' in v2, 'toggleModule 被破坏'
assert 'tt_applyFilter()' in v2, '初始渲染调用缺失'
print('验证通过')
print(f'TT_DATA 大小: {len(rows_js)//1024} KB，视频数: {len(rows_data)}')
