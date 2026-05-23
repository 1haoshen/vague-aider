r"""OOD rewrite of the 50 MobileWorld tasks in Vague-ins-expanded.json.

OOD principle (per project decision):
  For each task we HIDE the task's involved app(s) from the knowledge base
  before the rewriter (Qwen3-8B) sees it. The rewriter must therefore produce
  the augmented L2/L3 instruction purely from (a) the remaining similar apps'
  knowledge and (b) the model's own priors -- i.e. true out-of-distribution
  generalization to an app it has no stored procedure for.

We emit, per task, three rewrite conditions so the eval can compare them:
  - in_kb : full KB visible              (upper bound, = current paper setup)
  - ood   : KB \ {involved apps}         (the OOD condition we care about)
  - no_k  : empty KB                     (rewriter-only lower bound)

Usage:
  export QWEN3_API_KEY=sk-...                  # OpenRouter key
  python ood50_builder.py --model qwen/qwen3-8b --out ood50_rewritten.json
  python ood50_builder.py --dry-run            # only resolve which apps get hidden
"""

import argparse
import copy
import json
from pathlib import Path

from instr_rewrite_1 import load_app_data, rewrite_instruction

REPO = Path(__file__).resolve().parents[2]
VAGUE_INS = REPO / "app-data" / "Ins-bench" / "Vague-ins-expanded.json"
KB_PATH = Path(__file__).resolve().parent / "cn-en-app-data-action-str.json"


def load_kb() -> list:
    """Load the local KB, ignoring instr_rewrite_1's stale hardcoded path."""
    return load_app_data(str(KB_PATH))

# Involved-app strings in vague-ins use loose Chinese/English names that do not
# exactly match KB app_name keys. Map each surface form to the KB key(s) to hide.
# A surface form mapping to [] means "no KB entry to hide" (already OOD).
APP_ALIAS = {
    "闹钟": ["闹钟 "],            # trailing space in KB key
    "相册": ["相册"],
    "淘宝": ["淘宝"],
    "京东": ["京东"],
    "微信": ["微信"],
    "小红书": ["小红书"],
    "知乎": ["知乎"],
    "大众点评": ["大众点评"],
    "猫眼": ["猫眼"],
    "美图": ["美图秀秀"],
    "bilibili": ["哔哩哔哩"],
    "Chrome": ["Google/Chorme"],
    "高德地图(Amap)": ["高德地图"],
    "高德地图": ["高德地图"],
    "googleMap": ["Google Maps"],
    # Not in KB -> nothing to hide (these tasks are inherently OOD already):
    "信息": [],
    "日历": [],
    "gmail": [],
    "应用商店": [],
}


def split_apps(involved: str) -> list[str]:
    """Split the Invovled_App_Name field on common separators."""
    out: list[str] = []
    for chunk in involved.replace("、", ",").replace("，", ",").replace(" ", ",").split(","):
        c = chunk.strip()
        if c:
            out.append(c)
    return out


def resolve_hidden_keys(involved: str, kb_names: set[str]) -> tuple[list[str], list[str]]:
    """Return (kb_keys_to_hide, unmapped_surface_forms)."""
    hide, unmapped = [], []
    for surface in split_apps(involved):
        if surface in APP_ALIAS:
            for key in APP_ALIAS[surface]:
                if key in kb_names:
                    hide.append(key)
        else:
            unmapped.append(surface)
    return sorted(set(hide)), unmapped


def kb_minus(kb: list, hidden_keys: set[str]) -> list:
    return [copy.deepcopy(a) for a in kb if a["app_name"] not in hidden_keys]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen/qwen3-8b")
    ap.add_argument("--vague_ins", type=Path, default=VAGUE_INS)
    ap.add_argument("--out", type=Path, default=Path("ood50_rewritten.json"))
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve hidden apps only, no API calls")
    args = ap.parse_args()

    kb = load_kb()
    kb_names = {a["app_name"] for a in kb}
    tasks = json.loads(args.vague_ins.read_text(encoding="utf-8"))
    mw = [t for t in tasks if t.get("_source_bench") == "MobileWorld"]
    print(f"MobileWorld tasks: {len(mw)}")

    out = []
    for t in mw:
        involved = t.get("Invovled_App_Name", "")
        hidden, unmapped = resolve_hidden_keys(involved, kb_names)
        user_ins = t.get("Original-INS") or t.get("Level1-INS")

        rec = {
            "Task_id": t["Task_id"],
            "involved_apps": involved,
            "hidden_kb_keys": hidden,
            "unmapped_surface_forms": unmapped,
            "original_instruction": user_ins,
        }

        if args.dry_run:
            out.append(rec)
            print(f"[{t['Task_id']:>3}] hide={hidden} unmapped={unmapped}")
            continue

        kb_ood = kb_minus(kb, set(hidden))
        rec["ood"] = rewrite_instruction(user_ins, app_data_override=kb_ood,
                                         model_override=args.model)
        rec["in_kb"] = rewrite_instruction(user_ins, app_data_override=kb,
                                           model_override=args.model)
        rec["no_k"] = rewrite_instruction(user_ins, app_data_override=[],
                                          model_override=args.model)
        out.append(rec)
        print(f"[{t['Task_id']:>3}] done  hide={hidden}")

    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(out)} records -> {args.out}")


if __name__ == "__main__":
    main()
