#!/usr/bin/env python3
"""kb_sankey_v2_annotated.py

Hierarchical Sankey diagram optimized for EMNLP single-column appendix.
Features:
1. Vibrant, professional color palette with high contrast for Search vs Productivity.
2. Optimized category layout order to eliminate empty gaps and maximize balance.
3. App names are rendered via custom layout annotations cleanly aligned to the right.
4. Rendered at extreme high resolution (scale=4) with no truncation.
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

# 🚀【延续v2核心设计】精心编排的交错场景顺序，完美平衡流线，彻底杜绝空白断层
CAT_ORDER = [
    "System Tool",
    "Productivity",
    "Video & Music",
    "Search & Browser",
    "Social Media",
    "Shopping",
    "Lifestyle",
    "Travel",
]

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

# 🎨【延续v2高亮色彩】纯正明亮色彩
LANG_COLOR = {"cn": (0, 51, 238), "en": (118, 0, 137)}
CAT_COLOR = {
    "System Tool":      (243, 178, 38),   # 阳光金黄
    "Search & Browser": (38, 149, 224),   # 明朗海蓝
    "Productivity":     (74, 134, 232),   # 科技深蓝
    "Social Media":     (0, 166, 153),    # 翡翠松石绿
    "Video & Music":    (204, 102, 153),  # 绚丽玫红
    "Shopping":         (139, 87, 42),    # 浓郁咖啡棕
    "Travel":           (92, 184, 92),    # 生机嫩绿
    "Lifestyle":        (230, 92, 134),   # 珊瑚亮粉
    # "System Tool":      (243, 178, 38),   # 暖金黄
    # "Search & Browser": (30, 100, 230),   # 深邃明朗蓝
    # "Productivity":     (130, 175, 240),  # 冰川浅蓝（与Search彻底拉开色差）
    # "Social Media":     (0, 166, 153),    # 翡翠松石绿
    # "Video & Music":    (204, 102, 153),  # 绚丽玫红
    # "Shopping":         (139, 87, 42),    # 浓郁咖啡棕
    # "Travel":           (92, 184, 92),    # 生机草绿
    # "Lifestyle":        (240, 70, 110),   # 珊瑚红
}

# 🎨【延续v2多元色彩盘】
APP_PALETTE = [
    (119, 221, 119), (255, 179, 71),  (255, 105, 97),  (177, 156, 217),
    (100, 149, 237), (255, 182, 193), (0, 206, 209),  (154, 205, 50),
    (218, 112, 214), (244, 164, 96),  (127, 255, 212), (250, 128, 114),
    (186, 85, 211),  (64, 224, 208),  (144, 238, 144), (255, 215, 0),
    (255, 99, 71),   (123, 104, 238), (30, 144, 255),  (147, 112, 219),
    (60, 179, 113),  (220, 20, 60),   (0, 191, 255),   (255, 127, 80),
    (46, 139, 87),   (138, 43, 226),  (210, 105, 30),  (32, 178, 170)
]

LANG_LABEL = {"cn": "CN (Chinese app)", "en": "EN (international app)"}

# 画布全局物理尺寸规格定义（完美契合附录单栏横板空间）
_W, _H       = 1600, 1800
_ML, _MR     = 35, 210    # 拓宽右侧留白边界（210px）为独立注解文本提供完美的展示保护区
_MT, _MB     = 25, 80     # 底部留白防止边缘截断


def rgba(rgb, a: float) -> str:
    return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{a})"


def main() -> None:
    apps = [a for a in json.load(open(KB, encoding="utf-8")) if a.get("action_object_str")]
    missing = [a["id"] for a in apps if a["id"] not in APP_INFO]
    assert not missing, f"unmapped app ids: {missing}"

    rows = []
    for a in apps:
        name, lang = APP_INFO[a["id"]]
        cat = SCEN2CAT[a["scenario"]]
        rows.append({"id": a["id"], "name": name, "lang": lang, "cat": cat,
                     "nfn": len(a["action_object_str"])})

    # ---- nodes ----
    labels, ncolor, nx, ny = [], [], [], []
    idx: dict[str, int] = {}

    def add(key, label, color, x):
        idx[key] = len(labels)
        labels.append(label); ncolor.append(color); nx.append(x); ny.append(0.0)

    # 构建左侧源头与中间场景层
    for lang in ("cn", "en"):
        add(f"L::{lang}", LANG_LABEL[lang], rgba(LANG_COLOR[lang], 1.0), 0.001)
    for cat in CAT_ORDER:
        add(f"C::{cat}", cat, rgba(CAT_COLOR[cat], 1.0), 0.45)
    
    # 按照权重排序构建最右侧应用层
    cat_rank = {c: i for i, c in enumerate(CAT_ORDER)}
    sorted_rows = sorted(rows, key=lambda r: (cat_rank[r["cat"]], r["lang"], -r["nfn"], r["name"]))
    
    for i, r in enumerate(sorted_rows):
        app_rgb = APP_PALETTE[i % len(APP_PALETTE)]
        # 🚀【关键注入】最右侧的 node.label 设为空字符串 ""。名字将通过下方的独立 annotation 绘制。
        add(f"A::{r['id']}", "", rgba(app_rgb, 0.95), 0.999)

    # ---- links ----
    src, tgt, val, lcolor = [], [], [], []
    lang_cat = defaultdict(int)
    for r in rows:
        lang_cat[(r["lang"], r["cat"])] += r["nfn"]
    
    # 🚀【鲜艳度平衡】第一层流线 Alpha = 0.42，第二层流线 Alpha = 0.50，高对比度且高度鲜艳
    for (lang, cat), v in lang_cat.items():
        src.append(idx[f"L::{lang}"]); tgt.append(idx[f"C::{cat}"])
        val.append(v); lcolor.append(rgba(CAT_COLOR[cat], 0.42))
        
    for r in rows:
        src.append(idx[f"C::{r['cat']}"]); tgt.append(idx[f"A::{r['id']}"])
        val.append(r["nfn"]); lcolor.append(rgba(CAT_COLOR[r["cat"]], 0.50))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=ncolor, x=nx, y=ny,
                  pad=16, 
                  thickness=32,  # 保持大宽度色块矩形柱厚度
                  line=dict(color="rgba(255,255,255,0.95)", width=1.2)),
        link=dict(source=src, target=tgt, value=val, color=lcolor),
    ))
    
    # ---- 🚀 提取并移植的右侧独立文字标签生成算法 🚀 ----
    plot_h_px = _H - _MT - _MB          # 算得可用绘图区域的净高度 (1695 px)
    n_apps    = len(sorted_rows)
    pad_px    = 16                      # 必须与 node.pad 严格一致以防止坐标偏移
    total_nfn = sum(r["nfn"] for r in sorted_rows)
    avail_h   = plot_h_px - (n_apps - 1) * pad_px   # 扣除间距后分配给色块立柱的总像素高度

    plot_w_px = _W - _ML - _MR          # 绘图区域的物理净宽度 (1355 px)
    # x=1.0 代表绘图区最右边界，加 6.0/plot_w_px 代表向右平移 6 个像素，达成完美的贴合呼吸感
    ann_x     = 1.0 + 6.0 / plot_w_px 

    annotations = []
    cum_h = 0.0
    for r in sorted_rows:
        node_h_px = r["nfn"] / total_nfn * avail_h
        y_frac    = (cum_h + node_h_px / 2.0) / plot_h_px   # 从顶部向下的物理占比比例 (0=顶, 1=底)
        paper_y   = 1.0 - y_frac                             # 转换为 Plotly 视口坐标 (0=底, 1=顶)
        
        annotations.append(dict(
            x=ann_x, y=paper_y,
            xref="paper", yref="paper",
            text=r["name"],
            showarrow=False,
            xanchor="left", yanchor="middle",  # 文本向右水平对齐，纵向居中色块形心
            font=dict(size=16, family="Arial, Helvetica, sans-serif", color="#111111"),
        ))
        cum_h += node_h_px + pad_px

    # 更新整体布局
    fig.update_layout(
        font=dict(family="Arial, Helvetica, sans-serif", size=18, color="#111111"),
        paper_bgcolor="white", 
        plot_bgcolor="white",
        margin=dict(l=_ML, r=_MR, t=_MT, b=_MB),
        annotations=annotations,  # 🚀 将精心计算的独立标签层注入到布局中
    )

    png = os.path.join(HERE, "kb_sankey_v2_perfect.png")
    html = os.path.join(HERE, "kb_sankey_v2_perfect.html")
    fig.write_html(html)
    
    # 高清渲染（采样率提升至 4，以无损视网膜精度输出）
    fig.write_image(png, width=_W, height=_H, scale=4)
    print(f"Success! Refined V2 version with right-side annotations generated.")


if __name__ == "__main__":
    main()