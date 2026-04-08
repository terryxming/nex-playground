#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_insights_report.py
读取 insights_data.json，翻译评论，生成 comments_insights.html 消费者洞察报告
"""

import json
import html
import os
import sys
import time
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

# ─── 翻译模块 ────────────────────────────────────────────────
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("警告：deep_translator 未安装，跳过翻译")

CACHE_PATH = "D:/Terry-Vibe-Coding/nex-playground/insights_translations_cache.json"
DATA_PATH  = "D:/Terry-Vibe-Coding/nex-playground/insights_data.json"
OUTPUT_PATH = "D:/Terry-Vibe-Coding/nex-playground/comments_insights.html"

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def translate_texts(texts, cache):
    """批量翻译，命中缓存直接返回，否则调用 API"""
    if not TRANSLATOR_AVAILABLE:
        return cache

    to_translate = [t for t in texts if t and t not in cache]
    if not to_translate:
        print(f"  翻译缓存全部命中（共 {len(texts)} 条）")
        return cache

    print(f"  缓存命中 {len(texts) - len(to_translate)} 条，需翻译 {len(to_translate)} 条...")
    translator = GoogleTranslator(source='auto', target='zh-CN')
    translated_count = 0

    for text in to_translate:
        try:
            result = translator.translate(text)
            if result and result != text:
                cache[text] = result
                translated_count += 1
            time.sleep(0.1)  # 避免速率限制
        except Exception as e:
            pass  # 失败跳过，显示原文

    print(f"  翻译完成：{translated_count}/{len(to_translate)} 条成功")
    return cache

# ─── 数据读取 ────────────────────────────────────────────────
print("读取 insights_data.json ...")
with open(DATA_PATH, encoding="utf-8") as f:
    data = json.load(f)

meta = data["meta"]
m1 = data["module1_viral"]
m2 = data["module2_jtbd"]
m3 = data["module3_personas"]
m4 = data["module4_triggers"]
m5 = data["module5_needs"]
m6 = data["module6_scenarios"]
m7 = data["module7_unmet"]
m8 = data["module8_journey"]

# ─── 收集所有评论文本 ────────────────────────────────────────
def collect_all_comments(obj):
    results = []
    if isinstance(obj, dict):
        if "top_comments" in obj and isinstance(obj["top_comments"], list):
            results.extend(obj["top_comments"])
        for v in obj.values():
            results.extend(collect_all_comments(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(collect_all_comments(item))
    return results

all_comments = collect_all_comments(data)
all_texts = list({c.get("text", "").strip() for c in all_comments if c.get("text", "").strip()})
print(f"共收集到 {len(all_texts)} 条唯一评论文本")

# ─── 加载缓存 + 翻译 ─────────────────────────────────────────
print("加载翻译缓存 ...")
translation_cache = load_cache()
translation_cache = translate_texts(all_texts, translation_cache)
save_cache(translation_cache)
print(f"翻译缓存已保存（共 {len(translation_cache)} 条）")

def get_zh(text):
    """获取中文译文，失败返回空字符串"""
    if not text:
        return ""
    return translation_cache.get(text.strip(), "")

# ─── 工具函数 ────────────────────────────────────────────────
def fmt_num(n):
    return f"{int(n):,}"

def fmt_digg(n):
    n = int(n)
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def esc(s):
    return html.escape(str(s), quote=True)

def comment_card(c):
    """新版评论卡片：中文 + 英文原文 + meta"""
    text_en = c.get("text", "")
    text_zh = get_zh(text_en)
    digg = fmt_digg(c.get("diggCount", 0))
    liked = c.get("likedByAuthor", False)
    pinned = c.get("pinnedByAuthor", False)

    zh_line = f'<div class="comment-zh">{esc(text_zh)}</div>' if text_zh else ""
    en_line = f'<div class="comment-en">"{esc(text_en)}"</div>' if text_en else ""
    liked_badge = '<span class="badge-liked">作者点赞</span>' if liked else ""
    pinned_badge = '<span class="badge-pinned">置顶</span>' if pinned else ""

    return f"""
        <div class="comment-card">
            {zh_line}
            {en_line}
            <div class="comment-meta">
                <span class="likes">👍 {digg}</span>
                {liked_badge}
                {pinned_badge}
            </div>
        </div>"""

def bar_row(label, val, max_val, color="#58a6ff"):
    pct = (val / max_val * 100) if max_val > 0 else 0
    return f"""
        <div class="bar-row">
            <div class="bar-label">{esc(label)}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct:.1f}%;background:linear-gradient(90deg,{color},{color}99)"></div>
            </div>
            <div class="bar-value">{fmt_num(val)}</div>
        </div>"""

def simple_bar(val, max_val, color="#58a6ff", height="8px"):
    pct = (val / max_val * 100) if max_val > 0 else 0
    return f'<div class="bar-track" style="height:{height}"><div class="bar-fill" style="width:{pct:.1f}%;height:{height};background:linear-gradient(90deg,{color},{color}88)"></div></div>'

# ─── 关键词中文映射 ──────────────────────────────────────────
JTBD_LABELS = {
    "active_play":   "主动运动",
    "screen_alt":    "屏幕替代",
    "family_bond":   "家庭联结",
    "indoor_play":   "室内娱乐",
    "gift_solution": "礼物方案",
    "social_status": "社交话题",
}

# ─── CSS ─────────────────────────────────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 15px;
    line-height: 1.6;
}
a { color: inherit; text-decoration: none; }

/* ══ Header ══════════════════════════════════════════════════ */
.header {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    border-bottom: 1px solid #30363d;
    padding: 52px 48px 40px;
    text-align: center;
}
.header h1 {
    font-size: 2.6rem;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 10px;
    letter-spacing: -0.5px;
}
.header h1 span {
    background: linear-gradient(135deg, #58a6ff, #388bfd);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.header .subtitle {
    color: #8b949e;
    font-size: 1rem;
    margin-bottom: 6px;
}
.header .date-tag { color: #484f58; font-size: 0.85rem; }

.stats-row {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 36px;
    flex-wrap: wrap;
}
.stat-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 32px;
    text-align: center;
    min-width: 150px;
    position: relative;
    overflow: hidden;
}
.stat-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
}
.stat-card.blue::after   { background: #58a6ff; }
.stat-card.green::after  { background: #3fb950; }
.stat-card.orange::after { background: #f78166; }
.stat-card.yellow::after { background: #d29922; }
.stat-num {
    font-size: 2.2rem;
    font-weight: 700;
    color: #e6edf3;
    display: block;
}
.stat-lbl {
    color: #8b949e;
    font-size: 0.82rem;
    margin-top: 4px;
}

/* ══ Tab Nav ══════════════════════════════════════════════════ */
.tab-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 16px 40px;
    background: #161b22;
    border-bottom: 1px solid #30363d;
    position: sticky;
    top: 0;
    z-index: 100;
}
.tab-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 20px;
    color: #8b949e;
    cursor: pointer;
    font-size: 0.85rem;
    white-space: nowrap;
    transition: all 0.18s;
    font-family: inherit;
    line-height: 1.4;
}
.tab-btn:hover {
    background: #2d333b;
    color: #e6edf3;
    border-color: #484f58;
}
.tab-btn.active {
    background: #1f6feb;
    border-color: #1f6feb;
    color: #ffffff;
    font-weight: 600;
    box-shadow: 0 0 0 3px rgba(31,111,235,0.25);
}
.tab-icon { font-size: 1rem; line-height: 1; }
.tab-label { font-size: 0.85rem; }

/* ══ Section ══════════════════════════════════════════════════ */
.section { display: none; padding: 40px 48px; max-width: 1400px; margin: 0 auto; }
.section.active { display: block; }

/* ══ Module Header ═══════════════════════════════════════════ */
.module-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}
.module-badge {
    background: rgba(88,166,255,0.15);
    color: #58a6ff;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid rgba(88,166,255,0.3);
}
.section-label {
    font-size: 0.75rem;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 20px;
}

/* ══ Insight Box ══════════════════════════════════════════════ */
.insight-box {
    background: linear-gradient(135deg, rgba(31,111,235,0.1), rgba(88,166,255,0.05));
    border: 1px solid rgba(88,166,255,0.3);
    border-left: 4px solid #58a6ff;
    border-radius: 0 12px 12px 0;
    padding: 18px 22px;
    margin: 16px 0 28px;
    font-size: 0.95rem;
    color: #c9d1d9;
    line-height: 1.8;
}
.insight-box strong { color: #58a6ff; }

/* ══ Comment Card ═════════════════════════════════════════════ */
.comment-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    border-radius: 0 10px 10px 0;
    padding: 14px 18px;
    margin: 10px 0;
    transition: border-color 0.2s;
}
.comment-card:hover { border-left-color: #f78166; }
.comment-zh { color: #e6edf3; font-size: 14px; margin-bottom: 6px; font-weight: 500; }
.comment-en { color: #8b949e; font-size: 13px; font-style: italic; }
.comment-meta { margin-top: 8px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.likes { color: #8b949e; font-size: 12px; }
.badge-liked { background: rgba(88,166,255,0.15); color: #58a6ff; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge-pinned { background: rgba(247,129,102,0.15); color: #f78166; padding: 2px 8px; border-radius: 10px; font-size: 11px; }

/* ══ Bar Row ══════════════════════════════════════════════════ */
.bar-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 10px 0;
}
.bar-label { min-width: 160px; color: #c9d1d9; font-size: 0.88rem; flex-shrink: 0; }
.bar-track { background: #21262d; border-radius: 4px; height: 8px; flex: 1; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; }
.bar-value { min-width: 56px; text-align: right; color: #8b949e; font-size: 0.85rem; flex-shrink: 0; }

/* ══ Cards Grid ═══════════════════════════════════════════════ */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin: 20px 0;
}
.card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
    transition: box-shadow 0.2s, border-color 0.2s;
}
.card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.4); border-color: #444c56; }
.card-title { font-size: 1rem; font-weight: 600; color: #58a6ff; margin-bottom: 10px; }
.card-big-num { font-size: 2.2rem; font-weight: 700; color: #e6edf3; }
.card-sub { font-size: 0.82rem; color: #8b949e; margin: 4px 0 12px; }
.card-desc { font-size: 0.88rem; color: #8b949e; margin: 8px 0 12px; line-height: 1.6; }

/* ══ Section Divider ══════════════════════════════════════════ */
.section-divider { border: none; border-top: 1px solid #21262d; margin: 28px 0; }

/* ══ Ranked List ══════════════════════════════════════════════ */
.ranked-list { margin: 20px 0; }
.ranked-item {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 16px;
    transition: border-color 0.2s;
}
.ranked-item:hover { border-color: #444c56; }
.ranked-item.highlight { border-color: #d29922; }
.ranked-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}
.rank-num { font-size: 1.4rem; font-weight: 700; color: #f78166; min-width: 36px; }
.rank-name { font-size: 1rem; font-weight: 600; color: #e6edf3; flex: 1; }
.rank-meta { color: #8b949e; font-size: 0.85rem; }

/* ══ Three-column needs ═══════════════════════════════════════ */
.needs-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin: 20px 0;
}
@media (max-width: 900px) { .needs-grid { grid-template-columns: 1fr; } }
.needs-col {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
}
.needs-col-title {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 2px solid;
    display: flex;
    align-items: center;
    gap: 8px;
}
.needs-count-badge {
    font-size: 0.78rem;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 600;
    margin-left: auto;
}

/* ══ Keyword tags in needs ═══════════════════════════════════ */
.kw-list { margin: 0 0 14px; display: flex; flex-direction: column; gap: 4px; }
.kw-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: #8b949e;
}
.kw-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ══ Tag Cloud ════════════════════════════════════════════════ */
.tag-cloud { display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0; }
.tag {
    border-radius: 20px;
    padding: 6px 16px;
    cursor: default;
    transition: all 0.2s;
    font-weight: 500;
}

/* ══ Journey Timeline ════════════════════════════════════════ */
.timeline {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 24px 0;
}
@media (max-width: 900px) { .timeline { grid-template-columns: repeat(2,1fr); } }
.timeline-stage {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
    border-top-width: 3px;
    transition: box-shadow 0.2s;
}
.timeline-stage:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
.stage-phase {
    font-size: 0.72rem;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}
.stage-title { font-size: 0.95rem; font-weight: 700; color: #e6edf3; margin-bottom: 4px; }
.stage-theme { font-size: 0.8rem; color: #8b949e; margin-bottom: 14px; }
.stage-count { font-size: 1.8rem; font-weight: 700; margin-bottom: 14px; }
.sentiment-row { margin: 6px 0; }
.sentiment-label { font-size: 0.78rem; color: #8b949e; margin-bottom: 4px; }

/* ══ Two-col ══════════════════════════════════════════════════ */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 16px 0; }
@media (max-width: 800px) { .two-col { grid-template-columns: 1fr; } }

/* ══ Value Prop Box ═══════════════════════════════════════════ */
.value-prop-box {
    background: linear-gradient(135deg, rgba(63,185,80,0.1), rgba(88,166,255,0.08));
    border: 1px solid rgba(63,185,80,0.3);
    border-radius: 12px;
    padding: 24px;
    margin-top: 28px;
    text-align: center;
}
.value-prop-box h3 { color: #3fb950; margin-bottom: 10px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }
.value-prop-box p { color: #c9d1d9; font-size: 1.05rem; line-height: 1.8; }

/* ══ Warning / Opportunity Box ════════════════════════════════ */
.warning-box {
    background: rgba(210,153,34,0.1);
    border: 1px solid rgba(210,153,34,0.4);
    border-left: 4px solid #d29922;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin-top: 24px;
    font-size: 0.9rem;
    color: #c9d1d9;
}
.warning-box strong { color: #d29922; }

/* ══ Persona pct ══════════════════════════════════════════════ */
.persona-pct {
    font-size: 2.4rem;
    font-weight: 700;
    color: #58a6ff;
}

/* ══ Opp badge ════════════════════════════════════════════════ */
.opp-badge {
    display: inline-block;
    background: rgba(210,153,34,0.15);
    border: 1px solid rgba(210,153,34,0.4);
    color: #d29922;
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 8px;
    vertical-align: middle;
}

/* ══ Journey insight ══════════════════════════════════════════ */
.journey-insight {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 24px;
}
.journey-insight h3 { color: #8b949e; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
"""

