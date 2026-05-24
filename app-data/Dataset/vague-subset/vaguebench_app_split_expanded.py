"""Expanded VagueBench (Level1-INS, n=103) length comparison for the paper appendix.

Same protocol as vaguebench_app_split.py (which uses the original n=50 set), but
the VagueBench instructions are read from the expanded benchmark
  ../../Ins-bench/Vague-ins-expanded.json
using the `Level1-INS` field. Language (cn/en) is auto-detected from the text
(presence of CJK characters), since the expanded file has no `lang` field.
App count is parsed from `Invovled_App_Name`; 4 entries with an empty app field
are inferred from the instruction (EMPTY_INFER).

Two complexity-matched comparison groups, each reported with a cn/en split:
  Group A (atomic / single-app):
    VagueBench-exp single-app  vs  AndroidArena, AndroidWorld, MVISU-Bench
  Group B (compositional / multi-app):
    VagueBench-exp multi-app   vs  MobileWorld, AndroidDaily

Primary metric: tiktoken cl100k_base token count.

Outputs (parallel to the n=50 artifacts; originals are NOT overwritten):
  - app_split_stats_expanded.csv
  - length_boxplot_appsplit_expanded.png

Run:  python app-data/Dataset/vague-subset/vaguebench_app_split_expanded.py
"""
import json
import re
import csv
import statistics
from pathlib import Path

import tiktoken
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parent
EXPANDED = ROOT / '..' / '..' / 'Ins-bench' / 'Vague-ins-expanded.json'
enc = tiktoken.get_encoding('cl100k_base')

# Task_id -> inferred app count for the 4 entries with empty Invovled_App_Name
EMPTY_INFER = {
    11: 1,  # 查看红米手机的价格。                                  -> shopping (1)
    29: 2,  # Check LA weather ... and inform Kai Chen.            -> weather + messaging (2)
    30: 2,  # Look up info about Mobile-based Agent and make note. -> browser + notes (2)
    33: 1,  # Choose a 5G phone under $200 and add it to my cart.  -> shopping (1)
}

CN, EN = '#d62728', '#1f77b4'


def parse_apps(s):
    """Return list of app slots. '/' groups stay as one slot (alternatives)."""
    if not s:
        return []
    quoted = re.findall(r'"([^"]+)"', s)
    s2 = re.sub(r'"[^"]+"', ' ', s)
    if re.search(r'[、，,\t\n]', s2):
        parts = re.split(r'[、，,\t\n]+', s2)
    else:
        parts = re.split(r'\s+', s2)
    parts = quoted + [p.strip() for p in parts if p.strip()]
    return [p for p in parts if p]


def lang_of(s):
    return 'cn' if re.search(r'[一-鿿]', s or '') else 'en'


def tokens(text):
    return len(enc.encode(text))


def describe(values):
    vs = sorted(values)
    n = len(vs)
    if n == 0:
        return dict(n=0, mean=0, median=0, std=0, min=0, max=0, p25=0, p75=0)

    def q(p):
        idx = (n - 1) * p
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return round(vs[lo] + (vs[hi] - vs[lo]) * (idx - lo), 1)

    return dict(n=n, mean=round(statistics.mean(vs), 1), median=q(0.5),
                std=round(statistics.stdev(vs), 1) if n > 1 else 0.0,
                min=min(vs), max=max(vs), p25=q(0.25), p75=q(0.75))


_EXP = json.load(open(EXPANDED))


def app_count(entry):
    n = len(parse_apps(entry['Invovled_App_Name']))
    return EMPTY_INFER.get(entry['Task_id'], 0) if n == 0 else n


def vb_tokens(multi, lang=None):
    return [tokens(x['Level1-INS']) for x in _EXP
            if ((app_count(x) >= 2) == multi)
            and (lang is None or lang_of(x['Level1-INS']) == lang)]


def bench_tokens(fname, lang=None):
    d = json.load(open(ROOT / fname))
    return [tokens(x['instruction']) for x in d if lang is None or x.get('lang') == lang]


