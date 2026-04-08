"""
Nex Playground 消费者洞察分析
从 423 个视频的 8,756 条 TikTok 评论提取 8 个洞察模块
输出: insights_data.json
"""

import json
import re
import glob
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

WRONG_MARKER = "7517426238970006839"

# ─── 1. 数据加载 ────────────────────────────────────────────────────────────────

print("Loading videos...")
with open("tiktok_nex_videos.json", encoding="utf-8") as f:
    videos = json.load(f)
video_map = {str(v["id"]): v for v in videos}
print(f"  {len(videos)} videos")

print("Loading comments (skipping wrong/empty)...")
all_comments = []
seen_cids = set()
valid_files = 0

for fpath in glob.glob("comments/*.json"):
    try:
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            continue
        url = data[0].get("videoWebUrl", "")
        if not url or WRONG_MARKER in url:
            continue
        video_id = os.path.splitext(os.path.basename(fpath))[0]
        video_meta = video_map.get(video_id, {})
        valid_files += 1
        for c in data:
            cid = c.get("cid", "")
            if cid and cid in seen_cids:
                continue
            if cid:
                seen_cids.add(cid)
            c["_video_id"] = video_id
            c["_video_create_time"] = video_meta.get("createTime", 0)
            c["_video_play_count"] = video_meta.get("playCount", 0)
            c["_signal"] = (
                (c.get("diggCount") or 0)
                + (10 if c.get("likedByAuthor") else 0)
                + (50 if c.get("pinnedByAuthor") else 0)
            )
            all_comments.append(c)
    except Exception:
        continue

print(f"  {valid_files} valid files, {len(all_comments)} unique comments")

def tl(c):
    return (c.get("text") or "").lower()

def top_comments(lst, n=5, min_len=10):
    seen = set()
    out = []
    for c in sorted(lst, key=lambda x: x["_signal"], reverse=True):
        t = (c.get("text") or "").strip()
        if len(t) < min_len or t in seen:
            continue
        seen.add(t)
        out.append({
            "text": t,
            "diggCount": c.get("diggCount", 0),
            "likedByAuthor": c.get("likedByAuthor", False),
            "pinnedByAuthor": c.get("pinnedByAuthor", False),
            "signal": c["_signal"],
        })
        if len(out) >= n:
            break
    return out

insights = {}

# ─── 模块 1：爆品密码 ────────────────────────────────────────────────────────────

print("Module 1: Viral factors...")

viral_patterns = {
    "TikTok发现路径": [
        r"saw this on tiktok", r"tiktok (made|had|got|sent|showed|brought) me",
        r"(my|the) (fyp|for you|feed|algorithm)", r"found (this|it) on tiktok",
        r"tiktok (made|told|showed)", r"on (my )?tiktok",
    ],
    "自发传播": [
        r"best (purchase|buy|investment|decision|gift|thing i('ve| have) (ever )?bought)",
        r"worth every penny", r"no regrets",
        r"(telling|told|showing) (everyone|all my|my friends|my family)",
        r"you (need|have to|must|should) (get|try|buy) (this|one)",
        r"highly recommend",
    ],
    "惊喜反应": [
        r"reaction was", r"their face", r"(couldn't|can't) believe",
        r"face when", r"look on (their|his|her) face",
        r"(screamed|screaming|jumping|lost (their|his|her) mind)",
        r"priceless", r"so surprised",
    ],
    "循环效应": [
        r"already (ordered|bought|got) (another|more|a second|one for)",
        r"got (one for|another for|this for)",
        r"told my (friend|sister|brother|mom|neighbor|husband|wife)",
        r"(buying|getting|ordering) (one for|for my|for the|this for)",
        r"gifting (this|one)",
    ],
    "情感共鸣": [
        r"obsessed", r"addicted",
        r"(won't|can't|doesn't|never) (want to )?stop (playing|using)",
        r"been playing (all day|for hours|since|all week)",
        r"(hours|days|weeks|months) (and still|later|straight)",
        r"(best|greatest|most fun) (ever|i've had)",
    ],
}

m1 = {}
for factor, patterns in viral_patterns.items():
    matched = []
    for c in all_comments:
        t = tl(c)
        if any(re.search(p, t) for p in patterns):
            matched.append(c)
    m1[factor] = {
        "count": len(matched),
        "total_signal": sum(c["_signal"] for c in matched),
        "top_comments": top_comments(matched, 5),
    }