# ─── JavaScript ─────────────────────────────────────────────
JS = """
function showTab(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.querySelector('[data-tab="' + id + '"]').classList.add('active');
    window.scrollTo({top: 0, behavior: 'smooth'});
}
"""

# ─── 模块构建函数 ─────────────────────────────────────────────

def build_module1():
    factors = m1["factors"]
    max_signal = max(v["total_signal"] for v in factors.values()) or 1
    factor_icons = {
        "TikTok发现路径": "📱",
        "自发传播":       "🔄",
        "惊喜反应":       "😲",
        "循环效应":       "♻️",
        "情感共鸣":       "❤️",
    }

    cards_html = '<div class="cards-grid">'
    for fname, fdata in factors.items():
        icon = factor_icons.get(fname, "✨")
        bar_html = simple_bar(fdata["total_signal"], max_signal, "#58a6ff", "8px")
        comments_html = "".join(comment_card(c) for c in fdata["top_comments"][:2])
        cards_html += f"""
        <div class="card">
            <div class="card-title">{icon} {esc(fname)}</div>
            <div class="card-big-num">{fmt_num(fdata['count'])}</div>
            <div class="card-sub">评论数 · 总信号 {fmt_num(fdata['total_signal'])}</div>
            <div class="bar-row" style="margin:0 0 12px">
                <div class="bar-track" style="flex:1;height:8px">{bar_html}</div>
                <div style="font-size:0.8rem;color:#8b949e;min-width:40px;text-align:right">{round(fdata['total_signal']/max_signal*100)}%</div>
            </div>
            {comments_html}
        </div>"""
    cards_html += '</div>'

    viral_comments = m1.get("top_viral_comments", [])[:5]
    viral_html = "".join(comment_card(c) for c in viral_comments)

    return f"""
    <div class="module-title">
        <span>🚀 模块一：爆品密码</span>
        <span class="module-badge">传播因子分析</span>
    </div>
    <div class="section-label">Viral Factors Analysis</div>
    <div class="insight-box">
        传播密码 = <strong>TikTok 发现</strong> × <strong>惊喜反应</strong> × <strong>家庭情感</strong> × <strong>口碑裂变</strong>。
        情感共鸣类评论信号值最高，证明用户的<strong>真实情感投入</strong>是 TikTok 爆款的核心引擎；
        循环效应和自发传播说明产品在礼物场景中形成了强烈的购买意愿传播链。
    </div>
    <h3 style="color:#8b949e;margin-bottom:16px;font-size:0.85rem;text-transform:uppercase;letter-spacing:1px">五大传播因子</h3>
    {cards_html}
    <hr class="section-divider">
    <h3 style="color:#8b949e;margin-bottom:16px;font-size:0.85rem;text-transform:uppercase;letter-spacing:1px">全局高信号评论 TOP 5</h3>
    {viral_html}
    """

