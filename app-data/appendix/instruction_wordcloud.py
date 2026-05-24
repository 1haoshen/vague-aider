#!/usr/bin/env python3
"""instruction_wordcloud.py

Word clouds of the VagueBench L1 (headline / most-vague) instructions in
``Vague-ins.json``. The benchmark is bilingual: each task's L1 string is either
Chinese or English, so we split by language and render two clouds:

  * wordcloud_cn.png  -- Chinese L1 instructions (jieba word segmentation)
  * wordcloud_en.png  -- English L1 instructions (regex tokenisation)

Both are masked to a phone silhouette to echo the dataset overview figure.

Run:  python3 instruction_wordcloud.py
"""

from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter

import jieba
import numpy as np
from PIL import Image, ImageDraw
from wordcloud import WordCloud
import json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(REPO_ROOT, "app-data", "Ins-bench", "Vague-ins.json")

CJK_FONT = "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc"
import matplotlib
EN_FONT = os.path.join(os.path.dirname(matplotlib.__file__),
                       "mpl-data", "fonts", "ttf", "DejaVuSans-Bold.ttf")

# Function words / fillers to drop so action verbs and app names dominate.
CN_STOP = set("""
的 了 我 你 他 她 它 们 把 给 帮 请 个 这 那 些 和 与 及 或 在 用 到 为 是 有 就 都 也 还
一下 然后 接着 并且 并 帮我 一个 可以 需要 想要 要求 进行 一些 什么 怎么 如何 以及 之后 现在
今天 一条 一张 一首 一段 让 我的 我要 麻烦 一台 通过 关于 这个 那个 自己 一起 大家 这样
""".split())
EN_STOP = set("""
the a an to of in on for and or with please help me my i you it is are be can could would
this that these those at as by from into about your our their his her its will want need
me's let lets do does make get go put set take show tell find open check using use up out
one some any all here there now today then next also more most very just like than then
""".split())


def has_cjk(s: str) -> bool:
    return any("CJK" in unicodedata.name(c, "") for c in (s or ""))


def cn_freqs(texts: list[str]) -> Counter:
    c: Counter = Counter()
    for t in texts:
        for w in jieba.cut(t):
            w = w.strip()
            # keep words >=2 CJK chars, or Latin tokens (app names like clock)
            if not w or w in CN_STOP:
                continue
            if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", w):
                if len(w) > 1:
                    c[w.lower()] += 1
            elif len(w) >= 2 and any("CJK" in unicodedata.name(ch, "") for ch in w):
                c[w] += 1
    return c


def en_freqs(texts: list[str]) -> Counter:
    c: Counter = Counter()
    for t in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z0-9'’]+", t.lower()):
            w = w.replace("’", "'")
            if w in EN_STOP or len(w) < 2:
                continue
            c[w] += 1
    return c


def phone_mask(w: int, h: int) -> np.ndarray:
    """White (255) = excluded, black (0) = fillable screen area. Landscape
    phone: rounded screen inset from a frame border."""
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    m = int(min(w, h) * 0.07)          # frame thickness
    r = int(min(w, h) * 0.12)          # corner radius
    d.rounded_rectangle([m, m, w - m, h - m], radius=r, fill=0)
    return np.array(img)


def frame_overlay(canvas: Image.Image) -> Image.Image:
    """Draw a thick rounded black phone frame on top of a finished cloud."""
    w, h = canvas.size
    d = ImageDraw.Draw(canvas)
    m = int(min(w, h) * 0.045)
    r = int(min(w, h) * 0.12)
    d.rounded_rectangle([m, m, w - m, h - m], radius=r,
                        outline=(20, 20, 20), width=int(min(w, h) * 0.022))
    return canvas


def make_cloud(freqs: Counter, out: str, title: str) -> None:
    W, H = 1600, 900
    is_cn = title.startswith("CN")
    font = CJK_FONT if is_cn else EN_FONT
    mask = phone_mask(W, H)
    wc = WordCloud(
        font_path=font, width=W, height=H, mask=mask,
        background_color="white", colormap="viridis",
        prefer_horizontal=0.92, max_words=160, relative_scaling=0.45,
        min_font_size=10, max_font_size=190, margin=2, random_state=42,
    ).generate_from_frequencies(freqs)
    img = wc.to_image().convert("RGB")
    img = frame_overlay(img)
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
    make_cloud(cn_freqs(cn_txt), os.path.join(HERE, "wordcloud_cn.png"), "CN cloud")
    make_cloud(en_freqs(en_txt), os.path.join(HERE, "wordcloud_en.png"), "EN cloud")


if __name__ == "__main__":
    main()
