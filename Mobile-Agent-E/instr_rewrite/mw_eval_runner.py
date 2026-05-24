"""mw_eval_runner.py

Fan out the MobileWorld-runnable entries in Vague-ins-expanded.json across
L1 / L2 / L3 instruction levels, invoke MobileWorld's `mw eval` for each
level, then aggregate per-level success rates and per-task pass/fail.

Workflow per level:
  1. AST-patch each task file's `goal = ...` attribute to the level's
     instruction (Level1-INS / Level2-INS / Level3-INS).
  2. Run `mw eval --task <comma-class-list> --agent_type ... --model_name ...`
     with a level-tagged log directory.
  3. Restore all task files from their .backup copies (also runs on signal /
     crash).
  4. Scan `<log_root>/<level>/<TaskClass>/result.txt` for the score; a task
     "passes" at score > 0.99 (matching MobileWorld's own scan_finished_tasks).

Output:
  - <out_dir>/mw_eval_<level>.json          per-level raw scores
  - <out_dir>/mw_eval_summary.csv           per-task x level pass matrix
  - <out_dir>/mw_eval_success_rates.csv     per-level SR
  Plus a rich-style table to stdout.

Usage:
  # Single agent, all 3 levels, all 50 MW tasks
  python Mobile-Agent-E/instr_rewrite/mw_eval_runner.py \\
      --agent qwen3vl --model-name Qwen3-VL-235B-A22B \\
      --llm-base-url https://your-openai-compatible-url \\
      --api-key  $OPENROUTER_API_KEY

  # Dry-run (no mw eval, just patch+restore to verify)
  python Mobile-Agent-E/instr_rewrite/mw_eval_runner.py --dry-run

  # Limit to specific Task_ids
  python Mobile-Agent-E/instr_rewrite/mw_eval_runner.py --task-ids 56,62,75
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VAGUE_INS = REPO / "app-data" / "Ins-bench" / "Vague-ins-expanded.json"
MW_ROOT = REPO / "MobileWorld" / "MobileWorld"
MW_TASK_DEFS = MW_ROOT / "src" / "mobile_world" / "tasks" / "definitions"
DEFAULT_OUT_DIR = REPO / "app-data" / "Ins-bench" / "mw_eval_results"
DEFAULT_LOG_ROOT = REPO / "traj_logs"

LEVELS = ("L1", "L2", "L3")
LEVEL_TO_KEY = {"L1": "Level1-INS", "L2": "Level2-INS", "L3": "Level3-INS"}
SCORE_FILE_NAME = "result.txt"  # matches mobile_world.runtime.utils.trajectory_logger


def default_mw_cmd() -> str:
    """Prefer the project's own uv venv binary (its shebang is an absolute path
    to the right python, so it works regardless of PATH / conda / sudo). Fall
    back to `uv run mw` if the venv isn't built yet.

    NOTE: no `sudo` by default. If your Docker requires root, prepend it:
      --mw-cmd "sudo <printed-default>"
    """
    venv_mw = MW_ROOT / ".venv" / "bin" / "mw"
    if venv_mw.exists():
        return str(venv_mw)
    return "uv run mw"


def preflight_mw_cmd(mw_cmd: str, cwd: str) -> tuple[bool, str]:
    """Actually invoke `<mw_cmd> --help` (with a timeout) so we catch BOTH a
    missing binary AND the `sudo: <bin>: command not found` case where sudo's
    secure_path can't see conda/uv binaries. Runs BEFORE any task files are
    patched, so a failure costs nothing."""
    cmd = mw_cmd.split() + ["--help"]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return False, f"executable '{cmd[0]}' not found on PATH"
    except subprocess.TimeoutExpired:
        return False, ("`--help` timed out (likely a sudo password prompt). "
                       "Run once interactively to cache sudo, or drop sudo.")
    out = (r.stdout or "") + (r.stderr or "")
    if "command not found" in out:
        # e.g. "sudo: uv: command not found"
        return False, out.strip().splitlines()[-1] if out.strip() else "command not found"
    if r.returncode != 0:
        return False, f"`{' '.join(cmd)}` exited {r.returncode}: {out.strip()[:200]}"
    return True, "ok"


# ----------------------------------------------------------------------------
# Task-file patching
# ----------------------------------------------------------------------------

def patch_goal(task_file: Path, new_goal: str) -> None:
    """Replace the `goal = ...` class-attribute assignment in task_file
    with a single-line `goal = <repr(new_goal)>` assignment, preserving
    indentation. Crashes if the goal node isn't found."""
    src = task_file.read_text(encoding="utf-8")
    tree = ast.parse(src)
    target = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == "goal"
            ):
                target = stmt
                break
        if target is not None:
            break
    if target is None:
        raise RuntimeError(f"no class-level `goal = ...` in {task_file}")

    lines = src.splitlines(keepends=True)
    indent = " " * target.col_offset
    # ast lineno/end_lineno are 1-indexed inclusive.
    replacement = f"{indent}goal = {new_goal!r}\n"
    new_text = "".join(lines[: target.lineno - 1]) + replacement + "".join(lines[target.end_lineno :])
    task_file.write_text(new_text, encoding="utf-8")