def build_module2():
    sorted_jobs = m2["sorted_jobs"]
    func_count = m2["functional_count"]
    emo_count = m2["emotional_count"]
    total_fe = func_count + emo_count or 1
    max_signal = max(j["total_signal"] for j in sorted_jobs) or 1
    max_count  = max(j["count"] for j in sorted_jobs) or 1

    colors = ["#f78166", "#58a6ff", "#d29922", "#bc8cff", "#4facfe", "#3fb950"]
    rows_html = ""
    for i, jdata in enumerate(sorted_jobs):
        job_key = jdata["job"]
        job_name = JTBD_LABELS.get(job_key, jdata.get("name", job_key))
        color = colors[i % len(colors)]
        comments_html = "".join(comment_card(c) for c in jdata["top_comments"][:2])
        rows_html += f"""
        <div class="ranked-item">
            <div class="ranked-header">
                <div class="rank-num">#{i+1}</div>
                <div class="rank-name">{esc(job_name)}</div>
                <div class="rank-meta">{fmt_num(jdata['count'])} 条 · 均赞 {jdata['avg_diggCount']}</div>
            </div>
            {bar_row(f"计数 {fmt_num(jdata['count'])}", jdata['count'], max_count, color)}
            {bar_row(f"信号 {fmt_num(jdata['total_signal'])}", jdata['total_signal'], max_signal, color+'88')}
            {comments_html}
        </div>"""

    func_pct = func_count / total_fe * 100
    emo_pct = emo_count / total_fe * 100

    return f"""
    <div class="module-title">
        <span>🎯 模块二：用户任务 (JTBD)</span>
        <span class="module-badge">Jobs To Be Done</span>
    </div>
    <div class="section-label">What users hire Nex Playground for</div>
    <div class="insight-box">
        用户雇用 Nex Playground 的<strong>首要任务是制造全家人在一起的快乐时光</strong>。
        按信号量排名，家庭联结（9,500 信号）遥遥领先；礼物方案（305 条）按量最多。
        <strong>情感性任务占 {emo_pct:.0f}%</strong>，购买决策几乎由情感驱动，功能参数排第二。
    </div>
    {rows_html}
    <hr class="section-divider">
    <h3 style="color:#8b949e;margin-bottom:16px;font-size:0.85rem;text-transform:uppercase;letter-spacing:1px">功能性 vs 情感性任务占比</h3>
    <div style="max-width:560px">
        <div class="bar-row">
            <div class="bar-label">情感性任务</div>
            <div class="bar-track" style="height:20px;flex:1"><div class="bar-fill" style="width:{emo_pct:.1f}%;height:20px;background:linear-gradient(90deg,#f78166,#f7816699)"></div></div>
            <div class="bar-value">{emo_count} ({emo_pct:.0f}%)</div>
        </div>
        <div class="bar-row">
            <div class="bar-label">功能性任务</div>
            <div class="bar-track" style="height:20px;flex:1"><div class="bar-fill" style="width:{func_pct:.1f}%;height:20px;background:linear-gradient(90deg,#58a6ff,#58a6ff99)"></div></div>
            <div class="bar-value">{func_count} ({func_pct:.0f}%)</div>
        </div>
    </div>
    """

