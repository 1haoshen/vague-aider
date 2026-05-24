"""expand_vague_bench.py

Expand Vague-ins.json with new tasks sourced from the 5 vague-subset datasets
(AndroidArena / AndroidDaily / AndroidWorld / MobileWorld / MVISU).

Selection rule (per user spec):
  Keep an instruction ONLY IF every app in its `mapped_kb_apps` exists in
  AppUi-final.json AND has a non-empty `action_object_str` (so L3 paths are
  groundable). Instructions with empty mapped_kb_apps are skipped here (no
  app inference) to keep the set clean and runnable.

For each kept instruction we build a record in the *original* Vague-ins.json
schema (7 core fields), filling Level2/Level3 with instruction_rewrite_v2:

  {Task_id, "Task Type", Invovled_App_Name, Original-INS,
   Level1-INS, Level2-INS, Level3-INS}

Plus traceability fields (lang, _source, _source_id) so the local phone-agent
runner can filter by language and map results back to the origin dataset.

Output: Vague-ins-expanded-local.json (58-ish tasks, numbered from --start-id).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Reuse the token-efficient rewriter built earlier.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instruction_rewrite_v2 as rw  # noqa: E402

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
SUBSET_DIR = os.path.join(REPO_ROOT, "app-data", "Dataset", "vague-subset")
KB_FINAL = os.path.join(REPO_ROOT, "app-data", "knowledge-base", "AppUi-final.json")
DEFAULT_OUT = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins-expanded-local.json")

DATASETS = [
    "androidarena_vague.json",
    "androiddaily_vague.json",
    "androidworld_vague.json",
    "mobileworld_vague.json",
    "mvisu_vague.json",
]


def load_covered_apps() -> dict[str, str]:
    """Return {app_name: scenario} for apps in AppUi-final that HAVE a
    non-empty action_object_str (the only apps allowed in the expansion)."""
    with open(KB_FINAL, "r", encoding="utf-8") as f:
        kb = json.load(f)
    return {
        a["app_name"].strip(): a.get("scenario", "")
        for a in kb
        if a.get("action_object_str")
    }


def load_subset_items() -> list[dict]:
    items: list[dict] = []
    for fn in DATASETS:
        path = os.path.join(SUBSET_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for it in (data if isinstance(data, list) else list(data.values())):
            items.append(it)
    return items


def task_type_for(item: dict, primary_app: str, covered: dict[str, str]) -> str:
    """Resolve a Chinese 'Task Type' label.
    Priority: dataset scenario -> dataset category -> KB scenario of the app."""
    return (
        (item.get("scenario") or "").strip()
        or (item.get("category") or "").strip()
        or covered.get(primary_app, "").strip()
        or "其他"
    )


def select_eligible(items: list[dict], covered: dict[str, str]) -> list[dict]:
    """Keep items whose mapped_kb_apps are all covered (non-empty list)."""
    eligible = []
    for it in items:
        apps = [a.strip() for a in (it.get("mapped_kb_apps") or []) if a.strip()]
        if not apps:
            continue
        if all(a in covered for a in apps):
            eligible.append(it)
    return eligible


def _rewrite_with_retry(l1: str, hint: str, kb: dict, api_key: str,
                        attempts: int = 4, lang: str | None = None) -> dict:
    """rewrite_one + network-level retry with backoff (the LLM endpoint can
    flake behind a local proxy). Returns the rewrite_one dict, or an error
    dict if every attempt raised."""
    last = None
    for a in range(attempts):
        try:
            return rw.rewrite_one(l1, hint, kb, api_key, lang=lang)
        except Exception as e:  # network / proxy errors propagate from requests
            last = e
            wait = 2 * (a + 1)
            print(f"   ! attempt {a + 1}/{attempts} network error: {e}; retry in {wait}s")
            time.sleep(wait)
    return {"ok": False, "error": f"network: {last}",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


def build_records(
    eligible: list[dict],
    covered: dict[str, str],
    kb: dict,
    api_key: str,
    start_id: int,
    sleep: float,
    out_path: str,
    resume: bool,
    prepend: list[dict] | None = None,
) -> list[dict]:
    # Resume: keep already-generated records (those that have L3) and skip them.
    existing: dict[int, dict] = {}
    if resume and os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            for r in json.load(f):
                existing[r["Task_id"]] = r
        done = sum(1 for r in existing.values() if r.get("Level3-INS"))
        print(f"resume: {len(existing)} records on disk, {done} already have L3")

    # Append mode: keep these existing records verbatim in front of the new ones.
    records: list[dict] = list(prepend or [])
    grand = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for i, it in enumerate(eligible):
        tid = start_id + i
        l1 = it["instruction"].strip()
        apps = [a.strip() for a in it["mapped_kb_apps"] if a.strip()]
        hint = "、".join(apps)
        primary = apps[0]
        ttype = task_type_for(it, primary, covered)

        if resume and tid in existing and existing[tid].get("Level3-INS"):
            records.append(existing[tid])
            print(f"[{i + 1}/{len(eligible)}] id={tid} (skip, already done)")
            continue

        print(f"[{i + 1}/{len(eligible)}] id={tid} lang={it.get('lang')} "
              f"apps={hint} :: {l1[:50]}")
        res = _rewrite_with_retry(l1, hint, kb, api_key, lang=it.get("lang"))
        for k in grand:
            grand[k] += res.get("usage", {}).get(k, 0)

        if res.get("ok"):
            l2, l3 = res["level2"], res["level3"]
            ref_apps = res.get("referenced_apps") or apps
        else:
            print(f"   ! rewrite failed: {res.get('error')}; leaving L2/L3 empty")
            l2, l3, ref_apps = "", "", apps

        records.append({
            "Task_id": tid,
            "Task Type": ttype,
            "Invovled_App_Name": hint,
            "Original-INS": l1,
            "Level1-INS": l1,
            "Level2-INS": l2,
            "Level3-INS": l3,
            # ---- traceability (beyond the original 7 fields) ----
            "lang": it.get("lang", ""),
            "_source": it.get("source", ""),
            "_source_id": it.get("source_id", ""),
            "_referenced_apps": ref_apps,
        })
        # Incremental save so a mid-run proxy drop never loses progress.
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        if sleep:
            time.sleep(sleep)

    print(f"\nrewrite token totals: {grand}")
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--start-id", type=int, default=56,
                    help="Task_id of the first new task (default 56, after original max 55)")
    ap.add_argument("--limit", type=int, default=None, help="only process first N eligible")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between LLM calls")
    ap.add_argument("--dry-run", action="store_true",
                    help="only print the eligible selection, no LLM calls")
    ap.add_argument("--resume", action="store_true",
                    help="reuse already-generated records in --out, only fill missing L3")
    ap.add_argument("--seed", default=None,
                    help="JSON file of hand-authored items (instruction/mapped_kb_apps/lang/"
                         "scenario/source) to use INSTEAD of the 5 datasets")
    ap.add_argument("--append", action="store_true",
                    help="append new tasks after existing records in --out "
                         "(Task_id auto-continues from current max)")
    args = ap.parse_args()

    covered = load_covered_apps()
    if args.seed:
        with open(args.seed, "r", encoding="utf-8") as f:
            items = json.load(f)
        src_label = f"seed:{os.path.basename(args.seed)}"
    else:
        items = load_subset_items()
        src_label = "5 datasets"
    eligible = select_eligible(items, covered)
    if args.limit:
        eligible = eligible[: args.limit]

    print(f"covered apps (with action_object_str): {len(covered)}")
    print(f"source: {src_label} -> {len(items)} items")
    print(f"eligible (all apps covered): {len(eligible)}")
    # Surface any seed items dropped for an uncovered app (typo guard).
    dropped = [it for it in items
               if not all(a.strip() in covered for a in (it.get("mapped_kb_apps") or []))
               or not it.get("mapped_kb_apps")]
    if dropped:
        print(f"  WARNING: {len(dropped)} item(s) dropped (uncovered/empty app):")
        for it in dropped:
            print(f"    {it.get('mapped_kb_apps')} :: {it.get('instruction')}")
    by_lang = {}
    for it in eligible:
        by_lang[it.get("lang", "?")] = by_lang.get(it.get("lang", "?"), 0) + 1
    print(f"  by lang: {by_lang}")

    # Append mode: load existing records, continue Task_id from their max.
    prepend, start_id = None, args.start_id
    if args.append and os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8") as f:
            prepend = json.load(f)
        if prepend:
            start_id = max(r["Task_id"] for r in prepend) + 1
        print(f"append mode: {len(prepend or [])} existing records, new Task_id from {start_id}")

    if args.dry_run:
        for i, it in enumerate(eligible):
            print(f"  id={start_id + i} [{it.get('lang')}] {it['mapped_kb_apps']} :: {it['instruction']}")
        return

    api_key = os.getenv("OPENROUTER_API_KEY") or rw.FALLBACK_API_KEY
    kb = rw.load_kb()
    records = build_records(eligible, covered, kb, api_key, start_id,
                            args.sleep, args.out, args.resume, prepend=prepend)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    n_ok = sum(1 for r in records if r.get("Level3-INS"))
    print(f"\nwrote {len(records)} tasks ({n_ok} with L2/L3) -> {args.out}")


if __name__ == "__main__":
    main()
