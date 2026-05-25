#!/usr/bin/env python3
"""instruction_wordcloud.py

Word clouds of the VagueBench-expanded L1 (headline / most-vague) instructions
in ``Vague-ins-expanded.json``. The benchmark is bilingual, so we split each
task's L1 string by language and render two clouds:

  * wordcloud_cn.png  -- Chinese L1 instructions (jieba word segmentation)
  * wordcloud_en.png  -- English L1 instructions (regex tokenisation)

Cleaning (addresses earlier feedback):
  * Regular-weight fonts (Noto Sans CJK / DejaVu Sans), not bold -- thinner glyphs.
  * A NAMES stop set removes per-instruction entity / recipient names and
    placeholders (e.g. Kai Chen, Elon Musk, clock, xxoo, zyy) and explicit
    user-related tokens, so only the shared action vocabulary surfaces.

Both clouds are masked to a phone silhouette to echo the dataset overview figure.
Run:  python3 instruction_wordcloud.py
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter

import jieba
import matplotlib
import numpy as np
from PIL import Image, ImageDraw
from wordcloud import WordCloud

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins-expanded.json")

# Regular (not bold) weights -> thinner glyphs.
CJK_FONT = "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"
EN_FONT = os.path.join(os.path.dirname(matplotlib.__file__),
                       "mpl-data", "fonts", "ttf", "DejaVuSans.ttf")

# Person / recipient / placeholder / explicit-user tokens to drop from BOTH
# languages (matched lower-cased; Chinese names handled in CN_STOP).
NAMES = {
    # placeholders / dummy ids
    "xxoo", "xxx", "xx", "zyy", "f1",
    # contacts / recipients / people named in individual tasks
    "kai", "chen", "kaichen", "daniel", "kevin", "carl", "mia", "lucy",
    "hao", "alex", "rui", "elon", "musk", "lebron", "james", "clock",
    "tom", "ming", "xiao", "carl", "rickandmorty",
    # meta / self-reference
    "agent", "user",
}

CN_STOP = set("""
的 了 我 你 他 她 它 们 把 给 帮 请 个 这 那 些 和 与 及 或 在 用 到 为 是 有 就 都 也 还
一下 然后 接着 并且 并 帮我 一个 一份 一双 一本 一台 一条 一张 一首 一段 几件 可以 需要 想要
要求 进行 一些 什么 怎么 如何 以及 之后 现在 今天 让 我的 我要 我查 麻烦 通过 关于 这个 那个
自己 一起 大家 这样 其中 正在 左右 用户 多少 结果 一部 哪一部
""".split()) | NAMES

EN_STOP = set("""
the a an to of in on for and or with please help me my i you it is are be can could would
this that these those at as by from into about your our their his her its will want need
me's let lets do does make get go put set take show tell find open check using use up out
one two three four five six many few next last here there now today tomorrow then also more
most very just like than based am pm oct etc us if when which what who how have has had
""".split()) | NAMES


def has_cjk(s: str) -> bool:
    return any("CJK" in unicodedata.name(c, "") for c in (s or ""))


def cn_freqs(texts: list[str]) -> Counter:
    c: Counter = Counter()
    for t in texts:
        for w in jieba.cut(t):
            w = w.strip()
            if not w or w in CN_STOP:
                continue
            if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", w):
                if len(w) > 1 and w.lower() not in NAMES:
                    c[w.lower()] += 1
            elif len(w) >= 2 and any("CJK" in unicodedata.name(ch, "") for ch in w):
                c[w] += 1
    return c


def en_freqs(texts: list[str]) -> Counter:
    c: Counter = Counter()
    for t in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z']+", t.lower()):
            w = w.replace("’", "'")
            w = re.sub(r"'(s|ll|re|ve|d|m)$", "", w).strip("'")  # drop contractions
            if not w or w in EN_STOP or len(w) < 2:
                continue
            c[w] += 1
    return c


def phone_mask(w: int, h: int) -> np.ndarray:
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    m = int(min(w, h) * 0.07)
    r = int(min(w, h) * 0.12)
    d.rounded_rectangle([m, m, w - m, h - m], radius=r, fill=0)
    return np.array(img)


def frame_overlay(canvas: Image.Image) -> Image.Image:
    w, h = canvas.size
    d = ImageDraw.Draw(canvas)
    m = int(min(w, h) * 0.045)
    r = int(min(w, h) * 0.12)
    d.rounded_rectangle([m, m, w - m, h - m], radius=r,
                        outline=(20, 20, 20), width=int(min(w, h) * 0.022))
    return canvas


def make_cloud(freqs: Counter, out: str, title: str, font: str) -> None:
    W, H = 1600, 900
    mask = phone_mask(W, H)
    wc = WordCloud(
        font_path=font, width=W, height=H, mask=mask,
        background_color="white", colormap="viridis",
        prefer_horizontal=0.95, max_words=150, relative_scaling=0.5,
        min_font_size=10, max_font_size=170, margin=2, random_state=42,
    ).generate_from_frequencies(freqs)
    img = frame_overlay(wc.to_image().convert("RGB"))
    img.save(out, dpi=(300, 300))
    top = ", ".join(f"{w}({n})" for w, n in freqs.most_common(12))
    print(f"{title}: {sum(freqs.values())} tokens, {len(freqs)} types -> {os.path.basename(out)}")
    print(f"   top: {top}")


def main() -> None:
    data = json.load(open(SRC, encoding="utf-8"))
    cn_txt, en_txt = [], []
    for r in data:
        s = r.get("Level1-INS") or r.get("Original-INS") or ""
        (cn_txt if has_cjk(s) else en_txt).append(s)
    print(f"L1 instructions: {len(cn_txt)} CN / {len(en_txt)} EN\n")
    make_cloud(cn_freqs(cn_txt), os.path.join(HERE, "wordcloud_cn.png"), "CN cloud", CJK_FONT)
    make_cloud(en_freqs(en_txt), os.path.join(HERE, "wordcloud_en.png"), "EN cloud", EN_FONT)


if __name__ == "__main__":
    main()