def build_module3():
    sorted_personas = m3["sorted"]
    colors = ["#58a6ff", "#f78166", "#d29922", "#bc8cff", "#3fb950"]
    persona_emojis = {
        "Fun Parent": "👨‍👩‍👧",
        "Gift Hunter": "🎁",
        "TikTok Parent": "📱",
        "Active Parent": "🏃",
        "Kid Influencer": "⭐",
    }

    cards_html = '<div class="cards-grid">'
    for i, (pname, pdata) in enumerate(sorted_personas):
        color = colors[i % len(colors)]
        pct = pdata.get("percentage", 0)
        desc = pdata.get("desc", "")
        emoji = persona_emojis.get(pname, "👤")
        comments_html = "".join(comment_card(c) for c in pdata["top_comments"][:2])
        cards_html += f"""
        <div class="card">
            <div style="font-size:2rem;margin-bottom:8px">{emoji}</div>
            <div class="card-title" style="color:{color}">{esc(pname)}</div>
            <div class="persona-pct" style="color:{color}">{pct}%</div>
            <div class="card-sub">{fmt_num(pdata['count'])} 条评论</div>
            <div class="card-desc">{esc(desc)}</div>
            {comments_html}
        </div>"""
    cards_html += '</div>'

    return f"""
    <div class="module-title">
        <span>👥 模块三：用户画像</span>
        <span class="module-badge">Persona Analysis</span>
    </div>
    <div class="section-label">Who is talking about Nex Playground</div>
    <div class="insight-box">
        <strong>Fun Parent（76.2%）</strong>是绝对主流用户——为自家孩子购买，追求亲子互动与家庭时光。
        <strong>Gift Hunter（10%）</strong>是节假日营销的重要目标。TikTok Parent 虽数量少，但信号值极高，
        说明他们评论质量高、影响力强。
    </div>
    {cards_html}
    """

