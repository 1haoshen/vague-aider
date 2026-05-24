"""instruction_rewrite_v2.py

Token-efficient L1 -> L2 + L3 rewriter for Vague-ins.json.

Design vs v1:
- Single LLM call returns both L2 and L3 (was: full-KB + 6 verbose few-shots).
- Two KB files merged by app_name: AppUi-final.json (115 apps, CN-leaning,
  has `scenario`) + cn-en-app-data-action-str.json (34 apps, EN-leaning).
- Retrieval is deterministic and runs locally (no LLM):
    1. If task carries Invovled_App_Name, normalize the messy string
       (separators 、,/\\s, abbreviations, typos) and resolve to KB apps
       via alias table + substring/transliteration fuzzy match.
    2. Otherwise, score apps by token overlap between L1 and
       (app_name + common_functions text).
- KB slice injected per task contains ONLY:
    {app_name, brief_introduction(<=80 chars),
     top_k_functions: [{name, action_chain}]}
  where top_k_functions are the 2-3 common_functions whose name best
  overlaps L1 tokens. This is the single biggest token saving.
- One compact few-shot (drawn from Vague-ins.json task #1) instead of 6.

Result: ~1.5-3K input tokens / task instead of ~30K.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import time
import unicodedata
from typing import Any

import requests

try:
    import json_repair  # type: ignore
except ImportError:  # pragma: no cover
    json_repair = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rewrite_v2")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
KB_CN_EN = os.path.join(REPO_ROOT, "app-data", "knowledge-base", "cn-en-app-data-action-str.json")
KB_FINAL = os.path.join(REPO_ROOT, "app-data", "knowledge-base", "AppUi-final.json")
VAGUE_INS = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins.json")
DEFAULT_OUT = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins-rewritten.json")

MODEL = "qwen/qwen3-8b"
API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
FALLBACK_API_KEY = "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"


# ---------------------------------------------------------------------------
# KB loading + merge
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip().lower())


def load_kb() -> dict[str, dict]:
    """Merge both KBs keyed by normalized app_name. AppUi-final wins on
    conflicts because it carries the `scenario` tag."""
    merged: dict[str, dict] = {}
    for path in (KB_CN_EN, KB_FINAL):
        with open(path, "r", encoding="utf-8") as f:
            for app in json.load(f):
                key = _norm(app.get("app_name", ""))
                if not key:
                    continue
                if key in merged:
                    # Prefer the entry with more functions / scenario tag.
                    incoming_fns = len(app.get("action_object_str") or {})
                    current_fns = len(merged[key].get("action_object_str") or {})
                    if incoming_fns > current_fns or "scenario" in app:
                        merged[key] = {**merged[key], **app}
                    continue
                merged[key] = app
    log.info("KB loaded: %d unique apps", len(merged))
    return merged


# ---------------------------------------------------------------------------
# Invovled_App_Name normalization
# ---------------------------------------------------------------------------

# Alias / common-typo / CN<->EN map. Keys are the messy form (normalized),
# values are the canonical KB app_name (NOT normalized — must match KB's
# `app_name` field after our own _norm).
ALIASES: dict[str, str] = {
    # CN abbreviations
    "美图": "美图秀秀",
    "网易云": "网易云音乐",
    "大宗点评": "大众点评",
    "高德": "高德地图",
    "笔记": "备忘录",
    "notepad": "备忘录",
    "notes": "备忘录",
    "note": "备忘录",
    "weather": "天气",
    "应用商店": "应用市场",
    "闹钟": "时钟",
    # EN typos
    "chorme": "Google Chrome",
    "chrome": "Google Chrome",
    "googlemaps": "Google Maps",
    "maps": "Google Maps",
    # CN <-> EN
    "bilibili": "哔哩哔哩",
    "wechat": "微信",
    "tiktok": "TikTok",
    "edge": "Microsoft Edge",
    "youtube": "YouTube",
    "facebook": "Facebook",
    "x": "X ",
    "amazon": "Amazon Shopping",
    "walmart": "Walmart ",
    "ebay": "eBay",
    "booking": "Booking",
    "tripadvisor": "Tripadvisor",
    "fandango": "Fandango",
    "neteaseCloudMusic": "网易云音乐",
    "neteasecloudmusic": "网易云音乐",
    "googlechrome": "Google Chrome",
}


def split_app_hint(raw: str) -> list[str]:
    """Split the dirty Invovled_App_Name into individual app tokens."""
    if not raw:
        return []
    # Strip quotes, newlines, tabs.
    cleaned = re.sub(r'["\t\n\r]+', " ", raw)
    # Split on any of: 、 , / and runs of whitespace.
    parts = re.split(r"[、,/]+|\s{1,}", cleaned)
    return [p.strip() for p in parts if p and p.strip()]


def resolve_app(token: str, kb: dict[str, dict]) -> str | None:
    """Resolve one messy app token to a canonical KB key (the normalized
    app_name used as the merged-dict key). Returns None if unresolved."""
    if not token:
        return None
    t = _norm(token)
    if t in kb:
        return t
    # Alias table
    alias = ALIASES.get(t)
    if alias and _norm(alias) in kb:
        return _norm(alias)
    # Substring on KB names (covers e.g. "美图" matching "美图秀秀",
    # "bilibili" already aliased, "google chrome" -> "googlechrome").
    for key, app in kb.items():
        name_n = _norm(app["app_name"])
        if t in name_n or name_n in t:
            return key
    return None


# ---------------------------------------------------------------------------
# Function selection within a chosen app
# ---------------------------------------------------------------------------

def _detect_lang(text: str) -> str:
    for ch in text:
        if unicodedata.category(ch).startswith("Lo") and "CJK" in unicodedata.name(ch, ""):
            return "zh"
    return "en"


_STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or", "with",
    "please", "help", "me", "my", "i", "you", "is", "are", "be", "it",
    "打开", "一下", "帮我", "然后", "并", "的", "了", "我", "请",
}


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    if _detect_lang(text) == "zh":
        # CJK: keep both bigrams and Latin words.
        cjk = re.findall(r"[一-鿿]", text)
        latin = re.findall(r"[a-z0-9]+", text)
        bigrams = ["".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)]
        toks = cjk + bigrams + latin
    else:
        toks = re.findall(r"[a-z0-9]+", text)
    return [t for t in toks if t not in _STOPWORDS and len(t) > 1]


def pick_functions(app: dict, instruction_tokens: list[str], top_k: int = 3) -> list[tuple[str, list[str]]]:
    """Return up to top_k (function_name, action_chain) tuples chosen by
    token overlap between the function name and the instruction."""
    aos = app.get("action_object_str") or {}
    if not aos:
        # No action chains available; return common_functions as bare strings.
        return [(fn, []) for fn in (app.get("common_functions") or [])[:top_k]]

    scored: list[tuple[int, str, list[str]]] = []
    for fn_name, chain in aos.items():
        fn_toks = set(_tokenize(fn_name))
        score = len(fn_toks.intersection(instruction_tokens))
        scored.append((score, fn_name, chain))
    scored.sort(key=lambda x: (-x[0], len(x[2])))  # prefer overlap then shorter
    # If nothing overlaps, fall back to the first 2 functions (often the
    # canonical "open + search" pattern that almost every task starts with).
    if scored and scored[0][0] == 0:
        return [(name, chain) for _, name, chain in scored[:2]]
    return [(name, chain) for score, name, chain in scored if score > 0][:top_k]


# ---------------------------------------------------------------------------
# KB slice -> compact text block
# ---------------------------------------------------------------------------

def build_kb_slice(
    instruction: str,
    app_hint: str | None,
    kb: dict[str, dict],
    max_apps: int = 4,
) -> tuple[str, list[str]]:
    """Build the compact knowledge slice to inject. Returns (slice_text,
    resolved_app_names_in_KB_canonical_form)."""
    tokens = set(_tokenize(instruction))
    chosen_keys: list[str] = []

    # 1. Strong path: caller provided Invovled_App_Name.
    if app_hint:
        for raw_tok in split_app_hint(app_hint):
            key = resolve_app(raw_tok, kb)
            if key and key not in chosen_keys:
                chosen_keys.append(key)

    # 2. Fallback / supplement: score by token overlap on app_name +
    #    common_functions text.
    if not chosen_keys:
        scored: list[tuple[int, str]] = []
        for key, app in kb.items():
            text_toks = set(_tokenize(app["app_name"]))
            for fn in app.get("common_functions") or []:
                text_toks |= set(_tokenize(fn))
            score = len(text_toks & tokens)
            if score:
                scored.append((score, key))
        scored.sort(reverse=True)
        chosen_keys = [k for _, k in scored[:max_apps]]

    chosen_keys = chosen_keys[:max_apps]

    # 3. Build the compact text block.
    blocks: list[str] = []
    canon_names: list[str] = []
    for key in chosen_keys:
        app = kb[key]
        canon_names.append(app["app_name"].strip())
        functions = pick_functions(app, list(tokens))
        intro = (app.get("brief_introduction") or "").strip()
        if len(intro) > 80:
            intro = intro[:80] + "…"
        lines = [f"## {app['app_name'].strip()}"]
        if app.get("scenario"):
            lines.append(f"scenario: {app['scenario']}")
        if intro:
            lines.append(f"intro: {intro}")
        for fn_name, chain in functions:
            if chain:
                # Compress chain into one arrow-joined line.
                lines.append(f"- {fn_name}: " + " → ".join(chain))
            else:
                lines.append(f"- {fn_name}")
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks), canon_names


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

FEW_SHOT = """\
Example
L1 (user-friendly): 把最新的自拍美颜后发给clock
KB slice:
## 美图秀秀
- 一键美颜人像: open meitu app → tap renxiangmeirong → tap latest photo → tap yijianmeiyan → tap checkmark → tap save
## 微信
- 分享图片给好友: open wechat → tap search → type friend name → tap chat → tap +/album → select image → tap send

