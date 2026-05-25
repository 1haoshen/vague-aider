#!/usr/bin/env python3
"""rewrite_token_stats.py

Summarise the token / latency cost of the L1 -> {L2, L3} instruction rewrite
that produced ``Vague-ins-rewritten50.json`` (model: qwen/qwen3-8b, via
instruction_rewrite_v2.py).

Each task carries a ``_rewrite_meta`` block of the form::

    {"usage": {"prompt_tokens": .., "completion_tokens": .., "total_tokens": ..},
     "duration_s": .., "kb_slice_chars": .., "model": "qwen/qwen3-8b", ...}

We aggregate input (prompt), output (completion) and total tokens plus
wall-clock duration, both overall and per task type, and emit:

  * a console summary,
  * ``rewrite_token_stats_overall.csv``  (one row of headline numbers),
  * ``rewrite_token_stats_by_type.csv``  (one row per task type),
  * ``rewrite_token_stats.json``         (machine-readable, used by the paper).

Run:  python3 rewrite_token_stats.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_SRC = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins-rewritten50.json")


def _summary(xs: list[float]) -> dict:
    xs = [float(x) for x in xs]
    return {
        "n": len(xs),
        "total": round(sum(xs), 2),
        "mean": round(st.mean(xs), 2),
        "median": round(st.median(xs), 2),
        "std": round(st.pstdev(xs), 2) if len(xs) > 1 else 0.0,
        "min": round(min(xs), 2),
        "max": round(max(xs), 2),
    }


def analyse(src: str, prefix: str) -> None:
    with open(src, "r", encoding="utf-8") as f:
        records = json.load(f)

    ok = [r for r in records if "Level2-INS_v2" in r]
    fail = [r for r in records if "Level2-INS_v2" not in r]

    prompt_t, completion_t, total_t, dur, kb_chars = [], [], [], [], []
    n_apps_per_task: list[int] = []   # #apps each rewrite drew on
    distinct_apps: set[str] = set()
    models: set[str] = set()
    by_type: dict[str, dict[str, list]] = {}

    for r in records:
        meta = r.get("_rewrite_meta", {})
        usage = meta.get("usage", {})
        p = int(usage.get("prompt_tokens", 0) or 0)
        c = int(usage.get("completion_tokens", 0) or 0)
        t = int(usage.get("total_tokens", 0) or 0)
        d = float(meta.get("duration_s", 0) or 0)
        prompt_t.append(p)
        completion_t.append(c)
        total_t.append(t)
        dur.append(d)
        if "kb_slice_chars" in meta:
            kb_chars.append(int(meta["kb_slice_chars"]))
        models.add(meta.get("model", "?"))

        # apps the rewrite referenced (fall back to injected KB apps)
        apps = meta.get("referenced_apps") or meta.get("kb_apps_injected") or []
        apps = [a.strip() for a in apps if a and a.strip()]
        n_apps_per_task.append(len(apps))
        distinct_apps.update(apps)

        ttype = (r.get("Task Type") or "(unlabelled)").strip() or "(unlabelled)"
        b = by_type.setdefault(ttype, {"in": [], "out": [], "tot": [], "dur": [], "apps": []})
        b["in"].append(p); b["out"].append(c); b["tot"].append(t)
        b["dur"].append(d); b["apps"].append(len(apps))

    n = len(records)
    stats = {
        "source_file": os.path.relpath(src, REPO_ROOT),
        "model": sorted(models),
        "n_tasks": n,
        "n_ok": len(ok),
        "n_failed": len(fail),
        "input_tokens": _summary(prompt_t),
        "output_tokens": _summary(completion_t),
        "total_tokens": _summary(total_t),
        "duration_s": _summary(dur),
        "kb_slice_chars": _summary(kb_chars) if kb_chars else {},
        "apps_per_task": _summary(n_apps_per_task),
        "distinct_apps": len(distinct_apps),
        "output_input_ratio": round(sum(completion_t) / sum(prompt_t), 4),
    }

    # ---- console ----
    print(f"source : {stats['source_file']}")
    print(f"model  : {', '.join(stats['model'])}")
    print(f"tasks  : {n} ({len(ok)} ok / {len(fail)} failed)\n")
    hdr = f"{'metric':<18}{'total':>12}{'mean':>10}{'median':>9}{'std':>9}{'min':>8}{'max':>8}"
    print(hdr)
    print("-" * len(hdr))
    rows_spec = [("input (prompt)", "input_tokens"),
                 ("output (compl.)", "output_tokens"),
                 ("total tokens", "total_tokens"),
                 ("duration (s)", "duration_s"),
                 ("apps / task", "apps_per_task")]
    if kb_chars:
        rows_spec.append(("kb_slice_chars", "kb_slice_chars"))
    for label, key in rows_spec:
        s = stats[key]
        print(f"{label:<18}{s['total']:>12.0f}{s['mean']:>10.1f}"
              f"{s['median']:>9.1f}{s['std']:>9.1f}{s['min']:>8.0f}{s['max']:>8.0f}")
    print(f"\noutput/input token ratio : {stats['output_input_ratio']:.3f}")
    print(f"distinct apps rewritten  : {stats['distinct_apps']}")
    print(f"cost per task (avg)      : {stats['total_tokens']['mean']:.0f} tok"
          f" / {stats['duration_s']['mean']:.2f} s / {stats['apps_per_task']['mean']:.1f} apps")

    # ---- per type ----
    print("\nper task type (sorted by n):")
    type_rows = []
    for ttype, b in sorted(by_type.items(), key=lambda kv: -len(kv[1]["in"])):
        row = {
            "task_type": ttype, "n": len(b["in"]),
            "in_total": sum(b["in"]), "in_mean": round(st.mean(b["in"]), 1),
            "out_total": sum(b["out"]), "out_mean": round(st.mean(b["out"]), 1),
            "tot_total": sum(b["tot"]), "tot_mean": round(st.mean(b["tot"]), 1),
            "dur_total": round(sum(b["dur"]), 1), "dur_mean": round(st.mean(b["dur"]), 2),
            "apps_mean": round(st.mean(b["apps"]), 2),
        }
        type_rows.append(row)
        print(f"  {ttype:<14} n={row['n']:<3} in={row['in_total']:<6} "
              f"out={row['out_total']:<5} tot={row['tot_total']:<6} "
              f"dur={row['dur_total']}s apps/task={row['apps_mean']}")

    # ---- write artefacts ----
    with open(os.path.join(HERE, f"{prefix}.json"), "w", encoding="utf-8") as f:
        json.dump({"overall": stats, "by_type": type_rows}, f, ensure_ascii=False, indent=2)

    with open(os.path.join(HERE, f"{prefix}_overall.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "total", "mean", "median", "std", "min", "max"])
        for label, key in rows_spec:
            s = stats[key]
            w.writerow([label, s["total"], s["mean"], s["median"], s["std"], s["min"], s["max"]])

    with open(os.path.join(HERE, f"{prefix}_by_type.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(type_rows[0].keys()))
        w.writeheader(); w.writerows(type_rows)

    print(f"\nwrote: {prefix}.json, {prefix}_overall.csv, {prefix}_by_type.csv")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="src", default=DEFAULT_SRC,
                    help="path to a *-rewritten*.json file with _rewrite_meta")
    ap.add_argument("--prefix", default=None,
                    help="output filename prefix (default derived from input stem)")
    args = ap.parse_args()
    prefix = args.prefix or (
        "rewrite_token_stats"
        if os.path.basename(args.src) == os.path.basename(DEFAULT_SRC)
        else "rewrite_token_stats_" +
             os.path.splitext(os.path.basename(args.src))[0].replace("Vague-ins-", "")
    )
    analyse(args.src, prefix)


if __name__ == "__main__":
    main()