def build_module4():
    sorted_triggers = m4["sorted_triggers"]
    max_signal = max(t["total_signal"] for t in sorted_triggers) or 1
    max_count  = max(t["count"] for t in sorted_triggers) or 1
    colors = ["#58a6ff", "#f78166", "#3fb950", "#d29922", "#bc8cff", "#4facfe"]

    rows_html = ""
    for i, tdata in enumerate(sorted_triggers):
        color = colors[i % len(colors)]
        comments_html = "".join(comment_card(c) for c in tdata["top_comments"][:2])
        rows_html += f"""
        <div class="ranked-item">
            <div class="ranked-header">
                <div class="rank-num">#{i+1}</div>
                <div class="rank-name">{esc(tdata['name'])}</div>
                <div class="rank-meta">{fmt_num(tdata['count'])} 条</div>
            </div>
            {bar_row(f"信号 {fmt_num(tdata['total_signal'])}", tdata['total_signal'], max_signal, color)}
            {bar_row(f"计数 {fmt_num(tdata['count'])}", tdata['count'], max_count, color+'88')}
            {comments_html}
        </div>"""

    return f"""
    <div class="module-title">
        <span>⚡ 模块四：购买触发点</span>
        <span class="module-badge">Purchase Triggers</span>
    </div>
    <div class="section-label">What drives users to buy</div>
    <div class="insight-box">
        <strong>孩子看到想要 + TikTok 刷到 = 最强购买组合</strong>。TikTok 发现的信号值最高（12,459），
        说明 TikTok 内容直接触发了高质量的购买意愿表达。冲动购买（242 条）数量最多，
        礼物购买（59 条）以圣诞 / 生日场景为主。
    </div>
    {rows_html}
    """