# Top 20 最高信号评论（跨所有因子）
all_top = []
seen_top = set()
for v in m1.values():
    for c in v["top_comments"]:
        if c["text"] not in seen_top:
            seen_top.add(c["text"])
            all_top.append(c)
all_top.sort(key=lambda x: x["signal"], reverse=True)

insights["module1_viral"] = {"factors": m1, "top_viral_comments": all_top[:20]}
print("  " + ", ".join(f"{k}={v['count']}" for k, v in m1.items()))

# ─── 模块 2：JTBD ────────────────────────────────────────────────────────────────

print("Module 2: JTBD...")

jtbd = {
    "active_play": ["exercise", "active", "moving", "physical", "running", "jumping",
                    "workout", "fitness", "get up", "burn", "burn calories", "get moving"],
    "screen_alt": ["away from screen", "instead of", "replace", "no more", "put down",
                   "screen time", "less screen", "off the screen", "off the phone",
                   "off the tablet", "off the ipad", "away from (the )?(tv|phone|tablet|ipad)"],
    "family_bond": ["together", "family", "bonding", "quality time", "whole family",
                    "family (time|night|fun|game)", "everyone", "all of us",
                    "dad", "mom", "parents", "grandpa", "grandma", "siblings"],
    "indoor_play": ["inside", "indoors", "rainy day", "snow day", "winter",
                    "stuck inside", "living room", "basement", "bad weather",
                    "can't go outside", "cold outside"],
    "gift_solution": ["gift", "present", "surprise", "birthday", "christmas", "holiday",
                      "perfect gift", "wrapped", "under the tree", "stocking",
                      "bought (this|it|one) for", "got (this|it|one) for"],
    "social_status": ["school", "friends", "neighbor", "everyone has", "show",
                      "impressed", "classmates", "kids at school", "told their friends"],
}

m2 = {}
for job, kws in jtbd.items():
    matched = []
    for c in all_comments:
        t = tl(c)
        if any(re.search(kw, t) for kw in kws):
            matched.append(c)
    avg_digg = sum(c.get("diggCount", 0) for c in matched) / max(len(matched), 1)
    m2[job] = {
        "count": len(matched),
        "avg_diggCount": round(avg_digg, 1),
        "total_signal": sum(c["_signal"] for c in matched),
        "top_comments": top_comments(matched, 3),
    }

sorted_jobs = sorted(m2.items(), key=lambda x: x[1]["total_signal"], reverse=True)
functional = sum(m2[j]["count"] for j in ["active_play", "screen_alt", "indoor_play"])
emotional = sum(m2[j]["count"] for j in ["family_bond", "gift_solution", "social_status"])

insights["module2_jtbd"] = {
    "jobs": m2,
    "sorted_jobs": [{"job": k, **v} for k, v in sorted_jobs],
    "functional_count": functional,
    "emotional_count": emotional,
}
print(f"  Top JTBD: {sorted_jobs[0][0]} ({sorted_jobs[0][1]['count']})")

# ─── 模块 3：用户画像 ─────────────────────────────────────────────────────────────

print("Module 3: Personas...")