def backup_path(task_file: Path) -> Path:
    return task_file.with_suffix(task_file.suffix + ".vagueaider_backup")


def back_up(task_file: Path) -> None:
    bp = backup_path(task_file)
    if bp.exists():
        # Earlier run crashed without restoring — keep original.
        return
    shutil.copy2(task_file, bp)


def restore(task_file: Path) -> bool:
    bp = backup_path(task_file)
    if not bp.exists():
        return False
    shutil.move(str(bp), str(task_file))
    return True


def restore_all(task_files: list[Path]) -> int:
    restored = 0
    for tf in task_files:
        if restore(tf):
            restored += 1
    return restored


# ----------------------------------------------------------------------------
# Result parsing
# ----------------------------------------------------------------------------

def parse_score(result_file: Path) -> float | None:
    try:
        with result_file.open() as f:
            head = f.readline()
    except FileNotFoundError:
        return None
    if "score:" in head:
        try:
            return float(head.split("score:")[1].strip())
        except ValueError:
            return None
    return None


def collect_level_scores(log_root: Path, level: str, class_names: list[str]) -> dict[str, float | None]:
    level_dir = log_root / level
    scores: dict[str, float | None] = {}
    for cls in class_names:
        scores[cls] = parse_score(level_dir / cls / SCORE_FILE_NAME)
    return scores


# ----------------------------------------------------------------------------
# Level loop
# ----------------------------------------------------------------------------

def run_one_level(
    args: argparse.Namespace,
    mw_entries: list[dict],
    level: str,
) -> dict[str, float | None]:
    """Inject the level's instruction as the agent-facing goal (via the
    MW_GOAL_OVERRIDE json that the patched mobile_world/core/runner.py reads),
    run `mw eval`, collect scores. The task setup + is_successful checker in the
    container are untouched, so only the agent's instruction varies by level."""
    level_key = LEVEL_TO_KEY[level]

    # Build {task_class: level_instruction} — keyed by class name because
    # mobile_world resolves the goal by task_name == class name.
    override = {t["_mw_task_class"]: t[level_key] for t in mw_entries}
    if args.verbose:
        for cls, ins in override.items():
            print(f"  {level} {cls:42s} -> {ins[:60]!r}")

    log_root = Path(args.log_root)
    level_log = log_root / level
    ov_path = log_root / f"goal_override_{level}.json"

    if args.dry_run:
        print(f"[dry-run] level={level}: would inject {len(override)} goal overrides "
              f"via MW_GOAL_OVERRIDE and call mw eval.")
        return {t["_mw_task_class"]: None for t in mw_entries}

    log_root.mkdir(parents=True, exist_ok=True)
    level_log.mkdir(parents=True, exist_ok=True)
    with ov_path.open("w", encoding="utf-8") as f:
        json.dump(override, f, ensure_ascii=False, indent=2)

    class_list = ",".join(t["_mw_task_class"] for t in mw_entries)
    cmd = build_mw_eval_cmd(args, class_list, level_log)
    env = dict(os.environ, MW_GOAL_OVERRIDE=str(ov_path))
    print(f"\n========== Running {level} ({len(mw_entries)} tasks) ==========")
    print(f"(cwd={args.mw_cwd})  MW_GOAL_OVERRIDE={ov_path}\n  " + " ".join(cmd))
    rc = subprocess.call(cmd, cwd=args.mw_cwd, env=env)
    if rc != 0:
        print(f"⚠ mw eval exited with code {rc} for {level}; collecting whatever it managed to write.")

    return collect_level_scores(log_root, level, [t["_mw_task_class"] for t in mw_entries])


