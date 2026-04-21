"""
Grayscale word cloud from Reddit post/comment text that matches the
floater / vitreous topic (same token pattern as grouped_trends_graph.py).
Sizing, shade, and font file are driven primarily by **raw occurrence counts** (after
`process_text`): common terms (e.g. floaters, eye floaters, anxiety) get larger type,
darker gray, and heavier fonts; rare terms stay smaller and lighter.

Reads Jacob pipeline CSVs; merges posts (`text`) and comments (`body`).

Usage (from repo root):
  VIRTUOUS/floater-simulation-service/.venv/bin/python \\
    ankitgupta/semantic_analysis_viz/floater_word_cloud.py

Requires: pip install wordcloud
"""

from __future__ import annotations

import hashlib
import inspect
import os
import platform
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JACOB_RS_ROOT = REPO_ROOT / "jacob_folder" / "reddit_scrapping"
_MPL_CACHE = REPO_ROOT / "ankitgupta" / "semantic_analysis_viz" / ".mpl_cache"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

if str(JACOB_RS_ROOT) not in sys.path:
    sys.path.insert(0, str(JACOB_RS_ROOT))

from PIL import Image, ImageDraw, ImageFont

from reddit_scrapping.config import RedditResearchConfig
from wordcloud import WordCloud, STOPWORDS

_FLOATERS_TOPIC = re.compile(
    r"\b(floaters?|eye floaters|vitreous|vitreous opacity|opacities)\b",
    re.IGNORECASE,
)

def _resolve_weight_font_paths() -> list[str]:
    """Light → heavy order: regular sans, serif, bold sans, serif bold (when present)."""
    import matplotlib
    import matplotlib.font_manager as fm

    paths: list[str] = []
    tdir = Path(matplotlib.matplotlib_fname()).resolve().parent / "fonts" / "ttf"
    for name in (
        "DejaVuSans.ttf",
        "DejaVuSerif.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSerif-Bold.ttf",
    ):
        candidate = tdir / name
        if candidate.is_file():
            resolved = str(candidate)
            if resolved not in paths:
                paths.append(resolved)

    if len(paths) < 2:
        for spec in (
            {"family": "DejaVu Sans", "weight": "normal"},
            {"family": "DejaVu Sans", "weight": "bold"},
        ):
            p = fm.findfont(fm.FontProperties(**spec))
            if p and p not in paths:
                paths.append(p)

    if len(paths) < 2 and platform.system() == "Darwin":
        for candidate in (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ):
            cp = Path(candidate)
            if cp.is_file():
                resolved = str(cp.resolve())
                if resolved not in paths:
                    paths.append(resolved)

    if not paths:
        paths = [WordCloud().font_path]
    return paths