persona_defs = {
    "Fun Parent": {
        "patterns": [r"my (son|daughter|kid|child|children|boys|girls|little one)",
                     r"(my|our) (kids?|children)"],
        "exclude": ["nephew", "niece", "grandkid", "bought for", "gift for"],
        "desc": "为自家孩子买，追求亲子互动",
    },
    "Gift Hunter": {
        "patterns": [r"my (nephew|niece|grandkid|grandson|granddaughter)",
                     r"(bought|got|getting|ordered|buying|purchasing) (this |it |one )?(for|as) (a )?(gift|present|surprise)",
                     r"(gift|present) for (my|a|the|his|her)"],
        "exclude": [],
        "desc": "给他人买礼物的买家",
    },
    "TikTok Parent": {
        "patterns": [r"(saw|found|seen) (this |it )?(on tiktok|on here|in my feed|on my fyp)",
                     r"tiktok (made|had|got|sent|showed) me",
                     r"(my |the )?(fyp|for you( page)?|algorithm|feed)"],
        "exclude": [],
        "desc": "刷 TikTok 种草购买",
    },
    "Active Parent": {
        "patterns": [r"(too much |all that )?(screen time|time on (the )?(phone|tablet|ipad|screen))",
                     r"get(ting)? (them |kids? )?(more )?(active|moving|exercise|off)",
                     r"(off|away from) (the )?(phone|tablet|ipad|screen)",
                     r"(instead of|replace|alternative to) (the )?(tv|phone|tablet|ipad|screen)"],
        "exclude": [],
        "desc": "担心孩子宅，寻找屏幕替代",
    },
    "Kid Influencer": {
        "patterns": [r"(my )?(kid|son|daughter|child)(ren)? (saw|asked|begged|wanted|loves|found)",
                     r"(begged|kept asking|won't stop asking)",
                     r"on (their|his|her) (wish ?list|christmas list)",
                     r"they (saw|found|wanted|asked for) (it|this|one)"],
        "exclude": [],
        "desc": "孩子主动要求，反向种草",
    },
}

m3 = {}
for name, cfg in persona_defs.items():
    matched = []
    for c in all_comments:
        t = tl(c)
        if any(re.search(p, t) for p in cfg["patterns"]):
            if not any(ex in t for ex in cfg.get("exclude", [])):
                matched.append(c)
    m3[name] = {
        "count": len(matched),
        "total_signal": sum(c["_signal"] for c in matched),
        "desc": cfg["desc"],
        "top_comments": top_comments(matched, 3),
    }

total_p = sum(v["count"] for v in m3.values())
for v in m3.values():
    v["percentage"] = round(v["count"] / max(total_p, 1) * 100, 1)

insights["module3_personas"] = {
    "personas": m3,
    "total": total_p,
    "sorted": sorted(m3.items(), key=lambda x: x[1]["count"], reverse=True),
}
print(f"  Top persona: {max(m3, key=lambda x: m3[x]['count'])}")

# ─── 模块 4：购买触发点 ──────────────────────────────────────────────────────────

print("Module 4: Triggers...")

triggers = {
    "礼物购买 🎁": [
        r"(christmas|birthday|holiday|xmas) (gift|present)",
        r"(as a|as the|for a) (gift|present|surprise)",
        r"(perfect|great|best|ideal) (gift|present)",
        r"under the (christmas )?tree", r"stocking stuffer",
        r"(wrapped|wrapping) (it|this|one)",
    ],
    "TikTok发现 📱": [
        r"(saw|found|seen) (this|it) on tiktok",
        r"tiktok (made|had|got|sent|showed) me",
        r"(my |the )?(fyp|for you( page)?|feed|algorithm)",
        r"(went |gone )?viral( on tiktok)?",
    ],
    "问题触发 🔍": [
        r"(was |been )?(looking|searching) for (something|this|a way)",
        r"(couldn't|can't) find (something|anything|a game)",
        r"finally found (something|this|what)",
        r"needed (something|a game|an alternative)",
    ],
    "社交证明 👥": [
        r"everyone (loves?|has|is playing|wants|is (talking|raving) about)",
        r"all the kids", r"neighbor(s)? (has|have|got|bought)",
        r"(so many|all my) (people|friends|parents|moms?)",
        r"(kids at |at )?(school|daycare) (talking|have|has|want)",
    ],
    "冲动购买 ⚡": [
        r"(had|have) to (buy|get|order|have) (it|this|one)",
        r"(just |immediately )?(bought|ordered|got|purchased) (it|this|one)",
        r"couldn't resist", r"one click", r"impulse (buy|purchase)",
        r"before I (knew it|could stop myself)",
    ],
    "孩子要求 🧒": [
        r"(my )?(kid|son|daughter|child)(ren)? (asked|begged|wanted|keeps asking)",
        r"begged (me|us) (to|for)",
        r"kept (asking|begging) (for|about)",
        r"on (their|his|her) (wish ?list|christmas list)",
        r"they (saw|found|wanted|asked) (it|this|one|for it)",
    ],
}