GROUP_A = [
    ('VagueBench-exp\nsingle', lambda lang: vb_tokens(False, lang)),
    ('Android\nArena',         lambda lang: bench_tokens('androidarena_vague.json', lang)),
    ('Android\nWorld',         lambda lang: bench_tokens('androidworld_vague.json', lang)),
    ('MVISU',                  lambda lang: bench_tokens('mvisu_vague.json', lang)),
]
GROUP_B = [
    ('VagueBench-exp\nmulti', lambda lang: vb_tokens(True, lang)),
    ('Mobile\nWorld',         lambda lang: bench_tokens('mobileworld_vague.json', lang)),
    ('Android\nDaily',        lambda lang: bench_tokens('androiddaily_vague.json', lang)),
]


def panel(ax, groups, title):
    positions, data, colors, ticks, ticklabels = [], [], [], [], []
    base = 1.0
    for label, fn in groups:
        center = []
        for lang, color in [('cn', CN), ('en', EN)]:
            vals = fn(lang)
            if vals:
                positions.append(base)
                data.append(vals)
                colors.append(color)
                center.append(base)
                base += 1.0
        ticks.append(sum(center) / len(center))
        ticklabels.append(label)
        base += 0.8
    bp = ax.boxplot(data, positions=positions, widths=0.8, patch_artist=True,
                    showmeans=True, meanline=True,
                    medianprops=dict(color='black', lw=1.1),
                    meanprops=dict(color='black', lw=1.0, ls='--'),
                    flierprops=dict(marker='o', ms=3, alpha=0.5))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax.set_xticks(ticks)
    ax.set_xticklabels(ticklabels, fontsize=8)
    ax.set_title(title, fontsize=10)
    ax.grid(True, axis='y', ls=':', alpha=0.5)


def main():
    rows = []
    spec = [
        ('A:atomic',   'VagueBench-exp single', lambda l: vb_tokens(False, l)),
        ('A:atomic',   'AndroidArena',          lambda l: bench_tokens('androidarena_vague.json', l)),
        ('A:atomic',   'AndroidWorld',          lambda l: bench_tokens('androidworld_vague.json', l)),
        ('A:atomic',   'MVISU-Bench',           lambda l: bench_tokens('mvisu_vague.json', l)),
        ('B:composit', 'VagueBench-exp multi',  lambda l: vb_tokens(True, l)),
        ('B:composit', 'MobileWorld',           lambda l: bench_tokens('mobileworld_vague.json', l)),
        ('B:composit', 'AndroidDaily',          lambda l: bench_tokens('androiddaily_vague.json', l)),
    ]
    for group, name, fn in spec:
        for lang in ['all', 'cn', 'en']:
            vals = fn(None if lang == 'all' else lang)
            if not vals:
                continue
            rows.append({'group': group, 'bench': name, 'lang': lang, **describe(vals)})

    with open(ROOT / 'app_split_stats_expanded.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    hdr = (f"{'group':11s} {'bench':22s} {'lang':4s} {'n':>3} {'mean':>6} "
           f"{'med':>5} {'std':>5} {'min':>4} {'max':>4} {'p25':>5} {'p75':>5}")
    print("EXPANDED set (Level1-INS, n=103) — tiktoken cl100k_base token count")
    print(hdr + "\n" + "-" * len(hdr))
    for r in rows:
        print(f"{r['group']:11s} {r['bench']:22s} {r['lang']:4s} {r['n']:>3} "
              f"{r['mean']:>6} {r['median']:>5} {r['std']:>5} {r['min']:>4} "
              f"{r['max']:>4} {r['p25']:>5} {r['p75']:>5}")

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    panel(axA, GROUP_A, 'Group A: atomic / single-app')
    panel(axB, GROUP_B, 'Group B: compositional / multi-app')
    axA.set_ylabel('Token count (tiktoken cl100k_base)')
    handles = [plt.Rectangle((0, 0), 1, 1, fc=CN, alpha=0.55),
               plt.Rectangle((0, 0), 1, 1, fc=EN, alpha=0.55)]
    axB.legend(handles, ['cn', 'en'], loc='upper right', fontsize=9)
    fig.suptitle('L1 Vague Instruction Length: VagueBench (expanded, n=103) vs other benchmarks (cn / en)',
                 fontsize=12)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(ROOT / 'length_boxplot_appsplit_expanded.png', dpi=160)
    plt.close()

    print('\nFiles written:')
    for f in ['app_split_stats_expanded.csv', 'length_boxplot_appsplit_expanded.png']:
        p = ROOT / f
        print(f'  {p}  ({p.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
