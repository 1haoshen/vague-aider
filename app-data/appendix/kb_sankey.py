#!/usr/bin/env python3
"""kb_sankey.py

Hierarchical Sankey of the AppUi-final.json knowledge base, restricted to the
57 apps that carry an ``action_object_str`` (explicit GUI action chains).

Three columns:

    Language (CN / EN)  ->  App category (8)  ->  App name (English, 57)

The 11 raw KB ``scenario`` tags are consolidated into 8 app categories; every
app is tagged CN (Chinese-origin app) or EN (international app) and its name is
romanised / translated to English. Ribbon width = number of documented
functions of each app, so a thicker flow == a richer action repertoire.

Palette follows the colourful reference figure: one vivid hue per category,
translucent ribbons of the same hue.

Outputs: kb_sankey.png and kb_sankey.html.  Run:  python3 kb_sankey.py
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
KB = os.path.join(REPO_ROOT, "app-data", "knowledge-base", "AppUi-final.json")

# 11 raw scenarios -> 8 app categories.
SCEN2CAT = {
    "系统应用": "System Tool",
    "搜索引擎": "Search & Browser",
    "办公协助": "Productivity",
    "修图软件": "Productivity",
    "社交媒体": "Social Media",
    "视频播放": "Video & Music",
    "音乐电台": "Video & Music",
    "生活购物": "Shopping",
    "旅游出行": "Travel",
    "外卖平台": "Lifestyle",
    "健康与教育": "Lifestyle",
}
CAT_ORDER = ["System Tool", "Search & Browser", "Productivity", "Social Media",
             "Video & Music", "Shopping", "Travel", "Lifestyle"]

# Per-app: KB id -> (English name, language tag).
APP_INFO: dict[int, tuple[str, str]] = {
    1: ("iQIYI", "cn"), 2: ("Tencent Video", "cn"), 3: ("Youku", "cn"),
    5: ("Bilibili", "cn"), 6: ("Douyin", "cn"), 8: ("NetEase Music", "cn"),
    9: ("QQ Music", "cn"), 10: ("YouTube", "en"), 11: ("TikTok", "en"),
    18: ("Tencent Meeting", "cn"), 22: ("Feishu", "cn"), 23: ("Gmail", "en"),
    28: ("Notion", "en"), 29: ("Amap", "cn"), 31: ("Ctrip", "cn"),
    32: ("Baidu Maps", "cn"), 39: ("Booking", "en"), 40: ("Google Maps", "en"),
    41: ("Tripadvisor", "en"), 44: ("Agoda", "en"), 51: ("WeChat", "cn"),
    59: ("ChatGPT", "en"), 63: ("Doubao", "cn"), 67: ("Quark", "cn"),
    68: ("Chrome", "en"), 71: ("Keep", "cn"), 76: ("Ximalaya", "cn"),
    78: ("Meitu", "cn"), 85: ("Messages", "cn"), 86: ("Notes", "cn"),
    88: ("Photos", "cn"), 89: ("Clock", "cn"), 90: ("Weather", "cn"),
    92: ("Calendar", "cn"), 93: ("Xiaohongshu", "cn"), 94: ("Baidu", "cn"),
    95: ("Instagram", "en"), 96: ("Amazon", "en"), 97: ("Qunar", "cn"),
    98: ("Alibaba", "cn"), 99: ("Facebook", "en"), 100: ("Google Chrome", "en"),
    101: ("X", "en"), 102: ("Walmart", "en"), 103: ("eBay", "en"),
    104: ("Amazon Shopping", "en"), 105: ("Fandango", "en"),
    106: ("Google Play Store", "en"), 107: ("Maoyan", "cn"), 108: ("Damai", "cn"),
    109: ("Meituan", "cn"), 110: ("Dianping", "cn"), 111: ("JD.com", "cn"),
    112: ("Taobao", "cn"), 113: ("Pinduoduo", "cn"), 114: ("RedNote", "en"),
    115: ("Zhihu", "cn"),
}

# Vivid hue per category (reference-style); translucent ribbons reuse the hue.
CAT_COLOR = {
    "System Tool":      (242, 183, 30),
    "Search & Browser": (54, 124, 214),
    "Productivity":     (236, 122, 54),
    "Social Media":     (23, 172, 162),
    "Video & Music":    (146, 92, 209),
    "Shopping":         (162, 110, 64),
    "Travel":           (72, 168, 86),
    "Lifestyle":        (226, 84, 158),
}
LANG_COLOR = {"cn": (52, 73, 94), "en": (125, 88, 168)}
LANG_LABEL = {"cn": "CN (Chinese app)", "en": "EN (international app)"}


def rgba(rgb, a):
    return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{a})"


def main() -> None:
    apps = [a for a in json.load(open(KB, encoding="utf-8")) if a.get("action_object_str")]
    missing = [a["id"] for a in apps if a["id"] not in APP_INFO]
    assert not missing, f"unmapped app ids: {missing}"
    print(f"apps with action_object_str: {len(apps)}")

    # Enrich.
    rows = []
    for a in apps:
        name, lang = APP_INFO[a["id"]]
        cat = SCEN2CAT[a["scenario"]]
        rows.append({"id": a["id"], "name": name, "lang": lang, "cat": cat,
                     "nfn": len(a["action_object_str"])})

    by_lang = {"cn": sum(r["nfn"] for r in rows if r["lang"] == "cn"),
               "en": sum(r["nfn"] for r in rows if r["lang"] == "en")}
    n_cn = sum(1 for r in rows if r["lang"] == "cn")
    print(f"apps: {n_cn} CN / {len(rows)-n_cn} EN | functions: {by_lang}")

    # ---- nodes ----
    labels, ncolor, nx, ny = [], [], [], []
    idx: dict[str, int] = {}

    def add(key, label, color, x):
        idx[key] = len(labels)
        labels.append(label); ncolor.append(color); nx.append(x); ny.append(0.0)

    for lang in ("cn", "en"):
        add(f"L::{lang}", LANG_LABEL[lang], rgba(LANG_COLOR[lang], 0.95), 0.001)
    for cat in CAT_ORDER:
        add(f"C::{cat}", cat, rgba(CAT_COLOR[cat], 0.95), 0.5)
    # apps grouped by category, then lang, then richness
    cat_rank = {c: i for i, c in enumerate(CAT_ORDER)}
    for r in sorted(rows, key=lambda r: (cat_rank[r["cat"]], r["lang"], -r["nfn"], r["name"])):
        add(f"A::{r['id']}", f"{r['name']} ({r['nfn']})",
            rgba(CAT_COLOR[r["cat"]], 0.85), 0.999)

    # ---- links ----
    src, tgt, val, lcolor = [], [], [], []
    lang_cat = defaultdict(int)
    for r in rows:
        lang_cat[(r["lang"], r["cat"])] += r["nfn"]
    for (lang, cat), v in lang_cat.items():
        src.append(idx[f"L::{lang}"]); tgt.append(idx[f"C::{cat}"])
        val.append(v); lcolor.append(rgba(CAT_COLOR[cat], 0.38))
    for r in rows:
        src.append(idx[f"C::{r['cat']}"]); tgt.append(idx[f"A::{r['id']}"])
        val.append(r["nfn"]); lcolor.append(rgba(CAT_COLOR[r["cat"]], 0.42))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=ncolor, x=nx, y=ny,
                  pad=7, thickness=15,
                  line=dict(color="rgba(255,255,255,0.6)", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color=lcolor),
    ))
    fig.update_layout(
        title=dict(text="Knowledge base: Language → App category → App "
                        "(57 apps with action chains; ribbon width = #functions)",
                   x=0.5, font=dict(size=16)),
        font=dict(family="DejaVu Sans", size=11.5, color="#222"),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=10),
    )

    png = os.path.join(HERE, "kb_sankey.png")
    html = os.path.join(HERE, "kb_sankey.html")
    fig.write_html(html)
    fig.write_image(png, width=1180, height=1500, scale=2)
    print(f"wrote: {os.path.basename(png)}, {os.path.basename(html)}")


if __name__ == "__main__":
    main()