m4 = {}
for name, patterns in triggers.items():
    matched = []
    for c in all_comments:
        t = tl(c)
        if any(re.search(p, t) for p in patterns):
            matched.append(c)
    m4[name] = {
        "count": len(matched),
        "total_signal": sum(c["_signal"] for c in matched),
        "top_comments": top_comments(matched, 3),
    }

sorted_triggers = sorted(m4.items(), key=lambda x: x[1]["total_signal"], reverse=True)
insights["module4_triggers"] = {
    "triggers": m4,
    "sorted_triggers": [{"name": k, **v} for k, v in sorted_triggers],
}
print(f"  Top trigger: {sorted_triggers[0][0]} ({sorted_triggers[0][1]['count']})")

# ─── 模块 5：痛点/痒点/爽点 ─────────────────────────────────────────────────────

print("Module 5: Pain/Itch/Wow...")

pain_kws = [
    r"(too much |all that )?(screen time|time on (the )?(phone|tablet|ipad|tv))",
    r"(always |constantly )(on|glued to) (the )?(phone|tablet|ipad|screen|tv)",
    r"(bored|nothing to do|stuck inside|can't go outside)",
    r"(tired of|sick of|hate) (the )?(screen|phone|tablet|ipad|tv|same|boring)",
    r"(outgrown|grew out of|too old for)",
    r"(too expensive|costs? too much) (elsewhere|at|for)",
    r"rainy (day|weather|season)", r"snow day", r"bad weather",
    r"sedentary", r"(not enough |need more )?(exercise|activity|movement)",
]
itch_kws = [
    r"(wish|hope|would love|would be (nice|great|perfect|better) if)",
    r"if only (it|they|there)",
    r"(next version|next (model|iteration|update)|update (this|the))",
    r"(could use|needs?|should have|would want) (more|a|an)",
    r"almost perfect", r"only (complaint|issue|problem|thing|con) is",
    r"(would be perfect (if|with)|just needs?)",
]
wow_kws = [
    r"obsessed", r"addicted",
    r"(won't|can't|doesn't|never) stop (playing|wanting|asking)",
    r"been playing (all day|for hours|non.?stop|since (christmas|we got|i got))",
    r"(reaction|face|look) was (priceless|everything|amazing|so funny|so cute)",
    r"their (face|reaction|expression) when",
    r"(screaming|screamed|jumping|lost (it|their mind|his mind|her mind))",
    r"best (purchase|buy|decision|investment|gift|thing) (i('ve| have) )?(ever )?(made|bought|got)",
    r"worth every (penny|cent|dollar)",
    r"(exceeded|beyond|above) (my |our |all )?(expectations?)",
    r"(blown away|didn't expect|never expected)",
    r"(absolutely|completely|totally|genuinely) (love|loved|amazing|obsessed)",
    r"(so|very|incredibly|absolutely) worth (it|the (price|money|cost))",
]

def match_kws(comments, patterns):
    matched = []
    kw_counts = Counter()
    for c in comments:
        t = tl(c)
        for p in patterns:
            if re.search(p, t):
                matched.append(c)
                kw_counts[p] += 1
                break
    return matched, kw_counts

pain_m, pain_c = match_kws(all_comments, pain_kws)
itch_m, itch_c = match_kws(all_comments, itch_kws)
wow_m, wow_c = match_kws(all_comments, wow_kws)

insights["module5_needs"] = {
    "pain": {
        "count": len(pain_m),
        "keyword_freq": dict(pain_c.most_common(12)),
        "top_comments": top_comments(pain_m, 10),
    },
    "itch": {
        "count": len(itch_m),
        "keyword_freq": dict(itch_c.most_common(12)),
        "top_comments": top_comments(itch_m, 10),
    },
    "wow": {
        "count": len(wow_m),
        "keyword_freq": dict(wow_c.most_common(12)),
        "top_comments": top_comments(wow_m, 10),
    },
    "value_prop": "通过家庭活动替代屏幕时间，用孩子无法预料的惊喜反应创造亲子记忆，成为值得反复推荐的最佳礼物选择",
}
print(f"  Pain={len(pain_m)}, Itch={len(itch_m)}, Wow={len(wow_m)}")

# ─── 模块 6：使用场景 ─────────────────────────────────────────────────────────────

print("Module 6: Scenarios...")

