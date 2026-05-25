"""run_phoneagent_batch.py

Batch-run the expanded Vague bench on a real Android phone via Open-AutoGLM
phone_agent (ADB). For each task it runs the chosen instruction level(s),
each `--repeats` times, giving every run a unique `run_name` so the per-run
`steps.json` logs land in separate folders that analyze_phoneagent_logs.py can
aggregate.

Log layout produced (phone_agent's own convention):
    <log-dir>/<exp>/t<TaskId>_<LEVEL>_r<REP>/<timestamp>/steps.json

A manifest (one JSON line per run) is also written so analysis never has to
guess: <log-dir>/<exp>/manifest.jsonl

Example:
    python run_phoneagent_batch.py \
        --bench app-data/Ins-bench/Vague-ins-expanded-local.json \
        --levels L1,L3 --repeats 2 \
        --apikey <zhipu-key> --device-id <serial> \
        --exp expand_local_run1
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
AUTOGLM_DIR = os.path.join(REPO_ROOT, "Open-AutoGLM-main")
sys.path.insert(0, AUTOGLM_DIR)

DEFAULT_BENCH = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins-full-112.json")
DEFAULT_LOG_DIR = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "phoneagent_logs")

LEVEL_FIELD = {"L1": "Level1-INS", "L2": "Level2-INS", "L3": "Level3-INS"}


def load_bench(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_task_ids(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def press_home(adb: str, device_id: str | None) -> None:
    cmd = [adb]
    if device_id:
        cmd += ["-s", device_id]
    cmd += ["shell", "input", "keyevent", "KEYCODE_HOME"]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass


def newest_log_subdir(run_root: str) -> str | None:
    """phone_agent creates <run_root>/<timestamp>/. Return newest such dir."""
    if not os.path.isdir(run_root):
        return None
    subs = [os.path.join(run_root, d) for d in os.listdir(run_root)
            if os.path.isdir(os.path.join(run_root, d))]
    if not subs:
        return None
    return max(subs, key=os.path.getmtime)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bench", default=DEFAULT_BENCH)
    ap.add_argument("--levels", default="L1,L3", help="comma list of L1/L2/L3")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--task-ids", default="51-112",
                    help="e.g. 56,57,60-65 (默认 51-112: 跳过前50条原始指令; 传 1-112 跑全部)")
    ap.add_argument("--lang-filter", default="all", choices=["all", "cn", "en"],
                    help="only run tasks of this language")
    ap.add_argument("--exp", default=time.strftime("run_%Y%m%d_%H%M%S"),
                    help="experiment name; logs go under <log-dir>/<exp>/")
    ap.add_argument("--log-dir", default=DEFAULT_LOG_DIR)

    # phone_agent model/device knobs (mirror main.py defaults)
    ap.add_argument("--base-url", default=os.getenv("PHONE_AGENT_BASE_URL",
                    "https://open.bigmodel.cn/api/paas/v4"))
    ap.add_argument("--model", default=os.getenv("PHONE_AGENT_MODEL", "autoglm-phone"))
    # Fall back to the same built-in key main.py uses, so `python run_...` works
    # without setting anything (override via --apikey or PHONE_AGENT_API_KEY).
    ap.add_argument("--apikey", default=os.getenv("PHONE_AGENT_API_KEY")
                    or "ef4ddb96c6cc4a61baa4fbf641d73a1c.W132vOIUSFKpJ0XF")
    ap.add_argument("--device-id", default=os.getenv("PHONE_AGENT_DEVICE_ID"))
    ap.add_argument("--max-steps", type=int, default=int(os.getenv("PHONE_AGENT_MAX_STEPS", "50")))
    ap.add_argument("--agent-lang", default="auto", choices=["auto", "cn", "en"],
                    help="system-prompt lang; 'auto' = follow each task's lang field")
    ap.add_argument("--adb", default=os.getenv("ADB_PATH", "adb"))
    ap.add_argument("--press-home", action="store_true", default=True,
                    help="press HOME between runs (default on)")
    ap.add_argument("--no-press-home", dest="press_home", action="store_false")
    ap.add_argument("--sleep", type=float, default=2.0, help="seconds between runs")
    ap.add_argument("--resume", action="store_true",
                    help="skip (task,level,rep) already present in manifest")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the run plan, do not touch the device")
    args = ap.parse_args()

    levels = [x.strip().upper() for x in args.levels.split(",") if x.strip()]
    for lv in levels:
        if lv not in LEVEL_FIELD:
            ap.error(f"bad level {lv}; choose from L1/L2/L3")

    bench = load_bench(args.bench)
    want_ids = parse_task_ids(args.task_ids)

    tasks = []
    for t in bench:
        if want_ids is not None and t.get("Task_id") not in want_ids:
            continue
        if args.lang_filter != "all" and t.get("lang", "") != args.lang_filter:
            continue
        tasks.append(t)

    exp_root = os.path.join(args.log_dir, args.exp)
    os.makedirs(exp_root, exist_ok=True)
    manifest_path = os.path.join(exp_root, "manifest.jsonl")

    done = set()
    if args.resume and os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    m = json.loads(line)
                    done.add((m["task_id"], m["level"], m["repeat"]))
                except Exception:
                    pass

    plan = []
    for t in tasks:
        for lv in levels:
            instr = (t.get(LEVEL_FIELD[lv]) or "").strip()
            if not instr:
                continue
            for rep in range(1, args.repeats + 1):
                if (t["Task_id"], lv, rep) in done:
                    continue
                plan.append((t, lv, rep, instr))

    print(f"bench={args.bench}")
    print(f"tasks={len(tasks)} levels={levels} repeats={args.repeats} "
          f"-> {len(plan)} runs (resume-skipped {len(done)})")
    print(f"logs -> {exp_root}")
    if args.dry_run:
        for t, lv, rep, instr in plan[:30]:
            print(f"  t{t['Task_id']} {lv} r{rep} [{t.get('lang')}]: {instr[:60]}")
        if len(plan) > 30:
            print(f"  ... (+{len(plan) - 30} more)")
        return

    if not args.apikey:
        ap.error("no --apikey and PHONE_AGENT_API_KEY unset; phone_agent needs a model key")

    # Import here so --dry-run works without the device stack installed.
    from phone_agent import PhoneAgent
    from phone_agent.agent import AgentConfig
    from phone_agent.model import ModelConfig
    from phone_agent.device_factory import DeviceType, set_device_type
    set_device_type(DeviceType.ADB)

    t0 = time.time()
    for i, (t, lv, rep, instr) in enumerate(plan):
        tid = t["Task_id"]
        task_lang = t.get("lang") or "cn"
        agent_lang = task_lang if args.agent_lang == "auto" else args.agent_lang
        run_name = f"{args.exp}/t{tid}_{lv}_r{rep}"
        run_root = os.path.join(args.log_dir, run_name)

        print(f"\n[{i + 1}/{len(plan)}] t{tid} {lv} r{rep} lang={agent_lang}: {instr[:70]}")

        if args.press_home:
            press_home(args.adb, args.device_id)
            time.sleep(1.0)

        model_config = ModelConfig(base_url=args.base_url, model_name=args.model,
                                   api_key=args.apikey, lang=agent_lang)
        agent_config = AgentConfig(max_steps=args.max_steps, device_id=args.device_id,
                                   verbose=True, lang=agent_lang,
                                   log_dir=args.log_dir, run_name=run_name)
        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)

        run_start = time.time()
        result, error = "", None
        try:
            result = agent.run(instr)
        except KeyboardInterrupt:
            print("\ninterrupted by user")
            break
        except Exception as e:  # keep batch alive
            error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        run_dur = time.time() - run_start

        log_subdir = newest_log_subdir(run_root)
        steps_json = os.path.join(log_subdir, "steps.json") if log_subdir else None

        entry = {
            "task_id": tid, "level": lv, "repeat": rep, "lang": task_lang,
            "task_type": t.get("Task Type", ""),
            "apps": t.get("Invovled_App_Name", ""),
            "instruction": instr,
            "run_name": run_name,
            "steps_json": os.path.relpath(steps_json, REPO_ROOT) if steps_json else None,
            "result": result, "error": error,
            "wallclock_s": round(run_dur, 1),
            "model": args.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(manifest_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"   -> result: {str(result)[:80]!r}  ({run_dur:.0f}s)  log={steps_json}")

        if args.sleep:
            time.sleep(args.sleep)

    print(f"\ndone in {time.time() - t0:.0f}s; manifest -> {manifest_path}")
    print(f"next: python {os.path.relpath(__file__, REPO_ROOT)} analysis ->")
    print(f"  python Mobile-Agent-E/instr_rewrite/analyze_phoneagent_logs.py --exp-dir {exp_root}")


if __name__ == "__main__":
    main()
