"""Self-evolving KB demo: close the loop reviewers said is missing.

Pipeline:
  1. Run a task with current KB.
  2. If execution fails (final state != success OR max_consecutive_failures),
     mark (app, function) as a knowledge gap.
  3. Trigger self-exploration: spawn a base agent (e.g. MobileAgentE) to
     attempt that function on a clean app state, recording its trajectory.
  4. Distill the trajectory -> new action_object_str entry.
  5. Persist the augmented KB and re-run the failed task.
  6. Report before/after SR.

Run on ~5-10 apps removed from KB beforehand to demonstrate that
the loop genuinely *acquires new knowledge* online.

Usage:
  python self_evolve_demo.py --tasks demo_tasks.json --kb starter_kb.json \
      --out_kb evolved_kb.json --out_log evolve.log.json
"""

import argparse
import json
from pathlib import Path

from instr_rewrite_1 import build_prompt


def run_agent(prompt: str, task_id: str) -> dict:
    """TODO: wire to inference_agent_E.run_single_task.
    Must return {'success': bool, 'trajectory': [...], 'final_state': ...}.
    """
    raise NotImplementedError("plug in run_single_task here")


def explore_app(app_name: str, function: str, max_steps: int = 15) -> list[str]:
    """TODO: run a base mobile agent in exploration mode targeting `function`
    on `app_name`. Return the raw trajectory of UI actions as strings
    (matches the action_object_str format used in KB).
    """
    raise NotImplementedError("plug in self-exploration runner here")


def distill_trajectory(raw: list[str]) -> list[str]:
    """Strip out noise (redundant scrolls, dead-end taps). For the demo, keep
    only actions whose textual op-type is in the action vocabulary.
    """
    keep_prefixes = ("open ", "tap ", "type ", "swipe ", "long_press ", "back")
    return [a for a in raw if any(a.lower().startswith(p) for p in keep_prefixes)]


def update_kb(kb: list, app_name: str, function: str, path: list[str]) -> list:
    """Insert or overwrite the (app, function) action_object_str entry."""
    for app in kb:
        if app["app_name"] == app_name:
            app.setdefault("action_object_str", {})[function] = path
            if function not in app.get("common_functions", []):
                app.setdefault("common_functions", []).append(function)
            return kb
    # cold-start: app not in KB at all
    kb.append({
        "app_name": app_name,
        "brief_introduction": "",
        "icon_description": "",
        "common_functions": [function],
        "action_object_str": {function: path},
    })
    return kb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--kb", required=True, type=Path,
                        help="starter KB with target apps removed")
    parser.add_argument("--out_kb", required=True, type=Path)
    parser.add_argument("--out_log", required=True, type=Path)
    args = parser.parse_args()

    kb = json.loads(args.kb.read_text(encoding="utf-8"))
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))

    log = []
    for t in tasks:
        instr = t["instruction"]
        target_app = t["target_app"]
        function = t["target_function"]

        # ---- pass 1: current KB ----
        prompt1 = build_prompt(instr, kb)
        r1 = run_agent(prompt1, task_id=f"{t['id']}_pre")
        entry = {"task_id": t["id"], "pre": r1["success"]}

        if not r1["success"]:
            # ---- self-exploration ----
            raw = explore_app(target_app, function)
            distilled = distill_trajectory(raw)
            kb = update_kb(kb, target_app, function, distilled)
            entry["learned_path_len"] = len(distilled)

            # ---- pass 2: evolved KB ----
            prompt2 = build_prompt(instr, kb)
            r2 = run_agent(prompt2, task_id=f"{t['id']}_post")
            entry["post"] = r2["success"]

        log.append(entry)

    args.out_kb.write_text(json.dumps(kb, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    args.out_log.write_text(json.dumps(log, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    n = len(log)
    pre_sr = sum(1 for e in log if e.get("pre")) / n
    post_sr = sum(1 for e in log if e.get("post", e.get("pre"))) / n
    print(f"pre-evolve SR  = {pre_sr:.2%}")
    print(f"post-evolve SR = {post_sr:.2%}")


if __name__ == "__main__":
    main()