scenarios = {
    "室内 🏠": [r"(living room|basement|inside|indoors|apartment|home|bedroom|playroom)"],
    "季节/天气 🌨": [r"(rainy|snow) day", r"(winter|summer|spring|fall) break",
                   r"school break", r"(stuck|trapped) inside", r"bad weather"],
    "特殊场合 🎉": [r"(party|playdate|sleepover|game night|thanksgiving|halloween)",
                  r"(christmas|birthday) (morning|party|eve)", r"holiday"],
    "独玩 👤": [r"by (them|him|her)sel(f|ves)", r"\balone\b", r"solo", r"by (my|your)self"],
    "多人同玩 👨‍👩‍👧": [r"(with |and )(friends?|siblings?|cousins?|family|everyone)",
                    r"(whole |entire |all the )(family|house|neighborhood)",
                    r"(multiplayer|multi.player|2 players?|together)"],
    "停不下来 ⏱": [r"(all day|all night|for hours|\d+ hours?)",
                  r"(can't|won't|doesn't|never) (want to )?stop",
                  r"still playing (since|after|weeks?|months?)",
                  r"(weeks?|months?) (later|after|and (still|they))"],
    "全年龄段 👴": [r"(all ages|every age|any age)",
                  r"even (the )?(adults?|parents?|dad|mom|grandpa|grandma|husband|wife|teens?)",
                  r"(kids and adults|adults and kids|8 to 80|young and old)"],
}

m6 = {}
for name, patterns in scenarios.items():
    matched = []
    for c in all_comments:
        t = tl(c)
        if any(re.search(p, t) for p in patterns):
            matched.append(c)
    m6[name] = {
        "count": len(matched),
        "total_signal": sum(c["_signal"] for c in matched),
        "top_comments": top_comments(matched, 3),
    }

insights["module6_scenarios"] = {
    "scenarios": m6,
    "sorted": sorted(m6.items(), key=lambda x: x[1]["count"], reverse=True),
}
print("  " + ", ".join(f"{k}={v['count']}" for k, v in m6.items()))

# ─── 模块 7：未被满足的需求 ──────────────────────────────────────────────────────

print("Module 7: Unmet needs...")

unmet = {
    "更多游戏模式 🎮": [
        r"more (games?|modes?|levels?|activities|challenges|options|content)",
        r"(wish|hope|want) (there were|it had|they (would add|added|made)) more",
        r"only (has|comes with|includes?) \d+ (games?|modes?)",
        r"limited (games?|content|options|selection)",
        r"(need|needs?) (more|better|different) (games?|content|modes?)",
    ],
    "硬件/耐用性 🔧": [
        r"(battery|charge|charging) (dies?|drains?|doesn'?t last|life|issue|problem)",
        r"(sensor|tracker?|tracking|detector) (doesn'?t|not|off|wrong|miss|glitch)",
        r"(broke|broken|break(s|ing)?|stopped working|doesn'?t work (anymore|any more))",
        r"(lag(gy)?|delay(ed)?|slow response|not (responsive|accurate))",
        r"(falls? off|slips?|doesn'?t fit|too (big|small|loose|tight))",
    ],
    "价格/性价比 💰": [
        r"(too expensive|too much|price(y|ier)?|overpriced)",
        r"(wish it (was|were)|hope it (goes?|will (go|come)) )(cheaper|on sale|lower)",
        r"(discount|coupon|promo(tion)?|deal|sale|code)",
        r"(can'?t afford|out of (my |our )?budget)",
        r"(worth the (price|money|cost)|is (it|this) worth)",
        r"(not worth|waste of money) (it|the price|the money)",
    ],
    "订阅制顾虑 📋": [
        r"(subscription|monthly (fee|payment|charge)|pay (monthly|per month))",
        r"(have to |need to |must )?(subscribe|pay) to (play|access|get|unlock)",
        r"(only|just) (comes? with|includes?) \d+ (games?|free games?)",
        r"(can'?t buy|no way to (buy|purchase|own)) (individual |the )?(games?|content)",
        r"(lose|lost) (everything|access|your games?) (if|when) (you (cancel|stop|don'?t renew))",
    ],
    "库存/购买渠道 📦": [
        r"(out of stock|sold out|unavailable|not available|can'?t find (it|this|one))",
        r"(where (to|can (i|we)) (buy|get|find|order|purchase))",
        r"(shipping|delivery|when (does|will) it (arrive|come|ship))",
        r"(available in|ship(ping)? to) (canada|uk|australia|mexico|europe|international)",
    ],
}

