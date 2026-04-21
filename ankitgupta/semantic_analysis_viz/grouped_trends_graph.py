"""
Grouped bar charts:

1) **Control: floaters as a topic** — leftmost bar; row mentions floaters / vitreous but does **not**
   hit the merged mental-health pattern (baseline “topic without MH cues”).
2) **Mental health (merged)** — anxiety, depression, and closely related distress /
   mood language in one bucket (one hit per row).
3) **Dismissal + clinical mismatch** — minimization + conflicting / mistrusted clinical narrative.

4) QoL panel — lifestyle_impacts; `screen_time` and `outdoors` are omitted so x labels stay readable.

**Posts and comments are merged** — each bar is the sum of matching post rows
and matching comment rows (no split by source).

Uses jacob_folder data helpers:
  - reddit_scrapping.config.RedditResearchConfig

Usage (from repo root):
  VIRTUOUS/floater-simulation-service/.venv/bin/python \\
    ankitgupta/semantic_analysis_viz/grouped_trends_graph.py
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JACOB_RS_ROOT = REPO_ROOT / "jacob_folder" / "reddit_scrapping"
if str(JACOB_RS_ROOT) not in sys.path:
    sys.path.insert(0, str(JACOB_RS_ROOT))

MPL_CACHE = REPO_ROOT / "ankitgupta" / "semantic_analysis_viz" / ".mpl_cache"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reddit_scrapping.config import RedditResearchConfig

# 100% larger = 2× default sizes for axis labels, tick text, and numeric ticks.
_FONT_SCALE = 2.0


def _apply_larger_chart_fonts() -> None:
    base = matplotlib.rcParams.get("font.size")
    if not isinstance(base, (int, float)):
        base = 10.0
    fs = float(base) * _FONT_SCALE
    matplotlib.rcParams.update(
        {
            "font.size": fs,
            "axes.labelsize": fs,
            "xtick.labelsize": fs,
            "ytick.labelsize": fs,
        }
    )

# Merged: anxiety, depression, and common co-occurring distress / mood language.
_MENTAL_HEALTH = re.compile(
    r"\b("
    # anxiety / fear / stress
    r"anxious|anxiety|panic|panic attacks?|worried|worry|worrying|"
    r"overwhelm|overwhelmed|on edge|nervous|"
    r"stress|stressed|stressor|"
    r"ptsd|trauma|intrusive thought|"
    # depression / low mood
    r"depressed|depression|hopeless|hopelessness|"
    r"suicid|suicidal|want to die|wants to die|don't want to live|do not want to live|"
    r"end my life|kill myself|"
    r"crying|cry myself|tearful|sobbing|grief|"
    r"worthless|empty inside|numb|can't go on|cannot go on|"
    # isolation (often grouped with anxiety/depression in patient narratives)
    r"feel alone|feeling alone|so alone|lonely|loneliness|isolated|"
    r"no one understands|nobody understands|"
    # generic suffering / mental health
    r"suffering|struggling|struggle with|mental health|nervous breakdown|breakdown|"
    r"can't cope|cannot cope|giving up|given up|"
    r"ruining my life|ruined my life|quality of life"
    r")\b",
    re.IGNORECASE,
)

_DISMISSAL = re.compile(
    r"\b("
    r"normal|everyone has|you'll get used|get used to|just ignore|"
    r"nothing wrong|you're fine|stop worrying|in your head|"
    r"it's all in your head|you're overthinking|just anxiety|"
    r"doctor said|ophthalmologist said|they said it was normal|dismissed|"
    r"brush(?:ed)? off|not taken seriously|doesn't believe|don't believe me"
    r")\b",
    re.IGNORECASE,
)

_CLINICAL_MISMATCH = re.compile(
    r"\b("
    r"second opinion|different doctor|conflicting advice|doctor said|surgeon said|"
    r"specialist said|er said|urgent care said|one doctor|another doctor|"
    r"was told|they told me|misdiagnos|wrong diagnosis|not sure who to trust|"
    r"internet says|reddit says|research says|studies say|"
    r"doesn't match|does not match|contradict|confused about|mixed messages"
    r")\b",
    re.IGNORECASE,
)

# Baseline: user is discussing the floater / vitreous topic.
_FLOATERS_TOPIC = re.compile(
    r"\b(floaters?|eye floaters|vitreous|vitreous opacity|opacities)\b",
    re.IGNORECASE,
)

CLINICAL_PATTERNS: list[re.Pattern[str]] = [_DISMISSAL, _CLINICAL_MISMATCH]

QOL_LABELS = [
    "hobbies",
    "work",
    "reading",
    "screen_time",
    "outdoors",
    "driving",
    "sleep",
]

# Dropped from the right-hand chart only (keeps five bars; labels less crowded).
_QOL_CHART_EXCLUDE = frozenset({"screen_time", "outdoors"})


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _row_matches_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text or "") for p in patterns)


def _count_bucket(
    rows: list[dict[str, str]], text_field: str, patterns: list[re.Pattern[str]]
) -> int:
    return sum(
        1
        for row in rows
        if _row_matches_any(row.get(text_field) or "", patterns)
    )


def _count_floaters_no_mental_health(
    rows: list[dict[str, str]], text_field: str
) -> int:
    """Control: mentions floaters/vitreous but no merged mental-health hit."""
    n = 0
    for row in rows:
        text = row.get(text_field) or ""
        if not _FLOATERS_TOPIC.search(text):
            continue
        if _MENTAL_HEALTH.search(text):
            continue
        n += 1
    return n


def _count_pipe_label(rows: list[dict[str, str]], field: str, label: str) -> int:
    n = 0
    for row in rows:
        raw = row.get(field) or ""
        parts = {p.strip() for p in raw.split("|") if p.strip()}
        if label in parts:
            n += 1
    return n


def _filter_qol_for_chart(
    labels: list[str], totals: list[int]
) -> tuple[list[str], list[int]]:
    """Keep QoL bars in `QOL_LABELS` order, minus `_QOL_CHART_EXCLUDE`."""
    out_l: list[str] = []
    out_t: list[int] = []
    for lab, tot in zip(labels, totals, strict=True):
        if lab in _QOL_CHART_EXCLUDE:
            continue
        out_l.append(lab)
        out_t.append(tot)
    return out_l, out_t


def _bar_combined(
    ax: plt.Axes,
    x_labels: list[str],
    values: list[int],
    ylabel: str,
) -> None:
    x = np.arange(len(x_labels))
    width = 0.55
    ax.bar(x, values, width, color="black", edgecolor="black", linewidth=0.6)
    ax.set_xticks(x)
    fs = float(matplotlib.rcParams["font.size"])
    ax.set_xticklabels(x_labels, rotation=0, ha="center", color="black", fontsize=fs)
    ax.set_ylabel(ylabel, color="black", fontsize=fs)
    ax.tick_params(axis="both", colors="black", labelsize=fs)
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("black")
    ax.spines["bottom"].set_color("black")


def main() -> None:
    config = RedditResearchConfig(data_dir=JACOB_RS_ROOT / "data")
    post_csv = config.processed_dir / "post_analysis.csv"
    comment_csv = config.processed_dir / "comment_analysis.csv"

    post_rows = _load_rows(post_csv)
    comment_rows = _load_rows(comment_csv)

    psych_labels = [
        "Control:\nfloaters as a topic",
        "Mental health\nAnxiety\nDepression",
        "Dismissal + clinical\nmismatch",
    ]
    post_psych = [
        _count_floaters_no_mental_health(post_rows, "text"),
        _count_bucket(post_rows, "text", [_MENTAL_HEALTH]),
        _count_bucket(post_rows, "text", CLINICAL_PATTERNS),
    ]
    comment_psych = [
        _count_floaters_no_mental_health(comment_rows, "body"),
        _count_bucket(comment_rows, "body", [_MENTAL_HEALTH]),
        _count_bucket(comment_rows, "body", CLINICAL_PATTERNS),
    ]

    post_qol = [_count_pipe_label(post_rows, "lifestyle_impacts", lab) for lab in QOL_LABELS]
    comment_qol = [
        _count_pipe_label(comment_rows, "lifestyle_impacts", lab) for lab in QOL_LABELS
    ]

    psych_total = [a + b for a, b in zip(post_psych, comment_psych, strict=True)]
    qol_total = [a + b for a, b in zip(post_qol, comment_qol, strict=True)]
    qol_labels_plot, qol_totals_plot = _filter_qol_for_chart(QOL_LABELS, qol_total)

    _apply_larger_chart_fonts()
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.patch.set_facecolor("white")

    _bar_combined(
        axes[0],
        psych_labels,
        psych_total,
        ylabel="Row count (posts + comments)",
    )
    _bar_combined(
        axes[1],
        qol_labels_plot,
        qol_totals_plot,
        ylabel="Rows tagged (posts + comments)",
    )

    fig.tight_layout(rect=(0, 0.10, 1, 1))

    out_dir = REPO_ROOT / "ankitgupta" / "semantic_analysis_viz"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "grouped_symptoms_trends.png"
    fig.savefig(out_path, dpi=220, facecolor=fig.get_facecolor())
    print(f"Saved grouped graph: {out_path}")


if __name__ == "__main__":
    main()
