"""analyze_phoneagent_logs.py

Aggregate phone_agent run logs (steps.json) into the metrics used in the paper:
per instruction level (L1/L2/L3) -> completion rate, avg steps, avg duration,
and token consumption (total + average).

IMPORTANT — what "completion" means here:
    A local ADB run has NO ground-truth task checker (unlike MobileWorld's
    container eval). So `completed` = the agent *self-reported* finish
    (steps.json final entry has finish_flag == "success"), NOT verified
    correctness. The per-run CSV leaves a `manual_correct` column blank for
    you to hand-label; pass --use-manual to recompute success from it.

Inputs (either works):
    --exp-dir <log-dir>/<exp>     reads <exp>/manifest.jsonl (preferred) and/or
                                   globs <exp>/**/steps.json
Outputs (written into --exp-dir):
    runs.csv            one row per run, with per-run metrics
    summary_by_level.csv   paper-style per-level aggregate
    summary_by_level_repeat.csv   per (level,repeat) breakdown
and a summary table to stdout.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics
from collections import defaultdict

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))


def parse_steps_json(path: str) -> dict:
    """Extract metrics from one steps.json. Returns dict with:
    finished_success(bool), finish_flag, n_steps, duration_s, prompt_tokens,
    completion_tokens, total_tokens, instruction."""
    out = {
        "finish_flag": None, "finished_success": False, "n_steps": 0,
        "duration_s": None, "prompt_tokens": 0, "completion_tokens": 0,
        "total_tokens": 0, "instruction": None, "parse_error": None,
    }
    try:
        with open(path, "r", encoding="utf-8") as f:
            steps = json.load(f)
    except Exception as e:
        out["parse_error"] = str(e)
        return out

    action_steps = 0
    for s in steps:
        op = s.get("operation")
        if op == "init":
            out["instruction"] = s.get("instruction")
        elif op == "action":
            action_steps += 1
            out["prompt_tokens"] += int(s.get("prompt_tokens", 0) or 0)
            out["completion_tokens"] += int(s.get("completion_tokens", 0) or 0)
            out["total_tokens"] += int(s.get("total_tokens", 0) or 0)
        elif op == "finish":
            out["finish_flag"] = s.get("finish_flag")
            out["finished_success"] = s.get("finish_flag") == "success"
            if s.get("task_duration") is not None:
                out["duration_s"] = float(s["task_duration"])
    out["n_steps"] = action_steps
    return out


def collect_runs(exp_dir: str) -> list[dict]:
    """Build per-run records by merging manifest.jsonl (if present) with parsed
    steps.json metrics. Falls back to globbing steps.json from run_name dirs."""
    manifest_path = os.path.join(exp_dir, "manifest.jsonl")
    runs: list[dict] = []

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = json.loads(line)
                steps_json = m.get("steps_json")
                abs_steps = os.path.join(REPO_ROOT, steps_json) if steps_json else None
                if abs_steps and os.path.exists(abs_steps):
                    metrics = parse_steps_json(abs_steps)
                else:
                    # try to find it under the run_name dir
                    run_root = os.path.join(os.path.dirname(exp_dir),
                                            *m.get("run_name", "").split("/"))
                    hits = glob.glob(os.path.join(run_root, "*", "steps.json"))
                    metrics = parse_steps_json(hits[0]) if hits else {
                        "finish_flag": "no_log", "finished_success": False,
                        "n_steps": 0, "duration_s": None,
                        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                        "instruction": m.get("instruction"), "parse_error": "no steps.json",
                    }
                runs.append({**m, **metrics,
                             "duration_s": metrics.get("duration_s") or m.get("wallclock_s")})
        return runs

    # No manifest: glob steps.json and recover (task,level,rep) from path
    # .../<exp>/t<id>_<LEVEL>_r<rep>/<ts>/steps.json
    for sj in glob.glob(os.path.join(exp_dir, "*", "*", "steps.json")):
        run_name = os.path.basename(os.path.dirname(os.path.dirname(sj)))
        tid, level, rep = None, None, None
        try:
            tpart, level, rpart = run_name.split("_")
            tid = int(tpart.lstrip("t"))
            rep = int(rpart.lstrip("r"))
        except Exception:
            pass
        metrics = parse_steps_json(sj)
        runs.append({"task_id": tid, "level": level, "repeat": rep,
                     "run_name": run_name, "steps_json": sj, **metrics})
    return runs


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 2) if xs else 0.0


def summarize(runs: list[dict], success_key: str) -> tuple[list[dict], list[dict]]:
    by_level = defaultdict(list)
    by_level_rep = defaultdict(list)
    for r in runs:
        by_level[r.get("level")].append(r)
        by_level_rep[(r.get("level"), r.get("repeat"))].append(r)

    def block(group: list[dict]) -> dict:
        n = len(group)
        n_success = sum(1 for r in group if r.get(success_key))
        return {
            "n_total": n,
            "n_completed": n_success,
            "completion_rate": round(n_success / n, 4) if n else 0.0,
            "avg_steps": _avg([r.get("n_steps") for r in group]),
            "avg_duration_s": _avg([r.get("duration_s") for r in group]),
            "avg_total_tokens": _avg([r.get("total_tokens") for r in group]),
            "sum_total_tokens": sum(int(r.get("total_tokens", 0) or 0) for r in group),
            "sum_prompt_tokens": sum(int(r.get("prompt_tokens", 0) or 0) for r in group),
            "sum_completion_tokens": sum(int(r.get("completion_tokens", 0) or 0) for r in group),
        }

    level_rows = []
    for lv in sorted(by_level, key=lambda x: (x is None, x)):
        level_rows.append({"level": lv, **block(by_level[lv])})

    lr_rows = []
    for (lv, rep) in sorted(by_level_rep, key=lambda x: (str(x[0]), str(x[1]))):
        lr_rows.append({"level": lv, "repeat": rep, **block(by_level_rep[(lv, rep)])})

    return level_rows, lr_rows


def write_csv(path: str, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exp-dir", required=True,
                    help="<log-dir>/<exp> directory holding manifest.jsonl / steps.json")
    ap.add_argument("--use-manual", action="store_true",
                    help="compute completion from the manual_correct column of runs.csv")
    args = ap.parse_args()

    runs_csv = os.path.join(args.exp_dir, "runs.csv")

    if args.use_manual:
        if not os.path.exists(runs_csv):
            ap.error("runs.csv not found; run once without --use-manual first, then label it")
        with open(runs_csv, "r", encoding="utf-8") as f:
            runs = list(csv.DictReader(f))
        for r in runs:  # cast numerics back
            for k in ("n_steps", "total_tokens", "prompt_tokens", "completion_tokens"):
                r[k] = int(float(r.get(k) or 0))
            r["duration_s"] = float(r["duration_s"]) if r.get("duration_s") not in ("", None) else None
            r["repeat"] = int(float(r["repeat"])) if r.get("repeat") not in ("", None) else None
            r["manual_correct_bool"] = str(r.get("manual_correct", "")).strip().lower() in ("1", "true", "yes", "y")
        success_key = "manual_correct_bool"
    else:
        runs = collect_runs(args.exp_dir)
        success_key = "finished_success"

    if not runs:
        print(f"no runs found under {args.exp_dir}")
        return

    # Per-run CSV (only write fresh, don't clobber manual labels if --use-manual)
    run_fields = ["task_id", "level", "repeat", "lang", "task_type", "apps",
                  "finish_flag", "finished_success", "n_steps", "duration_s",
                  "prompt_tokens", "completion_tokens", "total_tokens",
                  "manual_correct", "instruction", "result", "steps_json"]
    if not args.use_manual:
        for r in runs:
            r.setdefault("manual_correct", "")  # blank for hand-labeling
        write_csv(runs_csv, runs, run_fields)

    level_rows, lr_rows = summarize(runs, success_key)

    level_fields = ["level", "n_total", "n_completed", "completion_rate",
                    "avg_steps", "avg_duration_s", "avg_total_tokens",
                    "sum_total_tokens", "sum_prompt_tokens", "sum_completion_tokens"]
    write_csv(os.path.join(args.exp_dir, "summary_by_level.csv"), level_rows, level_fields)
    write_csv(os.path.join(args.exp_dir, "summary_by_level_repeat.csv"),
              lr_rows, ["level", "repeat"] + level_fields[1:])

    label = "MANUAL correctness" if args.use_manual else "agent-reported completion"
    print(f"\nMetric basis: {label}")
    print("=" * 92)
    print(f"{'level':>6} {'n':>5} {'done':>5} {'rate%':>7} {'avg_steps':>10} "
          f"{'avg_dur_s':>10} {'avg_tok':>9} {'sum_tok':>10}")
    print("-" * 92)
    for r in level_rows:
        print(f"{str(r['level']):>6} {r['n_total']:>5} {r['n_completed']:>5} "
              f"{r['completion_rate'] * 100:>6.1f}% {r['avg_steps']:>10} "
              f"{r['avg_duration_s']:>10} {r['avg_total_tokens']:>9} {r['sum_total_tokens']:>10}")
    print("=" * 92)
    print(f"CSVs written to {args.exp_dir}/ "
          f"(runs.csv, summary_by_level.csv, summary_by_level_repeat.csv)")
    if not args.use_manual:
        print("Tip: hand-label the 'manual_correct' column in runs.csv (1/0), "
              "then re-run with --use-manual for true success rate.")


if __name__ == "__main__":
    main()
