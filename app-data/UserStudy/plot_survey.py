"""User-study figures for the VagueAider paper.

A 28-respondent questionnaire on how people *naturally* phrase requests to a
phone AI assistant, and where current assistants fall short. The survey probes
the central VagueAider hypothesis: users speak in *user-friendly vague intents*,
not *agent-friendly fully-explicit instructions*.

Two figures:
  fig_survey_problems.png   Q3 pain points + Q4 desired capabilities (two panels)
  fig_survey_spectrum.png   Q5/Q6/Q7 as a shared user-friendly <-> agent-friendly
                            stance axis (diverging 100%-stacked bars)

Primary source: survey_results.csv (n = 28).

Run:  python app-data/UserStudy/plot_survey.py
"""
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.unicode_minus": False,
    "svg.fonttype": "none",
})

ROOT = Path(__file__).resolve().parent
N = 28

# Semantic palette, shared across both figures.
EMPH   = "#1d3557"   # thesis-relevant emphasis (dark navy)
MUTE   = "#a8c0d0"   # background bars (light slate)
GREEN  = "#2a9d8f"   # stance: prefers user-friendly / vague / expects intelligence
GRAY   = "#b7bcc4"   # stance: conditional / neutral
RED    = "#e76f51"   # stance: prefers agent-friendly / fully-explicit control


def wrap(s, w=26):
    return "\n".join(textwrap.wrap(s, w))


# ----------------------------------------------------------------------------
# Figure 1 - Q3 pain points & Q4 desired capabilities (multi-select)
# ----------------------------------------------------------------------------
# (label, pct, count, emphasised?)  emphasised = the two thesis-relevant bars
Q3 = [
    ("Cannot complete cross-app tasks",                71.43, 20, True),
    ("Cannot understand abstract ideas;\nneeds every rigid step", 64.29, 18, True),
    ("Privacy / credential security\nnot guaranteed",  42.86, 12, False),
    ("Drains battery / heavy resource use",            32.14,  9, False),
    ("Slow execution, sluggish response",              28.57,  8, False),
    ("Overall satisfied, no real issue",               14.29,  4, False),
]
Q4 = [
    ("Smooth cross-app coordination",                  82.14, 23, True),
    ('Strong abstract-intent understanding\n("I\'m hungry" → right app)', 64.29, 18, True),
    ("Strict privacy & credential security",           64.29, 18, False),
    ("Fast response & low resource use",               42.86, 12, False),
    ("Other",                                          10.71,  3, False),
]


def hbar_panel(ax, rows, title):
    rows = sorted(rows, key=lambda r: r[1])  # ascending -> largest on top
    y = range(len(rows))
    colors = [EMPH if r[3] else MUTE for r in rows]
    bars = ax.barh(list(y), [r[1] for r in rows], color=colors,
                   edgecolor="white", height=0.68, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels([r[0] for r in rows], fontsize=11)
    for r, b in zip(rows, bars):
        ax.text(b.get_width() + 1.2, b.get_y() + b.get_height() / 2,
                f"{r[1]:.0f}%", va="center", ha="left",
                fontsize=10.5, color=EMPH if r[3] else "#5a6b78",
                fontweight="bold" if r[3] else "normal")
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of respondents (multi-select)", fontsize=10.5)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=8)
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(True, axis="x", ls=":", alpha=0.45, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def fig_problems():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    hbar_panel(a1, Q3, "Q3  Pain points of today's assistants")
    hbar_panel(a2, Q4, "Q4  Most-wanted future capabilities")
    handles = [Patch(fc=EMPH, label="Capability gap VagueAider targets"),
               Patch(fc=MUTE, label="Other factor")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=11, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=[0, 0.05, 1, 0.99])
    out = ROOT / "fig_survey_problems.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


# ----------------------------------------------------------------------------
# Figure 2 - Q5/Q6/Q7 on a shared user-friendly <-> agent-friendly stance axis
# ----------------------------------------------------------------------------
# Each question is reordered to (green, gray, red) where
#   green = leans user-friendly / vague / expects the agent to bridge the gap
#   gray  = conditional / neutral
#   red   = leans agent-friendly / wants to spell out every step
# Stored as (row_label, [(seg_label, pct), ...]) in green/gray/red order.
SPECTRUM = [
    ("Q5", [
        ("Intent description", 32.14),
        ("intermediate", 50.00),
        ("Path navigation and\ntrajectory knowledge", 17.86),
    ]),
    ("Q6", [
        ("No — too tedious", 50.00),
        ("Only when complex\n/ error-prone", 39.29),
        ("Yes — give all\ndetails", 10.71),
    ]),
    ("Q7", [
        ("Not smart enough", 50.00),
        ("Acceptable\n(tech limit)", 39.29),
        ("Good — I like\nfull control", 10.71),
    ]),
]
SEG_COLORS = [GREEN, GRAY, RED]


def fig_spectrum():
    fig, ax = plt.subplots(figsize=(14, 6))
    bar_h = 0.56
    ys = list(range(len(SPECTRUM)))[::-1]  # Q5 on top
    for y, (_, segs) in zip(ys, SPECTRUM):
        left = 0.0
        for (seg_label, pct), color in zip(segs, SEG_COLORS):
            ax.barh(y, pct, left=left, height=bar_h, color=color,
                    edgecolor="white", lw=1.4, zorder=3)
            txt_color = "white" if color != GRAY else "#2b2f36"
            ax.text(left + pct / 2, y + 0.11, f"{pct:.0f}%", ha="center",
                    va="center", fontsize=14, fontweight="bold",
                    color=txt_color, zorder=4)
            if pct >= 14:  # label inside wide-enough segments
                ax.text(left + pct / 2, y - 0.13, seg_label, ha="center",
                        va="center", fontsize=9.5, color=txt_color, zorder=4)
            left += pct

    ax.set_yticks(ys)
    ax.set_yticklabels([s[0] for s in SPECTRUM], fontsize=15, fontweight="bold")
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of respondents", fontsize=11)
    ax.tick_params(axis="x", labelsize=11)
    ax.set_ylim(-0.6, len(SPECTRUM) - 0.35)

    # boundary guideline = share who do NOT default to fully-explicit (green+gray)
    for y, (_, segs) in zip(ys, SPECTRUM):
        b = segs[0][1] + segs[1][1]
        ax.plot([b, b], [y - bar_h / 2 - 0.03, y + bar_h / 2 + 0.03],
                color="#1b2a36", lw=1.6, ls=(0, (4, 2)), zorder=6)
        ax.text(b - 0.8, y + bar_h / 2 + 0.06, f"{b:.0f}%", ha="right",
                va="bottom", fontsize=10.5, color="#1b2a36", fontweight="bold",
                zorder=6)

    handles = [
        Patch(fc=GREEN, label="Most user-friendly answer  —  state the vague intent, expect the agent to bridge the gap"),
        Patch(fc=GRAY,  label="Intermediate  —  some detail given, but the operations are still left to the agent"),
        Patch(fc=RED,   label="Most agent-friendly answer  —  willing to spell out every app & click"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01),
               ncol=1, frameon=False, fontsize=11, handlelength=1.3)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(True, axis="x", ls=":", alpha=0.4, zorder=0)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.96, bottom=0.28)
    out = ROOT / "fig_survey_spectrum.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def main():
    for f in (fig_problems(), fig_spectrum()):
        print(f"wrote {f}  ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
