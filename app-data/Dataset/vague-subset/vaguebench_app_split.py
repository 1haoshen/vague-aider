"""VagueBench-L1 single-app vs multi-app length split + cross-bench comparison.

Splits VagueBench-L1 by declared app count:
  - single-app: exactly 1 declared app
  - multi-app : >= 2 declared apps
The declared_app field uses mixed separators (、 , space, /, quotes, newlines);
parse_apps() normalizes them. "a/b" means alternative apps for one role -> 1 slot.
4 entries have an empty declared_app and are inferred from the instruction
(see EMPTY_INFER).

The multi-app subset is then compared against MobileWorld and AndroidDaily,
which are the two benches with the longest natural-language instructions.

Outputs:
  - app_split_stats.csv          single/multi token stats + comparison benches
  - length_boxplot_appsplit.png  boxplot: VagueBench single/multi vs MW/AD

Run:  python app-data/Dataset/vague-subset/vaguebench_app_split.py
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
enc = tiktoken.get_encoding('cl100k_base')

# entries whose declared_app is empty -> app count inferred from the instruction
EMPTY_INFER = {
    13: 1,  # 查看红米手机的价格。                                  -> shopping (1)
    33: 2,  # Check LA weather ... and inform Kai Chen.            -> weather + messaging (2)
    34: 2,  # Look up info about Mobile-based Agent and make note. -> browser + notes (2)
    38: 1,  # Choose a 5G phone under $200 and add it to my cart.  -> shopping (1)
}


def parse_apps(s):
    """Return list of app slots. '/' groups stay as one slot (alternatives)."""
    if not s:
        return []
    quoted = re.findall(r'"([^"]+)"', s)
    s2 = re.sub(r'"[^"]+"', ' ', s)
    # strong separators only when present, so multiword names ("Netease Cloud
    # Music") survive; otherwise fall back to whitespace split.
    if re.search(r'[、，,\t\n]', s2):
        parts = re.split(r'[、，,\t\n]+', s2)
    else:
        parts = re.split(r'\s+', s2)
    parts = quoted + [p.strip() for p in parts if p.strip()]
    return [p for p in parts if p]


def app_count(entry):
    n = len(parse_apps(entry['declared_app']))
    if n == 0:
        n = EMPTY_INFER.get(entry['source_id'], 0)
    return n


def tokens(text):
    return len(enc.encode(text))


def describe(values):
    vs = sorted(values)
    n = len(vs)

    def q(p):
        idx = (n - 1) * p
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return round(vs[lo] + (vs[hi] - vs[lo]) * (idx - lo), 1)

    return dict(n=n, mean=round(statistics.mean(vs), 1), median=q(0.5),
                std=round(statistics.stdev(vs), 1) if n > 1 else 0.0,
                min=min(vs), max=max(vs), p25=q(0.25), p75=q(0.75))


def bench_tokens(fname):
    return [tokens(x['instruction']) for x in json.load(open(ROOT / fname))]


def main():
    vb = json.load(open(ROOT / 'vaguebench_L1.json'))
    single = [tokens(x['instruction']) for x in vb if app_count(x) == 1]
    multi = [tokens(x['instruction']) for x in vb if app_count(x) >= 2]
    mw = bench_tokens('mobileworld_vague.json')
    ad = bench_tokens('androiddaily_vague.json')

    groups = [
        ('VagueBench-L1 single-app', single),
        ('VagueBench-L1 multi-app', multi),
        ('MobileWorld (all)', mw),
        ('AndroidDaily (all)', ad),
    ]

    # CSV
    rows = [{'group': name, **describe(vals)} for name, vals in groups]
    with open(ROOT / 'app_split_stats.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # console table
    hdr = f"{'group':26s} {'n':>3} {'mean':>6} {'med':>5} {'std':>5} {'min':>4} {'max':>4} {'p25':>5} {'p75':>5}"
    print("tiktoken cl100k_base token count\n" + hdr + "\n" + "-" * len(hdr))
    for r in rows:
        print(f"{r['group']:26s} {r['n']:>3} {r['mean']:>6} {r['median']:>5} "
              f"{r['std']:>5} {r['min']:>4} {r['max']:>4} {r['p25']:>5} {r['p75']:>5}")

    # boxplot
    labels = [f"{name}\n(n={len(vals)})" for name, vals in groups]
    data = [vals for _, vals in groups]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bp = ax.boxplot(data, labels=labels, showmeans=True, meanline=True,
                    patch_artist=True, medianprops=dict(color='black', lw=1.2),
                    meanprops=dict(color='red', lw=1.2, ls='--'))
    for patch, c in zip(bp['boxes'], ['#ff7f0e', '#e377c2', '#8c564b', '#d62728']):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax.set_ylabel('Token count (tiktoken cl100k_base)')
    ax.set_title('VagueBench-L1 single vs multi-app, compared with MobileWorld & AndroidDaily')
    ax.grid(True, axis='y', ls=':', alpha=0.5)
    plt.xticks(fontsize=8)
    plt.tight_layout()
    plt.savefig(ROOT / 'length_boxplot_appsplit.png', dpi=160)
    plt.close()

    print('\nFiles written:')
    for f in ['app_split_stats.csv', 'length_boxplot_appsplit.png']:
        p = ROOT / f
        print(f'  {p}  ({p.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