Output JSON:
{"level2_instruction": "用美图秀秀美颜相机最新的一张照片, 打开微信将美颜好的照片发送给好友clock并发送消息'看看这个效果怎么样？'",
 "level3_instruction": "打开美图秀秀app，点击人像美容，选择图片中最新的自拍照，点击一键美容后点击右下角的打勾符号，然后点击右上角的保存。保存照片后，点击分享到微信好友，选择分享给微信好友clock，并发送消息'看看这个效果怎么样？'",
 "referenced_apps": ["美图秀秀", "微信"],
 "reason": "美图秀秀提供一键美颜路径, 微信负责发送给好友"}
"""

SYS_PROMPT = (
    "You rewrite a vague user instruction (L1) into two more concrete forms.\n"
    "L2 (agent-benchmark style): name each app + the sub-task it performs; no UI controls.\n"
    "L3 (agent-friendly): explicit GUI actions per app, drawn from the KB slice's action chains.\n"
    "Rules: (1) Only use apps from the KB slice; (2) Keep the same final deliverable as L1; "
    "(3) Match the language of the user instruction; (4) Output ONE JSON object, nothing else."
)


def build_prompt(instruction: str, kb_slice: str, lang: str | None = None) -> str:
    # The KB slice is Chinese, so the model tends to answer in Chinese even for
    # English tasks. When lang is given, force the output language explicitly.
    lang_line = ""
    if lang == "en":
        lang_line = ("\nIMPORTANT: write level2_instruction and level3_instruction FULLY in "
                     "ENGLISH. The KB slice is in Chinese, but the user task is English. "
                     "Translate any Chinese app names to their common English names "
                     "(e.g. 天气->Weather, 备忘录/笔记->Notes, 网易云音乐->NetEase Music). "
                     "Do NOT output any Chinese characters.")
    elif lang == "cn":
        lang_line = "\nIMPORTANT: write level2_instruction and level3_instruction in Chinese."
    return (
        FEW_SHOT
        + "\nNow rewrite this task.\nL1: "
        + instruction.strip()
        + "\nKB slice:\n"
        + kb_slice
        + lang_line
        + "\n\nOutput JSON with keys: level2_instruction, level3_instruction, "
        "referenced_apps (list of app names from the KB slice), reason (one short sentence)."
    )


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(prompt: str, api_key: str, timeout: int = 60) -> tuple[str, dict]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
        # Qwen3 ships in "thinking" mode by default; on OpenRouter that burns
        # all completion tokens as reasoning_tokens and leaves nothing for the
        # actual JSON. Disable it both ways for safety.
        "reasoning": {"enabled": False},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    resp = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    return text, usage


def parse_json(text: str) -> dict | None:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if json_repair is not None:
            try:
                return json_repair.loads(text)  # type: ignore[no-any-return]
            except Exception:
                return None
        return None


# ---------------------------------------------------------------------------
# Per-task rewrite
# ---------------------------------------------------------------------------

def rewrite_one(
    instruction: str,
    app_hint: str | None,
    kb: dict[str, dict],
    api_key: str,
    max_retries: int = 2,
    lang: str | None = None,
) -> dict[str, Any]:
    start = time.time()
    kb_slice, resolved = build_kb_slice(instruction, app_hint, kb)
    if not kb_slice:
        kb_slice = "(no matching apps; use general mobile UI logic)"

    prompt = build_prompt(instruction, kb_slice, lang=lang)
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    last_raw = ""
    for attempt in range(max_retries + 1):
        text, usage = call_llm(prompt, api_key)
        last_raw = text
        for k in total_usage:
            total_usage[k] += int(usage.get(k, 0) or 0)
        parsed = parse_json(text)
        if parsed and "level2_instruction" in parsed and "level3_instruction" in parsed:
            parsed.setdefault("referenced_apps", resolved)
            parsed.setdefault("reason", "")
            return {
                "ok": True,
                "level2": parsed["level2_instruction"],
                "level3": parsed["level3_instruction"],
                "referenced_apps": parsed.get("referenced_apps") or resolved,
                "reason": parsed.get("reason", ""),
                "kb_apps_injected": resolved,
                "kb_slice_chars": len(kb_slice),
                "usage": total_usage,
                "duration_s": round(time.time() - start, 2),
            }
        log.warning("attempt %d returned unparseable output", attempt + 1)

    return {
        "ok": False,
        "error": "parse_failed",
        "raw": last_raw,
        "kb_apps_injected": resolved,
        "kb_slice_chars": len(kb_slice),
        "usage": total_usage,
        "duration_s": round(time.time() - start, 2),
    }


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------

def run_batch(in_path: str, out_path: str, api_key: str, limit: int | None = None) -> None:
    with open(in_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    kb = load_kb()

    out_records: list[dict] = []
    grand_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    t0 = time.time()

    for idx, task in enumerate(tasks):
        if limit is not None and idx >= limit:
            break
        l1 = task.get("Level1-INS") or task.get("Original-INS") or ""
        if not l1.strip():
            log.info("skip task %s: empty L1", task.get("Task_id"))
            continue
        hint = task.get("Invovled_App_Name") or ""
        log.info("[%d/%d] task_id=%s hint=%r", idx + 1, len(tasks), task.get("Task_id"), hint)
        result = rewrite_one(l1, hint, kb, api_key)
        for k in grand_usage:
            grand_usage[k] += result["usage"].get(k, 0)

        record = dict(task)
        if result["ok"]:
            record["Level2-INS_v2"] = result["level2"]
            record["Level3-INS_v2"] = result["level3"]
            record["_rewrite_meta"] = {
                "referenced_apps": result["referenced_apps"],
                "reason": result["reason"],
                "kb_apps_injected": result["kb_apps_injected"],
                "kb_slice_chars": result["kb_slice_chars"],
                "usage": result["usage"],
                "duration_s": result["duration_s"],
                "model": MODEL,
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            }
        else:
            record["_rewrite_meta"] = {
                "error": result.get("error"),
                "raw": result.get("raw"),
                "usage": result["usage"],
                "duration_s": result["duration_s"],
            }
        out_records.append(record)

        # Incremental save so a crash doesn't lose progress.
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_records, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    n_ok = sum(1 for r in out_records if "Level2-INS_v2" in r)
    log.info(
        "done: %d/%d ok in %.1fs; total tokens=%s (avg/task=%.0f input + %.0f output)",
        n_ok, len(out_records), elapsed, grand_usage,
        grand_usage["prompt_tokens"] / max(n_ok, 1),
        grand_usage["completion_tokens"] / max(n_ok, 1),
    )


def run_single(instruction: str, hint: str | None, api_key: str) -> None:
    kb = load_kb()
    result = rewrite_one(instruction, hint, kb, api_key)
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="in_path", default=VAGUE_INS, help="path to Vague-ins.json")
    p.add_argument("--out", dest="out_path", default=DEFAULT_OUT, help="output JSON")
    p.add_argument("--limit", type=int, default=None, help="only run first N tasks")
    p.add_argument("--single", default=None, help="run on a single ad-hoc L1 instruction")
    p.add_argument("--hint", default=None, help="Invovled_App_Name override for --single")
    args = p.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY") or FALLBACK_API_KEY

    if args.single:
        run_single(args.single, args.hint, api_key)
    else:
        run_batch(args.in_path, args.out_path, api_key, args.limit)


if __name__ == "__main__":
    main()