def build_mw_eval_cmd(args: argparse.Namespace, class_list: str, level_log: Path) -> list[str]:
    # `--mw-cmd` is split on spaces so it can carry e.g. "sudo uv run mw".
    cmd = args.mw_cmd.split() + ["eval",
           "--agent_type", args.agent,
           "--task", class_list,
           "--max_round", str(args.max_round),
           "--step_wait_time", str(args.step_wait_time),
           "--log_file_root", str(level_log)]
    if args.model_name:
        cmd += ["--model_name", args.model_name]
    if args.llm_base_url:
        cmd += ["--llm_base_url", args.llm_base_url]
    if args.api_key:
        cmd += ["--api_key", args.api_key]
    if args.max_concurrency is not None:
        cmd += ["--max_concurrency", str(args.max_concurrency)]
    if args.enable_mcp:
        cmd.append("--enable_mcp")
    if args.enable_user_interaction:
        cmd.append("--enable_user_interaction")
    return cmd


# ----------------------------------------------------------------------------
# Aggregation + output
# ----------------------------------------------------------------------------

PASS_THRESHOLD = 0.99


def summarize(
    mw_entries: list[dict],
    per_level: dict[str, dict[str, float | None]],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Per-task per-level matrix.
    matrix_path = out_dir / "mw_eval_summary.csv"
    with matrix_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Task_id", "task_class", "task_path", "apps", "lang",
                    "L1_score", "L2_score", "L3_score",
                    "L1_pass", "L2_pass", "L3_pass"])
        for t in mw_entries:
            row = [t["Task_id"], t["_mw_task_class"], t["_mw_task_path"],
                   t["Invovled_App_Name"],
                   "cn" if any("一" <= c <= "鿿" for c in t["Level1-INS"]) else "en"]
            for lvl in LEVELS:
                row.append(per_level[lvl].get(t["_mw_task_class"]))
            for lvl in LEVELS:
                s = per_level[lvl].get(t["_mw_task_class"])
                row.append(int(s is not None and s > PASS_THRESHOLD))
            w.writerow(row)

    # Per-level success rate.
    sr_path = out_dir / "mw_eval_success_rates.csv"
    with sr_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "n_total", "n_with_score", "n_passed", "success_rate"])
        for lvl in LEVELS:
            scores = list(per_level[lvl].values())
            with_score = [s for s in scores if s is not None]
            passed = [s for s in with_score if s > PASS_THRESHOLD]
            sr = len(passed) / len(scores) if scores else 0.0
            w.writerow([lvl, len(scores), len(with_score), len(passed), f"{sr:.4f}"])

    # Per-level raw scores as JSON for downstream analysis.
    for lvl in LEVELS:
        (out_dir / f"mw_eval_{lvl}.json").write_text(
            json.dumps(per_level[lvl], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Console summary.
    print("\n" + "=" * 60)
    print(f"{'level':>5s}  {'total':>5s}  {'scored':>6s}  {'passed':>6s}  {'SR%':>6s}")
    print("-" * 60)
    for lvl in LEVELS:
        scores = list(per_level[lvl].values())
        with_score = [s for s in scores if s is not None]
        passed = [s for s in with_score if s > PASS_THRESHOLD]
        sr = len(passed) / len(scores) if scores else 0.0
        print(f"{lvl:>5s}  {len(scores):>5d}  {len(with_score):>6d}  {len(passed):>6d}  {sr * 100:>5.1f}%")
    print(f"\nOutputs written to {out_dir}/")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vague-ins", default=str(VAGUE_INS),
                   help="Path to Vague-ins-expanded.json")
    p.add_argument("--levels", default="L1,L2,L3",
                   help="Comma list of levels to run (default: L1,L2,L3)")
    p.add_argument("--task-ids", default=None,
                   help="Optional comma list of Task_ids to restrict to")

    # how to invoke the mw CLI + from which directory
    p.add_argument("--mw-cmd", default=default_mw_cmd(),
                   help="Command prefix to invoke the mw CLI. Default auto-detects "
                        "MobileWorld/.venv/bin/mw (absolute, PATH-independent). "
                        "Prepend 'sudo ' if your Docker needs root.")
    p.add_argument("--mw-cwd", default=str(MW_ROOT),
                   help="Working dir to run mw from (default: the MobileWorld repo)")

    # mw eval pass-through
    p.add_argument("--agent", default="qwen3vl",
                   help="agent_type for mw eval (e.g. qwen3vl, general_e2e)")
    p.add_argument("--model-name", default=None)
    p.add_argument("--llm-base-url", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--max-round", type=int, default=50)
    p.add_argument("--step-wait-time", type=float, default=3.0)
    p.add_argument("--max-concurrency", type=int, default=None)
    p.add_argument("--enable-mcp", action="store_true", default=True)
    p.add_argument("--no-enable-mcp", dest="enable_mcp", action="store_false")
    p.add_argument("--enable-user-interaction", action="store_true", default=True)
    p.add_argument("--no-enable-user-interaction", dest="enable_user_interaction",
                   action="store_false")

    p.add_argument("--log-root", default=str(DEFAULT_LOG_ROOT),
                   help="Root dir for per-level traj logs (subdir per level)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                   help="Where to write summary CSV / JSON")
    p.add_argument("--dry-run", action="store_true",
                   help="Patch + restore but don't call mw eval")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    # Load Vague-ins-expanded and filter to MobileWorld entries.
    with open(args.vague_ins) as f:
        all_entries = json.load(f)
    mw_entries = [t for t in all_entries if t.get("_source_bench") == "MobileWorld"]
    if args.task_ids:
        wanted = {int(x) for x in args.task_ids.split(",") if x.strip()}
        mw_entries = [t for t in mw_entries if t["Task_id"] in wanted]
    if not mw_entries:
        sys.exit("No MobileWorld entries to run.")

    for t in mw_entries:
        if "_mw_task_path" not in t or "_mw_task_class" not in t:
            sys.exit(f"Task_id {t['Task_id']} missing _mw_task_path/_mw_task_class")
        if not (MW_TASK_DEFS / t["_mw_task_path"]).exists():
            sys.exit(f"Task file not found: {t['_mw_task_path']}")

    levels = [lv.strip() for lv in args.levels.split(",") if lv.strip()]
    for lv in levels:
        if lv not in LEVELS:
            sys.exit(f"unknown level {lv!r}; expected one of {LEVELS}")

    # Signal-safe restore for all task files we might touch.
    all_task_files = [MW_TASK_DEFS / t["_mw_task_path"] for t in mw_entries]

    def _on_sig(signum, frame):
        n = restore_all(all_task_files)
        print(f"\n⚠ caught signal {signum}; restored {n} task files. Exiting.")
        sys.exit(130)

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)

    print(f"MobileWorld entries to evaluate: {len(mw_entries)}")
    print(f"Levels: {levels}")
    print(f"Agent: {args.agent}  Model: {args.model_name}  Log root: {args.log_root}")
    print(f"mw-cmd: {args.mw_cmd}   (cwd: {args.mw_cwd})")

    # Preflight: make sure the mw executable resolves BEFORE patching any files,
    # so a PATH/sudo problem fails fast instead of after a patch+restore cycle.
    if not args.dry_run:
        ok, msg = preflight_mw_cmd(args.mw_cmd, args.mw_cwd)
        if not ok:
            sys.exit(
                f"\n✗ mw preflight failed for --mw-cmd {args.mw_cmd!r}:\n    {msg}\n\n"
                f"  Common cause: `sudo` resets PATH and can't see conda/uv binaries.\n"
                f"  Fixes:\n"
                f"    • use the venv binary directly (current default):\n"
                f"        --mw-cmd \"{MW_ROOT / '.venv' / 'bin' / 'mw'}\"\n"
                f"    • if Docker needs root, prepend sudo to that absolute path:\n"
                f"        --mw-cmd \"sudo {MW_ROOT / '.venv' / 'bin' / 'mw'}\"\n"
                f"    • or preserve PATH through sudo:\n"
                f"        --mw-cmd \"sudo env PATH=$PATH uv run mw\"\n"
            )
        print(f"✓ mw preflight ok")
    if args.dry_run:
        print("[DRY-RUN] no actual mw eval will be invoked.")

    t0 = time.time()
    per_level: dict[str, dict[str, float | None]] = {}
    for lv in levels:
        per_level[lv] = run_one_level(args, mw_entries, lv)

    # For any level NOT run, fill with None so the matrix is well-formed.
    for lv in LEVELS:
        per_level.setdefault(lv, {t["_mw_task_class"]: None for t in mw_entries})

    summarize(mw_entries, per_level, Path(args.out_dir))
    print(f"\nTotal wall time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