def build_module5():
    pain = m5["pain"]
    itch = m5["itch"]
    wow  = m5["wow"]
    value_prop = m5.get("value_prop", "")

    def kw_items(kf, color, limit=5):
        if not kf:
            return ""
        items = list(kf.items())[:limit]
        max_val = max(v for _, v in items) or 1
        out = '<div class="kw-list">'
        for kw, cnt in items:
            # 截短正则，只显示第一个 | 前的内容或前 30 字
            display = kw.split('|')[0].strip('(').strip()
            if len(display) > 30:
                display = display[:28] + "…"
            pct = cnt / max_val * 100
            out += f"""
            <div class="kw-item">
                <div class="kw-dot" style="background:{color}"></div>
                <span style="flex:1;color:#c9d1d9">{esc(display)}</span>
                <div style="width:60px;margin:0 8px">
                    <div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{color}88"></div></div>
                </div>
                <span style="color:#8b949e;font-size:0.8rem;min-width:24px;text-align:right">{cnt}</span>
            </div>"""
        out += '</div>'
        return out

    pain_comments = "".join(comment_card(c) for c in pain["top_comments"][:4])
    itch_comments = "".join(comment_card(c) for c in itch["top_comments"][:4])
    wow_comments  = "".join(comment_card(c) for c in wow["top_comments"][:4])

    return f"""
    <div class="module-title">
        <span>🔍 模块五：三层需求分析</span>
        <span class="module-badge">Pain · Itch · Wow</span>
    </div>
    <div class="section-label">Layered user needs analysis</div>
    <div class="insight-box">
        爽点（Wow）词语如 "obsessed" / "worth every penny" 说明产品<strong>超出用户期待</strong>；
        痒点（Itch）以"希望订阅制不存在"为主；痛点（Pain）集中在屏幕时间过多和运动不足，
        正是产品的<strong>核心切入点</strong>。
    </div>
    <div class="needs-grid">
        <div class="needs-col">
            <div class="needs-col-title" style="color:#f78166;border-color:#f78166">
                😣 痛点（Pain）
                <span class="needs-count-badge" style="background:rgba(247,129,102,0.15);color:#f78166">{pain['count']} 条</span>
            </div>
            {kw_items(pain['keyword_freq'], '#f78166')}
            {pain_comments}
        </div>
        <div class="needs-col">
            <div class="needs-col-title" style="color:#d29922;border-color:#d29922">
                🤔 痒点（Itch）
                <span class="needs-count-badge" style="background:rgba(210,153,34,0.15);color:#d29922">{itch['count']} 条</span>
            </div>
            {kw_items(itch['keyword_freq'], '#d29922')}
            {itch_comments}
        </div>
        <div class="needs-col">
            <div class="needs-col-title" style="color:#3fb950;border-color:#3fb950">
                🤩 爽点（Wow）
                <span class="needs-count-badge" style="background:rgba(63,185,80,0.15);color:#3fb950">{wow['count']} 条</span>
            </div>
            {kw_items(wow['keyword_freq'], '#3fb950')}
            {wow_comments}
        </div>
    </div>
    <div class="value-prop-box">
        <h3>💡 核心价值主张</h3>
        <p>{esc(value_prop)}</p>
    </div>
    """

def build_module6():
    sorted_scenarios = m6["sorted"]
    max_count = max(s[1]["count"] for s in sorted_scenarios) or 1

    # 标签云
    tag_colors = ["#58a6ff", "#f78166", "#3fb950", "#d29922", "#bc8cff", "#4facfe", "#e6edf3"]
    tags_html = '<div class="tag-cloud">'
    for idx, (sname, sdata) in enumerate(sorted_scenarios):
        cnt = sdata["count"]
        size = 12 + int(cnt / max_count * 14)
        color = tag_colors[idx % len(tag_colors)]
        opacity = 0.3 + cnt / max_count * 0.5
        tags_html += f'<span class="tag" style="font-size:{size}px;background:rgba(88,166,255,{opacity:.2f});color:{color};border:1px solid {color}44">{esc(sname)} <strong>{cnt}</strong></span>'
    tags_html += '</div>'

    # 排行
    rows_html = ""
    for i, (sname, sdata) in enumerate(sorted_scenarios):
        color = tag_colors[i % len(tag_colors)]
        comments_html = "".join(comment_card(c) for c in sdata["top_comments"][:2])
        rows_html += f"""
        <div class="ranked-item">
            <div class="ranked-header">
                <div class="rank-num">#{i+1}</div>
                <div class="rank-name">{esc(sname)}</div>
                <div class="rank-meta">{fmt_num(sdata['count'])} 条 · 信号 {fmt_num(sdata['total_signal'])}</div>
            </div>
            {bar_row("", sdata['count'], max_count, color)}
            {comments_html}
        </div>"""

    return f"""
    <div class="module-title">
        <span>🎮 模块六：使用场景</span>
        <span class="module-badge">Usage Scenarios</span>
    </div>
    <div class="section-label">Where and how users engage with Nex Playground</div>
    <div class="insight-box">
        <strong>多人同玩（52 条）</strong>是最高频场景，印证了家庭联结 JTBD；
        <strong>停不下来（36 条）</strong>信号值最高（7,175），说明产品沉浸感极强；
        <strong>特殊场合（37 条）</strong>的圣诞 / 生日礼物场景是内容营销的黄金题材。
    </div>
    <h3 style="color:#8b949e;margin-bottom:12px;font-size:0.82rem;text-transform:uppercase;letter-spacing:1px">场景标签云（大小 = 频次）</h3>
    {tags_html}
    <hr class="section-divider">
    <h3 style="color:#8b949e;margin-bottom:16px;font-size:0.82rem;text-transform:uppercase;letter-spacing:1px">场景排行榜</h3>
    {rows_html}
    """

