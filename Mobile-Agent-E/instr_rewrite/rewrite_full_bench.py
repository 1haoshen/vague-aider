"""rewrite_full_bench.py

Merge the original Vague-ins.json (50) with the expansion
Vague-ins-expanded-local.json (59) into a single 109-task bench, then
re-run instruction_rewrite_v2 on EVERY task to regenerate Level2/Level3,
and report token consumption (prompt / completion / total) and timing.

The original Vague-ins.json is left untouched; output goes to a new file.
Per-task rewrite usage is stored under `_rw_usage` so a crash can resume
(`--resume` skips tasks that already carry `_rw_usage`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instruction_rewrite_v2 as rw  # noqa: E402

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
INS = os.path.join(REPO_ROOT, "app-data", "Ins-bench")
ORIG = os.path.join(INS, "Vague-ins.json")
EXPANDED = os.path.join(INS, "Vague-ins-expanded-local.json")
DEFAULT_OUT = os.path.join(INS, "Vague-ins-full109.json")

CORE_FIELDS = ["Task_id", "Task Type", "Invovled_App_Name",
               "Original-INS", "Level1-INS", "Level2-INS", "Level3-INS"]


def detect_lang(s: str) -> str:
    return "cn" if any("一" <= c <= "鿿" for c in (s or "")) else "en"


def normalize(rec: dict, source: str) -> dict:
    """Ensure a record has the core 7 fields + lang + _source."""
    out = {k: rec.get(k, "") for k in CORE_FIELDS}
    out["lang"] = rec.get("lang") or detect_lang(out.get("Level1-INS") or out.get("Original-INS"))
    out["_source"] = rec.get("_source") or source
    out["_source_id"] = rec.get("_source_id", rec.get("Task_id"))
    return out


def merge() -> list[dict]:
    with open(ORIG, "r", encoding="utf-8") as f:
        orig = [normalize(r, "Vague-ins") for r in json.load(f)]
    with open(EXPANDED, "r", encoding="utf-8") as f:
        exp = [normalize(r, r.get("_source", "expanded")) for r in json.load(f)]
    return orig + exp


def _rewrite_retry(l1, hint, kb, key, lang, attempts=4):
    last = None
    for a in range(attempts):
        try:
            return rw.rewrite_one(l1, hint, kb, key, lang=lang)
        except Exception as e:
            last = e
            print(f"   ! attempt {a+1}/{attempts} net error: {e}; retry in {2*(a+1)}s")
            time.sleep(2 * (a + 1))
    return {"ok": False, "error": f"network: {last}",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "duration_s": 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--resume", action="store_true",
                    help="skip tasks already carrying _rw_usage in --out")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    # Resume: start from whatever is already in --out, else from a fresh merge.
    if args.resume and os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8") as f:
            records = json.load(f)
        print(f"resume: loaded {len(records)} records from {args.out}")
    else:
        records = merge()
        print(f"merged {len(records)} tasks (orig 50 + expanded 59)")

    kb = rw.load_kb()
    key = os.getenv("OPENROUTER_API_KEY") or rw.FALLBACK_API_KEY

    grand = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    api_secs = 0.0
    n_done = n_skip = n_fail = 0
    wall0 = time.time()

    todo = records if args.limit is None else records[: args.limit]
    for i, r in enumerate(todo):
        if args.resume and r.get("_rw_usage"):
            # already rewritten; still fold its usage into the grand totals
            for k in grand:
                grand[k] += r["_rw_usage"].get(k, 0)
            api_secs += r.get("_rw_duration_s", 0) or 0
            n_skip += 1
            continue

        l1 = r.get("Level1-INS") or r.get("Original-INS") or ""
        hint = r.get("Invovled_App_Name") or ""
        lang = r.get("lang") or detect_lang(l1)
        print(f"[{i+1}/{len(todo)}] id={r['Task_id']} lang={lang} apps={hint!r} :: {l1[:45]}")

        res = _rewrite_retry(l1, hint, kb, key, lang)
        usage = res.get("usage", {})
        for k in grand:
            grand[k] += usage.get(k, 0)
        dur = res.get("duration_s", 0) or 0
        api_secs += dur

        if res.get("ok"):
            r["Level2-INS"] = res["level2"]
            r["Level3-INS"] = res["level3"]
            r["_referenced_apps"] = res.get("referenced_apps") or r.get("_referenced_apps")
            n_done += 1
        else:
            print(f"   ! rewrite failed: {res.get('error')}; keeping old L2/L3")
            n_fail += 1
        r["_rw_usage"] = {k: usage.get(k, 0) for k in grand}
        r["_rw_duration_s"] = round(dur, 2)

        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        if args.sleep:
            time.sleep(args.sleep)

    wall = time.time() - wall0
    n = n_done + n_skip
    print("\n" + "=" * 60)
    print(f"重新改写完成: {n_done} 新跑 / {n_skip} 跳过(resume) / {n_fail} 失败")
    print(f"输出 -> {args.out}  (共 {len(records)} 条)")
    print("-" * 60)
    print(f"输入  token (prompt)     : {grand['prompt_tokens']:>10,}")
    print(f"输出  token (completion) : {grand['completion_tokens']:>10,}")
    print(f"总    token (total)      : {grand['total_tokens']:>10,}")
    if n:
        print(f"平均每条 total token     : {grand['total_tokens']/n:>10.1f}")
        print(f"平均每条 输入/输出       : {grand['prompt_tokens']/n:>8.1f} / {grand['completion_tokens']/n:.1f}")
    print("-" * 60)
    print(f"API 累计耗时 (sum/call)  : {api_secs:>8.1f} s")
    print(f"墙钟总耗时 (含sleep/重试): {wall:>8.1f} s")
    if n_done:
        print(f"平均每条 API 耗时        : {api_secs/n:>8.2f} s")
    print("=" * 60)


if __name__ == "__main__":
    main()