class VariableWeightWordCloud(WordCloud):
    """WordCloud that uses several font files so words vary in stroke weight."""

    def __init__(
        self,
        weight_font_paths: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        if weight_font_paths is None:
            weight_font_paths = _resolve_weight_font_paths()
        uniq: list[str] = []
        for p in weight_font_paths:
            if p not in uniq:
                uniq.append(p)
        self._weight_paths = uniq
        mid = self._weight_paths[len(self._weight_paths) // 2]
        kwargs.setdefault("font_path", mid)
        super().__init__(**kwargs)

    def _pick_font_path(self, word: str, normalized_freq: float) -> str:
        """Map corpus-normalized frequency (max=1) to font index: rare→light, common→bold."""
        paths = self._weight_paths
        if len(paths) == 1:
            return paths[0]
        t = max(0.0, min(1.0, float(normalized_freq)))
        # Exponent >1 pulls mass toward the heaviest fonts for high-occurrence words.
        t_eff = t**1.38
        base_f = t_eff * (len(paths) - 1)
        h = int(
            hashlib.md5(word.lower().encode(), usedforsecurity=False).hexdigest()[:4],
            16,
        )
        # Small tie-break only; occurrence still dominates.
        tie = (h % 7) / 14.0 * (1.0 - t) ** 0.5
        idx = int(round(base_f + 0.45 * tie))
        idx = max(0, min(len(paths) - 1, idx))
        return paths[idx]

    def generate_from_frequencies(self, frequencies, max_font_size=None):
        wc_self = self
        orig_tt = ImageFont.truetype

        def truetype_hook(font_path, size, *args, **kwargs):
            if str(font_path) == str(wc_self.font_path):
                stk = inspect.stack()
                if len(stk) > 1 and stk[1].function == "generate_from_frequencies":
                    loc = stk[1].frame.f_locals
                    w, fq = loc.get("word"), loc.get("freq")
                    if w is not None and fq is not None:
                        font_path = wc_self._pick_font_path(w, float(fq))
            return orig_tt(font_path, size, *args, **kwargs)

        ImageFont.truetype = truetype_hook
        try:
            return WordCloud.generate_from_frequencies(
                self, frequencies, max_font_size=max_font_size
            )
        finally:
            ImageFont.truetype = orig_tt

    def to_image(self):
        self._check_generated()
        if self.mask is not None:
            width = self.mask.shape[1]
            height = self.mask.shape[0]
        else:
            height, width = self.height, self.width

        img = Image.new(
            self.mode,
            (int(width * self.scale), int(height * self.scale)),
            self.background_color,
        )
        draw = ImageDraw.Draw(img)
        for (word, nf), font_size, position, orientation, color in self.layout_:
            path = self._pick_font_path(word, float(nf))
            font = ImageFont.truetype(path, int(font_size * self.scale))
            transposed_font = ImageFont.TransposedFont(font, orientation=orientation)
            pos = (int(position[1] * self.scale), int(position[0] * self.scale))
            draw.text(pos, word, fill=color, font=transposed_font)

        return self._draw_contour(img=img)


def _make_count_based_color_func(
    freq_counts: dict[str, float | int],
) -> object:
    """Grayscale from raw counts: highest-count tokens are darkest and most uniform."""
    mx = float(max(freq_counts.values())) if freq_counts else 1.0
    if mx <= 0:
        mx = 1.0

    def color_func(
        word: str,
        font_size: int,
        position: object,
        orientation: object,
        random_state=None,
        **kwargs: object,
    ) -> str:
        c = float(freq_counts.get(word, 0))
        nf = max(0.0, min(1.0, c / mx))
        # Strong curve: top terms cluster near black; long tail stays lighter.
        nf_curve = nf**0.82
        lum_lo, lum_hi = 5, 90
        lum = lum_lo + (1.0 - nf_curve) * (lum_hi - lum_lo)
        # Extra shade separation for mid/low frequency; almost none at the top.
        digest = hashlib.md5(word.lower().encode(), usedforsecurity=False).hexdigest()
        h = int(digest[:8], 16)
        amp = 3.0 + (1.0 - nf) ** 1.1 * 18.0
        lum += (h % int(2 * amp + 1)) - amp
        lum = int(max(lum_lo - 2, min(lum_hi + 2, lum)))
        return f"#{lum:02x}{lum:02x}{lum:02x}"

    return color_func


_EXTRA_STOP = {
    "https",
    "http",
    "com",
    "www",
    "reddit",
    "imgur",
    "gif",
    "png",
    "like",
    "just",
    "know",
    "think",
    "really",
    "would",
    "could",
    "also",
    "get",
    "got",
    "one",
}


def main() -> None:
    import csv

    config = RedditResearchConfig(data_dir=JACOB_RS_ROOT / "data")
    post_csv = config.processed_dir / "post_analysis.csv"
    comment_csv = config.processed_dir / "comment_analysis.csv"

    chunks: list[str] = []
    for path, field in ((post_csv, "text"), (comment_csv, "body")):
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                text = (row.get(field) or "").strip()
                if not text or not _FLOATERS_TOPIC.search(text):
                    continue
                chunks.append(text)

    corpus = " ".join(chunks)
    stop = set(STOPWORDS) | _EXTRA_STOP

    wc = VariableWeightWordCloud(
        width=2000,
        height=1300,
        background_color="white",
        mode="RGB",
        max_words=125,
        stopwords=stop,
        collocations=True,
        min_font_size=10,
        max_font_size=320,
        margin=14,
        relative_scaling=0.92,
        prefer_horizontal=0.92,
        include_numbers=False,
    )
    frequencies = wc.process_text(corpus)
    wc.color_func = _make_count_based_color_func(frequencies)
    wc.generate_from_frequencies(frequencies)

    out_dir = REPO_ROOT / "ankitgupta" / "semantic_analysis_viz"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "floaters_wordcloud.png"
    wc.to_file(str(out_path))
    print(f"Saved word cloud ({len(chunks)} texts): {out_path}")


if __name__ == "__main__":
    main()