m7 = {}
for name, patterns in unmet.items():
    matched = []
    for c in all_comments:
        t = tl(c)
        if any(re.search(p, t) for p in patterns):
            matched.append(c)
    avg_sig = sum(c["_signal"] for c in matched) / max(len(matched), 1)
    m7[name] = {
        "count": len(matched),
        "avg_signal": round(avg_sig, 1),
        "total_signal": sum(c["_signal"] for c in matched),
        "top_comments": top_comments(matched, 5),
    }

sorted_unmet = sorted(m7.items(), key=lambda x: x[1]["count"], reverse=True)
insights["module7_unmet"] = {
    "needs": m7,
    "sorted_needs": [{"name": k, **v} for k, v in sorted_unmet],
}
print("  " + ", ".join(f"{k}={v['count']}" for k, v in m7.items()))

# ─── 模块 8：情感旅程 ─────────────────────────────────────────────────────────────

print("Module 8: Emotional journey...")

pos_words = ["love", "amazing", "awesome", "great", "wonderful", "fantastic", "perfect",
             "obsessed", "best", "excellent", "incredible", "worth", "recommend",
             "happy", "joy", "fun", "excited", "thrilled", "priceless", "blessed"]
neg_words = ["bad", "terrible", "awful", "horrible", "disappointed", "broken",
             "waste", "refund", "return", "doesn't work", "stopped working",
             "problem", "issue", "complaint", "annoying", "frustrating",
             "not worth", "overpriced", "misleading", "false"]

def sentiment(text):
    t = text.lower()
    p = sum(1 for w in pos_words if w in t)
    n = sum(1 for w in neg_words if w in t)
    return "positive" if p > n else ("negative" if n > p else "neutral")

buckets = {"0-24h": [], "1-7d": [], "7-30d": [], "30d+": []}
for c in all_comments:
    vt = c.get("_video_create_time", 0)
    ct = c.get("createTime", 0)
    if not vt or not ct or ct < vt:
        continue
    delta_h = (ct - vt) / 3600
    if delta_h <= 24:
        buckets["0-24h"].append(c)
    elif delta_h <= 168:
        buckets["1-7d"].append(c)
    elif delta_h <= 720:
        buckets["7-30d"].append(c)
    else:
        buckets["30d+"].append(c)

bucket_meta = {
    "0-24h":  ("即时反应（0-24小时）", "好奇 / 种草 / 询问"),
    "1-7d":   ("购买决策期（1-7天）",  "询问 / 比价 / 下单"),
    "7-30d":  ("使用体验期（7-30天）", "开箱 / 初体验 / 好评"),
    "30d+":   ("长期口碑（30天+）",    "耐用性 / 复购 / 持续推荐"),
}

m8 = {}
for key, comments in buckets.items():
    emo = Counter(sentiment(c.get("text", "")) for c in comments)
    total = len(comments)
    label, theme = bucket_meta[key]
    m8[key] = {
        "label": label, "theme": theme,
        "count": total,
        "positive": emo["positive"],
        "negative": emo["negative"],
        "neutral": emo["neutral"],
        "positive_pct": round(emo["positive"] / max(total, 1) * 100, 1),
        "negative_pct": round(emo["negative"] / max(total, 1) * 100, 1),
        "top_comments": top_comments(comments, 5),
    }

insights["module8_journey"] = {
    "buckets": m8,
    "bucket_order": ["0-24h", "1-7d", "7-30d", "30d+"],
}
print("  " + ", ".join(f"{k}={v['count']}" for k, v in m8.items()))

# ─── Meta ────────────────────────────────────────────────────────────────────────

insights["meta"] = {
    "total_comments": len(all_comments),
    "valid_videos": valid_files,
    "total_videos": len(videos),
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

with open("insights_data.json", "w", encoding="utf-8") as f:
    json.dump(insights, f, ensure_ascii=False, indent=2)

print()
print("insights_data.json saved!")
print(f"  {len(all_comments)} comments from {valid_files} videos analyzed")
