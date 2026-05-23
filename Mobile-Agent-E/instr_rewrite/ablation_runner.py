"""Ablation runner for KnowGUI EMNLP rebuttal.

Variants:
  BASE             : raw user instruction, no rewriter
  RW_ONLY          : rewriter sees empty K
  RW_RAND_K        : rewriter sees K from random unrelated apps
  RW_PROFILE       : rewriter sees only R_I (description + functions)
  RW_PATH          : rewriter sees only R_P (action_object_str)
  KNOWGUI_FULL     : rewriter sees full K = R_I + R_P
  RAW_K_NO_RW      : K concatenated directly to instruction, no rewriter

Usage:
  python ablation_runner.py --variant KNOWGUI_FULL --tasks <tasks.json> --seed 0
"""

import argparse
import copy
import json
import random
from pathlib import Path
from typing import Any

from instr_rewrite_1 import (
    APP_DATA_PATH,
    load_app_data,
    build_prompt,
)

VARIANTS = [
    "BASE",
    "RW_ONLY",
    "RW_RAND_K",
    "RW_PROFILE",
    "RW_PATH",
    "KNOWGUI_FULL",
    "RAW_K_NO_RW",
]


def strip_profile(app: dict) -> dict:
    """Remove R_I: brief_introduction, icon_description, common_functions text."""
    a = copy.deepcopy(app)
    a["brief_introduction"] = ""
    a["icon_description"] = ""
    return a


def strip_path(app: dict) -> dict:
    """Remove R_P: action_object_str."""
    a = copy.deepcopy(app)
    a["action_object_str"] = {}
    return a


def shuffle_knowledge(app_data: list, target_app_names: set, rng: random.Random) -> list:
    """Replace any matched-app entry with a randomly chosen unrelated app's K.

    Preserves the matching scaffold (same app_name keys are looked up) but
    swaps the content of (R_I, R_P) with another app's content.
    """
    pool = [a for a in app_data if a["app_name"] not in target_app_names]
    if not pool:
        return app_data
    out = []
    for a in app_data:
        if a["app_name"] in target_app_names:
            donor = rng.choice(pool)
            shuffled = copy.deepcopy(a)
            shuffled["brief_introduction"] = donor["brief_introduction"]
            shuffled["icon_description"] = donor["icon_description"]
            shuffled["common_functions"] = donor.get("common_functions", [])
            shuffled["action_object_str"] = donor.get("action_object_str", {})
            out.append(shuffled)
        else:
            out.append(a)
    return out


def apply_variant(
    variant: str,
    user_instruction: str,
    app_data: list,
    target_app_names: set,
    rng: random.Random,
) -> tuple[str, str]:
    """Return (agent_instruction, mode) where mode in {'agent_direct','rewrite'}.

    'agent_direct' means feed string straight to the GUI agent (skip rewriter).
    'rewrite' means feed to the Qwen3-4B rewriter first.
    """
    if variant == "BASE":
        return user_instruction, "agent_direct"

    if variant == "RW_ONLY":
        prompt = build_prompt(user_instruction, app_data=[])
        return prompt, "rewrite"

    if variant == "RW_RAND_K":
        shuffled = shuffle_knowledge(app_data, target_app_names, rng)
        prompt = build_prompt(user_instruction, app_data=shuffled)
        return prompt, "rewrite"

    if variant == "RW_PROFILE":
        kb = [strip_path(a) for a in app_data]
        prompt = build_prompt(user_instruction, app_data=kb)
        return prompt, "rewrite"

    if variant == "RW_PATH":
        kb = [strip_profile(a) for a in app_data]
        prompt = build_prompt(user_instruction, app_data=kb)
        return prompt, "rewrite"

    if variant == "KNOWGUI_FULL":
        prompt = build_prompt(user_instruction, app_data=app_data)
        return prompt, "rewrite"

    if variant == "RAW_K_NO_RW":
        relevant = [a for a in app_data if a["app_name"] in target_app_names]
        kb_dump = json.dumps(relevant, ensure_ascii=False)
        return f"{user_instruction}\n\nKNOWLEDGE:\n{kb_dump}", "agent_direct"

    raise ValueError(f"unknown variant: {variant}")


def match_target_apps(user_instruction: str, app_data: list) -> set:
    """Lightweight match — substring match on app_name. Swap for the real
    intent-driven selector from instr_rewrite_1.py if you want exact parity.
    """
    hits = set()
    text = user_instruction.lower()
    for a in app_data:
        if a["app_name"].lower() in text:
            hits.add(a["app_name"])
    return hits


def run_one_task(task: dict, variant: str, app_data: list, rng: random.Random) -> dict:
    user_instruction = task["instruction"]
    targets = match_target_apps(user_instruction, app_data)
    prompt, mode = apply_variant(variant, user_instruction, app_data, targets, rng)

    # TODO: plug your existing inference here.
    # from inference_agent_E import run_single_task
    # result = run_single_task(prompt, run_name=f"{variant}_{task['id']}_seed{rng_seed}", ...)
    # For now we just dump the prompt so you can dry-run the matrix.
    return {
        "task_id": task["id"],
        "variant": variant,
        "mode": mode,
        "matched_apps": sorted(targets),
        "agent_input": prompt,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=VARIANTS)
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--app_data", type=Path, default=Path(APP_DATA_PATH))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    app_data = load_app_data(str(args.app_data))
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))

    results = [run_one_task(t, args.variant, app_data, rng) for t in tasks]
    args.out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(results)} prompts to {args.out}")


if __name__ == "__main__":
    main()
