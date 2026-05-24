#!/usr/bin/env python3
"""kb_sankey.py

Hierarchical Sankey diagram of the AppUi-final.json knowledge base, restricted
to the apps that carry an ``action_object_str`` (i.e. apps for which we authored
explicit GUI action chains).

Three columns, mirroring the reference figure (task category -> app type -> app
name):

    Domain (4)  ->  Scenario (11)  ->  App (57)

Link width encodes the number of documented functions (``action_object_str``
entries) of each app, so a thicker ribbon == a richer action repertoire.

Structural labels (Domain / Scenario) are in English for the paper; app names
are kept verbatim (proper nouns, mostly Chinese) and rendered with Noto Sans CJK.

Outputs: kb_sankey.png  (vector-quality raster via kaleido) and kb_sankey.html.
Run:  python3 kb_sankey.py
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
KB = os.path.join(REPO_ROOT, "app-data", "knowledge-base", "AppUi-final.json")

# Chinese scenario -> coarse domain  /  English scenario label
SCENARIO_DOMAIN = {
    "系统应用": "Tools & Productivity",
    "办公协助": "Tools & Productivity",
    "搜索引擎": "Tools & Productivity",
    "修图软件": "Tools & Productivity",
    "社交媒体": "Social & Entertainment",
    "视频播放": "Social & Entertainment",
    "音乐电台": "Social & Entertainment",
    "生活购物": "Life Services",
    "外卖平台": "Life Services",
    "健康与教育": "Life Services",
    "旅游出行": "Travel & Mobility",
}
SCENARIO_EN = {
    "系统应用": "System Apps",
    "办公协助": "Office & Productivity",
    "搜索引擎": "Search Engine",
    "修图软件": "Photo Editing",
    "社交媒体": "Social Media",
    "视频播放": "Video Streaming",
    "音乐电台": "Music & Radio",
    "生活购物": "Shopping",
    "外卖平台": "Food Delivery",
    "健康与教育": "Health & Education",
    "旅游出行": "Travel",
}
# Stable domain order (left column, top -> bottom) and palette.
DOMAIN_ORDER = ["Tools & Productivity", "Social & Entertainment",
                "Life Services", "Travel & Mobility"]
DOMAIN_COLOR = {
    "Tools & Productivity": (76, 114, 176),    # blue
    "Social & Entertainment": (221, 132, 82),  # orange
    "Life Services": (85, 168, 104),           # green
    "Travel & Mobility": (196, 78, 82),        # red
}


def rgba(rgb, a):
    return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{a})"


def main() -> None:
    apps = [a for a in json.load(open(KB, encoding="utf-8")) if a.get("action_object_str")]
    print(f"apps with action_object_str: {len(apps)}")

    # Group apps by scenario; keep a deterministic ordering.
    by_scen: dict[str, list[dict]] = defaultdict(list)
    for a in apps:
        by_scen[a.get("scenario", "(none)")].append(a)

    # Order scenarios by their domain, then by app count desc.
    scen_order = sorted(
        by_scen,
        key=lambda s: (DOMAIN_ORDER.index(SCENARIO_DOMAIN.get(s, DOMAIN_ORDER[0])),
                       -len(by_scen[s])),
    )

    # ---- build node index (domain, then scenario, then app) ----
    labels: list[str] = []
    node_color: list[str] = []
    node_x: list[float] = []
    node_y: list[float] = []
    idx: dict[str, int] = {}

    def add_node(key: str, label: str, color: str, x: float) -> int:
        idx[key] = len(labels)
        labels.append(label)
        node_color.append(color)
        node_x.append(x)
        node_y.append(0.0)  # y filled later
        return idx[key]

    for dom in DOMAIN_ORDER:
        add_node(f"D::{dom}", dom, rgba(DOMAIN_COLOR[dom], 0.95), 0.001)
    for scen in scen_order:
        dom = SCENARIO_DOMAIN.get(scen, DOMAIN_ORDER[0])
        add_node(f"S::{scen}", SCENARIO_EN.get(scen, scen),
                 rgba(DOMAIN_COLOR[dom], 0.75), 0.5)
    for scen in scen_order:
        dom = SCENARIO_DOMAIN.get(scen, DOMAIN_ORDER[0])
        for a in sorted(by_scen[scen], key=lambda x: -len(x["action_object_str"])):
            name = a["app_name"].strip()
            n_fn = len(a["action_object_str"])
            add_node(f"A::{a['id']}", f"{name} ({n_fn})",
                     rgba(DOMAIN_COLOR[dom], 0.55), 0.999)

    # ---- links ----
    src, tgt, val, link_color = [], [], [], []
    scen_fn_total: dict[str, int] = defaultdict(int)
    for scen in scen_order:
        dom = SCENARIO_DOMAIN.get(scen, DOMAIN_ORDER[0])
        for a in by_scen[scen]:
            n_fn = len(a["action_object_str"])
            scen_fn_total[scen] += n_fn
            src.append(idx[f"S::{scen}"]); tgt.append(idx[f"A::{a['id']}"])
            val.append(n_fn); link_color.append(rgba(DOMAIN_COLOR[dom], 0.32))
    for scen in scen_order:
        dom = SCENARIO_DOMAIN.get(scen, DOMAIN_ORDER[0])
        src.append(idx[f"D::{dom}"]); tgt.append(idx[f"S::{scen}"])
        val.append(scen_fn_total[scen]); link_color.append(rgba(DOMAIN_COLOR[dom], 0.40))

    total_fn = sum(len(a["action_object_str"]) for a in apps)
    print(f"scenarios: {len(scen_order)} | total functions (link units): {total_fn}")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=labels,
            color=node_color,
            x=node_x, y=node_y,
            pad=6, thickness=14,
            line=dict(color="rgba(0,0,0,0.25)", width=0.4),
        ),
        link=dict(source=src, target=tgt, value=val, color=link_color),
    ))
    fig.update_layout(
        title=dict(
            text="Knowledge base: Domain → Scenario → App "
                 f"(57 apps with action chains, link width = #functions)",
            x=0.5, font=dict(size=16),
        ),
        font=dict(family="Noto Sans CJK SC, DejaVu Sans", size=11, color="#222"),
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
