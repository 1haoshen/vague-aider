"""L1 vague instruction length comparison across 6 benches.

Primary metric: tiktoken cl100k_base token count.
Secondary metrics: character count, word count (whitespace-split).
Outputs:
  - length_stats.csv       per-bench mean/median/std/min/max/p25/p75/n
  - length_stats_lang.csv  same stats split by lang (cn/en)
  - length_boxplot.png     boxplot of token count per bench
  - length_boxplot_lang.png boxplot with cn/en separated

Run:  python app-data/Dataset/vague-subset/length_compare.py
"""
import json
import os
import statistics
import csv
from pathlib import Path

import tiktoken
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parent

FILES = [
    ('VagueBench-L1',  'vaguebench_L1.json'),
    ('AndroidArena',   'androidarena_vague.json'),
    ('AndroidWorld',   'androidworld_vague.json'),
    ('MVISU-Bench',    'mvisu_vague.json'),
    ('AndroidDaily',   'androiddaily_vague.json'),
    ('MobileWorld',    'mobileworld_vague.json'),
]

enc = tiktoken.get_encoding('cl100k_base')


def load(fname):
    return json.load(open(ROOT / fname))


def metrics(text):
    return {
        'tokens': len(enc.encode(text)),
        'chars': len(text),
        'words': len(text.split()),
    }


def describe(values):
    if not values:
        return dict(n=0, mean=0, median=0, std=0, min=0, max=0, p25=0, p75=0)
    vs = sorted(values)
    n = len(vs)

    def quantile(q):
        idx = (n - 1) * q
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return vs[lo] + (vs[hi] - vs[lo]) * (idx - lo)

    return dict(
        n=n,
        mean=round(statistics.mean(vs), 2),
        median=quantile(0.5),
        std=round(statistics.stdev(vs) if n > 1 else 0, 2),
        min=min(vs),
        max=max(vs),
        p25=quantile(0.25),
        p75=quantile(0.75),
    )


def main():
    per_bench_tokens = {}
    rows = []
    rows_lang = []

    for label, fname in FILES:
        items = load(fname)
        token_lens = [metrics(x['instruction'])['tokens'] for x in items]
        char_lens = [metrics(x['instruction'])['chars'] for x in items]
        word_lens = [metrics(x['instruction'])['words'] for x in items]
        per_bench_tokens[label] = token_lens

        # overall stats
        t = describe(token_lens)
        c = describe(char_lens)
        w = describe(word_lens)
        rows.append({
            'bench': label, 'lang': 'all', **{f'tok_{k}': v for k, v in t.items()},
            **{f'char_{k}': v for k, v in c.items()},
            **{f'word_{k}': v for k, v in w.items()},
        })

        # per-language stats
        for lang in ['cn', 'en']:
            sub = [x for x in items if x.get('lang') == lang]
            if not sub:
                continue
            tlens = [metrics(x['instruction'])['tokens'] for x in sub]
            clens = [metrics(x['instruction'])['chars'] for x in sub]
            wlens = [metrics(x['instruction'])['words'] for x in sub]
            rows_lang.append({
                'bench': label, 'lang': lang,
                **{f'tok_{k}': v for k, v in describe(tlens).items()},
                **{f'char_{k}': v for k, v in describe(clens).items()},
                **{f'word_{k}': v for k, v in describe(wlens).items()},
            })

    # write CSVs
    def dump(path, rows):
        if not rows: return
        cols = list(rows[0].keys())
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    dump(ROOT / 'length_stats.csv', rows)
    dump(ROOT / 'length_stats_lang.csv', rows_lang)

    # boxplot (tokens, all)
    labels = [l for l, _ in FILES]
    data = [per_bench_tokens[l] for l in labels]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bp = ax.boxplot(data, labels=labels, showmeans=True, meanline=True,
                    patch_artist=True, medianprops=dict(color='black', lw=1.2),
                    meanprops=dict(color='red', lw=1.2, ls='--'))
    colors = ['#ff7f0e', '#1f77b4', '#2ca02c', '#9467bd', '#d62728', '#8c564b']
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax.set_ylabel('Token count (tiktoken cl100k_base)')
    ax.set_title('L1 Vague Instruction Length per Benchmark')
    ax.grid(True, axis='y', ls=':', alpha=0.5)
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(ROOT / 'length_boxplot.png', dpi=160)
    plt.close()

    # boxplot split by lang
    fig, ax = plt.subplots(figsize=(12, 5.5))
    positions = []
    bp_data = []
    bp_labels = []
    bp_colors = []
    base = 0
    for label, _ in FILES:
        items = load(_)
        for lang, color in [('cn', '#d62728'), ('en', '#1f77b4')]:
            sub = [metrics(x['instruction'])['tokens']
                   for x in items if x.get('lang') == lang]
            if sub:
                base += 1
                positions.append(base)
                bp_data.append(sub)
                bp_labels.append(f'{label}\n({lang}, n={len(sub)})')
                bp_colors.append(color)
        base += 0.5
    bp2 = ax.boxplot(bp_data, positions=positions, widths=0.7,
                     patch_artist=True, showmeans=True, meanline=True,
                     medianprops=dict(color='black', lw=1.0),
                     meanprops=dict(color='black', lw=1.0, ls='--'))
    for patch, c in zip(bp2['boxes'], bp_colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax.set_xticks(positions)
    ax.set_xticklabels(bp_labels, fontsize=8, rotation=20)
    ax.set_ylabel('Token count (tiktoken cl100k_base)')
    ax.set_title('L1 Vague Instruction Length per Benchmark (cn / en)')
    ax.grid(True, axis='y', ls=':', alpha=0.5)
    plt.tight_layout()
    plt.savefig(ROOT / 'length_boxplot_lang.png', dpi=160)
    plt.close()

    # print summary table
    print(f"{'bench':14s}  {'n':>3s}  {'mean':>6s}  {'med':>4s}  {'std':>5s}  {'min':>4s}  {'max':>4s}  {'p25':>4s}  {'p75':>4s}")
    print('-' * 65)
    for r in rows:
        print(f"{r['bench']:14s}  {r['tok_n']:3d}  {r['tok_mean']:6.2f}  "
              f"{r['tok_median']:4.1f}  {r['tok_std']:5.2f}  {r['tok_min']:4d}  "
              f"{r['tok_max']:4d}  {r['tok_p25']:4.1f}  {r['tok_p75']:4.1f}")
    print('\nFiles written:')
    for f in ['length_stats.csv', 'length_stats_lang.csv',
              'length_boxplot.png', 'length_boxplot_lang.png']:
        p = ROOT / f
        print(f'  {p}  ({p.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