def build_module7():
    sorted_needs = m7["sorted_needs"]
    max_count  = max(n["count"] for n in sorted_needs) or 1
    max_signal = max(n["total_signal"] for n in sorted_needs) or 1

    HIGHLIGHT_NAMES = {"价格/性价比 💰", "订阅制顾虑 📋"}
    OPP_TEXTS = {
        "价格/性价比 💰":   "Black Friday 策略 / 强调性价比",
        "订阅制顾虑 📋":    "订阅价值教育 / 对比竞品",
        "硬件/耐用性 🔧":   "延迟问题透明沟通",
        "更多游戏模式 🎮":  "订阅制内容路线图",
        "库存/购买渠道 📦": "多渠道扩展",
    }
    colors = ["#d29922", "#d29922", "#58a6ff", "#bc8cff", "#3fb950"]

    rows_html = ""
    for i, ndata in enumerate(sorted_needs):
        name = ndata["name"]
        is_hl = name in HIGHLIGHT_NAMES
        color = colors[i % len(colors)]
        opp = OPP_TEXTS.get(name, "")
        opp_badge = f'<span class="opp-badge">{esc(opp)}</span>' if opp else ""
        comments_html = "".join(comment_card(c) for c in ndata["top_comments"][:3])
        hl_cls = "ranked-item highlight" if is_hl else "ranked-item"
        rows_html += f"""
        <div class="{hl_cls}">
            <div class="ranked-header">
                <div class="rank-num" style="color:{color}">#{i+1}</div>
                <div class="rank-name">{esc(name)}{opp_badge}</div>
                <div class="rank-meta">{fmt_num(ndata['count'])} 条 · 均信号 {ndata['avg_signal']}</div>
            </div>
            {bar_row("评论数", ndata['count'], max_count, color)}
            {bar_row("总信号", ndata['total_signal'], max_signal, color+'88')}
            {comments_html}
        </div>"""

    return f"""
    <div class="module-title">
        <span>⚠️ 模块七：未满足需求</span>
        <span class="module-badge">Unmet Needs</span>
    </div>
    <div class="section-label">Pain points and product improvement opportunities</div>
    <div class="insight-box">
        <strong>订阅制顾虑（302 条，均信号 50.3）</strong>是信号强度最高的负面话题，远超其他问题；
        <strong>价格 / 性价比（305 条）</strong>数量最多。两者合计超过 600 条，是产品<strong>最大的转化障碍</strong>。
    </div>
    {rows_html}
    <div class="warning-box">
        <strong>产品机会矩阵：</strong>
        <strong>价格 / 性价比</strong> 和 <strong>订阅制顾虑</strong> 这两个高频问题是产品改进和竞争突破的最大机会——
        解决这两个痛点可直接提升转化率和口碑评分。
    </div>
    """

def build_module8():
    bucket_order = m8["bucket_order"]
    buckets = m8["buckets"]
    stage_colors = {
        "0-24h": "#58a6ff",
        "1-7d":  "#d29922",
        "7-30d": "#3fb950",
        "30d+":  "#f78166",
    }

    stages_html = ""
    best_pos   = max(buckets[b].get("positive_pct", 0) for b in bucket_order)
    worst_neg  = max(buckets[b].get("negative_pct", 0) for b in bucket_order)

    for bkey in bucket_order:
        bdata = buckets[bkey]
        color = stage_colors.get(bkey, "#58a6ff")
        pos_pct = bdata.get("positive_pct", 0)
        neg_pct = bdata.get("negative_pct", 0)
        comments_html = "".join(comment_card(c) for c in bdata["top_comments"][:3])
        stages_html += f"""
        <div class="timeline-stage" style="border-top-color:{color}">
            <div class="stage-phase">{esc(bkey)}</div>
            <div class="stage-title">{esc(bdata['label'])}</div>
            <div class="stage-theme">{esc(bdata['theme'])}</div>
            <div class="stage-count" style="color:{color}">{fmt_num(bdata['count'])} 条</div>
            <div class="sentiment-row">
                <div class="sentiment-label">正面 {pos_pct}%</div>
                <div class="bar-track"><div class="bar-fill" style="width:{pos_pct}%;background:#3fb950"></div></div>
            </div>
            <div class="sentiment-row" style="margin-top:8px">
                <div class="sentiment-label">负面 {neg_pct}%</div>
                <div class="bar-track"><div class="bar-fill" style="width:{neg_pct*10}%;background:#f78166"></div></div>
            </div>
            <hr class="section-divider" style="margin:16px 0">
            {comments_html}
        </div>"""

    # 找出正面率最高和负面最集中的阶段
    best_pos_stage  = max(bucket_order, key=lambda b: buckets[b].get("positive_pct", 0))
    worst_neg_stage = max(bucket_order, key=lambda b: buckets[b].get("negative_pct", 0))
    bp_label = buckets[best_pos_stage]['label']
    wn_label = buckets[worst_neg_stage]['label']

    return f"""
    <div class="module-title">
        <span>📅 模块八：情感旅程</span>
        <span class="module-badge">Emotional Journey</span>
    </div>
    <div class="section-label">How sentiment evolves over time</div>
    <div class="insight-box">
        <strong>30 天+ 留存用户最多（3,739 条）</strong>，说明产品具备强长期粘性；
        即时反应期（0-24h）正面率最高（28.4%），说明内容种草效果显著；
        各阶段负面率均低于 2%，整体用户满意度高。
    </div>
    <div class="timeline">{stages_html}</div>
    <div class="journey-insight">
        <h3>阶段对比洞察</h3>
        <div class="two-col">
            <div>
                <div style="color:#3fb950;font-weight:600;margin-bottom:6px">✅ 正面率最高阶段</div>
                <div style="color:#c9d1d9">{esc(bp_label)}（{buckets[best_pos_stage].get('positive_pct')}%）</div>
                <div style="color:#8b949e;font-size:0.85rem;margin-top:4px">种草内容触达效果最强</div>
            </div>
            <div>
                <div style="color:#f78166;font-weight:600;margin-bottom:6px">⚠️ 负面最集中阶段</div>
                <div style="color:#c9d1d9">{esc(wn_label)}（{buckets[worst_neg_stage].get('negative_pct')}%）</div>
                <div style="color:#8b949e;font-size:0.85rem;margin-top:4px">长期用户对订阅制/耐用性问题更敏感</div>
            </div>
        </div>
    </div>
    """

# ─── 组装 HTML ─────────────────────────────────────────────────
MODULES = [
    ("tab-m1", "🚀", "爆品密码",   build_module1),
    ("tab-m2", "🎯", "JTBD",       build_module2),
    ("tab-m3", "👥", "用户画像",   build_module3),
    ("tab-m4", "⚡", "购买触发",   build_module4),
    ("tab-m5", "🔍", "三层需求",   build_module5),
    ("tab-m6", "🗺", "使用场景",   build_module6),
    ("tab-m7", "⚠", "未满足需求", build_module7),
    ("tab-m8", "📈", "情感旅程",   build_module8),
]

print("\n生成 HTML 各模块...")
tabs_html = ""
for tid, icon, label, _ in MODULES:
    active = ' active' if tid == MODULES[0][0] else ''
    tabs_html += (
        f'<button class="tab-btn{active}" data-tab="{tid}" onclick="showTab(\'{tid}\')">'
        f'<span class="tab-icon">{icon}</span>'
        f'<span class="tab-label">{esc(label)}</span>'
        f'</button>\n'
    )

sections_html = ""
for i, (tid, icon, label, build_fn) in enumerate(MODULES):
    print(f"  构建模块 [{i+1}/8] {tid}...")
    active = ' active' if i == 0 else ''
    sections_html += f'<div class="section{active}" id="{tid}">{build_fn()}</div>\n'

today = date.today().strftime("%Y-%m-%d")

# 计算正向评论数（m1 情感共鸣因子 + wow 评论）
positive_count = m1["factors"].get("情感共鸣", {}).get("count", 0) + m5["wow"]["count"]
high_signal_count = sum(1 for c in collect_all_comments(data) if c.get("signal", 0) >= 100)

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nex Playground 消费者洞察报告</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
    <h1>Nex Playground <span>消费者洞察报告</span></h1>
    <div class="subtitle">基于 {fmt_num(meta['valid_videos'])} 个 TikTok 视频 · {fmt_num(meta['total_comments'])} 条真实评论深度分析</div>
    <div class="date-tag">生成日期：{today} · 数据截止：{esc(meta.get('generated_at', today))}</div>
    <div class="stats-row">
        <div class="stat-card blue">
            <span class="stat-num">{fmt_num(meta['total_comments'])}</span>
            <div class="stat-lbl">评论总数</div>
        </div>
        <div class="stat-card green">
            <span class="stat-num">{fmt_num(meta['valid_videos'])}</span>
            <div class="stat-lbl">有效视频</div>
        </div>
        <div class="stat-card orange">
            <span class="stat-num">{fmt_num(positive_count)}</span>
            <div class="stat-lbl">正向评论</div>
        </div>
        <div class="stat-card yellow">
            <span class="stat-num">{fmt_num(high_signal_count)}</span>
            <div class="stat-lbl">高信号评论</div>
        </div>
    </div>
</div>

<nav class="tab-nav">
{tabs_html}
</nav>

{sections_html}

<script>{JS}</script>
</body>
</html>"""

# ─── 写出文件 ─────────────────────────────────────────────────
print(f"\n写入 {OUTPUT_PATH} ...")
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(HTML)

size_kb = len(HTML.encode("utf-8")) / 1024
print(f"\n生成成功：comments_insights.html")
print(f"文件大小：{size_kb:.1f} KB（{len(HTML):,} 字符）")
print(f"翻译条数：{len(translation_cache)} 条缓存")
print(f"评论总数：{fmt_num(meta['total_comments'])} · 视频数：{fmt_num(meta['valid_videos'])}")
