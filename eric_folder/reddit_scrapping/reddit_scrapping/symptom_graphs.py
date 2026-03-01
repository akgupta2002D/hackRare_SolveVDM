from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from pathlib import Path

from .config import RedditResearchConfig
from .io_utils import ensure_dir, read_json

# Categorized phrase banks to capture not just symptoms, but patient impact and care patterns.
CATEGORIZED_PATTERNS: dict[str, dict[str, list[re.Pattern[str]]]] = {
    "symptoms": {
        "eye floaters": [re.compile(r"\beye floaters?\b", re.IGNORECASE)],
        "floaters": [re.compile(r"\bfloaters?\b", re.IGNORECASE)],
        "flashes": [re.compile(r"\bflashes?\b", re.IGNORECASE)],
        "light sensitivity": [
            re.compile(r"\blight sensitivity\b", re.IGNORECASE),
            re.compile(r"\bphotophobia\b", re.IGNORECASE),
            re.compile(r"\bbright light\b", re.IGNORECASE),
        ],
        "blurry vision": [
            re.compile(r"\bblurry vision\b", re.IGNORECASE),
            re.compile(r"\bblurred vision\b", re.IGNORECASE),
        ],
        "visual snow": [re.compile(r"\bvisual snow\b", re.IGNORECASE)],
        "eye pain": [
            re.compile(r"\beye pain\b", re.IGNORECASE),
            re.compile(r"\beyes hurt\b", re.IGNORECASE),
        ],
        "eye pressure": [
            re.compile(r"\beye pressure\b", re.IGNORECASE),
            re.compile(r"\bpressure\b", re.IGNORECASE),
        ],
        "black spots/dots": [
            re.compile(r"\bblack spots?\b", re.IGNORECASE),
            re.compile(r"\bblack dots?\b", re.IGNORECASE),
            re.compile(r"\bdark dots?\b", re.IGNORECASE),
        ],
        "cobwebs/strings": [
            re.compile(r"\bcobwebs?\b", re.IGNORECASE),
            re.compile(r"\bstrings?\b", re.IGNORECASE),
            re.compile(r"\bthread-like\b", re.IGNORECASE),
        ],
        "haze/cloudy vision": [
            re.compile(r"\bhaze\b", re.IGNORECASE),
            re.compile(r"\bcloudy vision\b", re.IGNORECASE),
        ],
        "retinal tear concern": [re.compile(r"\bretinal tear\b", re.IGNORECASE)],
        "retinal detachment concern": [
            re.compile(r"\bretinal detachment\b", re.IGNORECASE)
        ],
    },
    "daily_life_impact": {
        "anxiety/distress": [
            re.compile(r"\banxiety\b", re.IGNORECASE),
            re.compile(r"\banxious\b", re.IGNORECASE),
            re.compile(r"\bpanic\b", re.IGNORECASE),
            re.compile(r"\bstress(?:ed)?\b", re.IGNORECASE),
        ],
        "depression/hopelessness": [
            re.compile(r"\bdepression\b", re.IGNORECASE),
            re.compile(r"\bdepressed\b", re.IGNORECASE),
            re.compile(r"\bhopeless\b", re.IGNORECASE),
            re.compile(r"\bsuicidal\b", re.IGNORECASE),
        ],
        "work impact": [
            re.compile(r"\b(can't|cannot|hard to)\s+work\b", re.IGNORECASE),
            re.compile(r"\bmy job\b", re.IGNORECASE),
            re.compile(r"\bwork\b", re.IGNORECASE),
            re.compile(r"\boffice\b", re.IGNORECASE),
        ],
        "driving impact": [
            re.compile(r"\b(can't|cannot|hard to)\s+drive\b", re.IGNORECASE),
            re.compile(r"\bdriving\b", re.IGNORECASE),
        ],
        "screen use impact": [
            re.compile(r"\b(can't|cannot|hard to)\s+(use )?(screens?|computer|monitor|phone)\b", re.IGNORECASE),
            re.compile(r"\bscreens?\b", re.IGNORECASE),
            re.compile(r"\bmonitor\b", re.IGNORECASE),
        ],
        "reading impact": [
            re.compile(r"\b(can't|cannot|hard to)\s+read\b", re.IGNORECASE),
            re.compile(r"\breading\b", re.IGNORECASE),
        ],
        "outdoor/light avoidance": [
            re.compile(r"\b(can't|cannot|avoid)\s+go(ing)?\s+outside\b", re.IGNORECASE),
            re.compile(r"\boutside\b", re.IGNORECASE),
            re.compile(r"\bsunlight\b", re.IGNORECASE),
        ],
        "sleep impact": [
            re.compile(r"\bsleep\b", re.IGNORECASE),
            re.compile(r"\binsomnia\b", re.IGNORECASE),
            re.compile(r"\bsleepless\b", re.IGNORECASE),
        ],
        "quality of life impact": [
            re.compile(r"\bquality of life\b", re.IGNORECASE),
            re.compile(r"\bcan'?t enjoy\b", re.IGNORECASE),
            re.compile(r"\blife is ruined\b", re.IGNORECASE),
        ],
    },
    "doctor_feedback": {
        "reassurance (nothing serious)": [
            re.compile(r"\bnothing (serious|wrong)\b", re.IGNORECASE),
            re.compile(r"\bnormal\b", re.IGNORECASE),
            re.compile(r"\bbenign\b", re.IGNORECASE),
            re.compile(r"\bjust ignore\b", re.IGNORECASE),
            re.compile(r"\bbrain will adapt\b", re.IGNORECASE),
        ],
        "urgency warning": [
            re.compile(r"\bemergency\b", re.IGNORECASE),
            re.compile(r"\burgent\b", re.IGNORECASE),
            re.compile(r"\bgo to (the )?(er|ed)\b", re.IGNORECASE),
            re.compile(r"\bget checked immediately\b", re.IGNORECASE),
        ],
        "diagnosis mentions": [
            re.compile(r"\bpvd\b", re.IGNORECASE),
            re.compile(r"\bposterior vitreous detachment\b", re.IGNORECASE),
            re.compile(r"\bretinal tear\b", re.IGNORECASE),
            re.compile(r"\bretinal detachment\b", re.IGNORECASE),
            re.compile(r"\bvitreous (change|detachment)\b", re.IGNORECASE),
        ],
        "uncertainty/conflicting advice": [
            re.compile(r"\bnot sure\b", re.IGNORECASE),
            re.compile(r"\bunclear\b", re.IGNORECASE),
            re.compile(r"\bconfused\b", re.IGNORECASE),
            re.compile(r"\bsecond opinion\b", re.IGNORECASE),
            re.compile(r"\bdifferent doctor\b", re.IGNORECASE),
        ],
    },
    "recurring_patterns": {
        "diagnostic delay": [
            re.compile(r"\b(waited|waiting)\s+(months?|years?)\b", re.IGNORECASE),
            re.compile(r"\bfinally diagnosed\b", re.IGNORECASE),
            re.compile(r"\bdelayed diagnosis\b", re.IGNORECASE),
        ],
        "confusion about urgency": [
            re.compile(r"\bdidn'?t know.*emergency\b", re.IGNORECASE),
            re.compile(r"\bunsure if.*emergency\b", re.IGNORECASE),
            re.compile(r"\bwhen to worry\b", re.IGNORECASE),
        ],
        "fear vs advice mismatch": [
            re.compile(r"\bdoctor.*(normal|fine|nothing wrong).*but\b", re.IGNORECASE),
            re.compile(r"\btold me.*ignore.*but\b", re.IGNORECASE),
            re.compile(r"\bstill scared\b", re.IGNORECASE),
        ],
        "dismissed by clinician": [
            re.compile(r"\blaughed off\b", re.IGNORECASE),
            re.compile(r"\bnot taken seriously\b", re.IGNORECASE),
            re.compile(r"\bdismiss(ed|ive)\b", re.IGNORECASE),
        ],
    },
}


def _collect_text_corpus(raw_threads: list[dict], include_comments: bool) -> list[str]:
    corpus: list[str] = []
    for thread in raw_threads:
        title = str(thread.get("title") or "").strip()
        selftext = str(thread.get("selftext") or "").strip()
        combined = " ".join(part for part in [title, selftext] if part).strip()
        if combined:
            corpus.append(combined)

        if include_comments:
            comments = thread.get("comments") or []
            for comment in comments:
                body = str(comment.get("body") or "").strip()
                if body:
                    corpus.append(body)
    return corpus


def _count_categorized_phrases(corpus: list[str]) -> dict[str, Counter[str]]:
    counts_by_category: dict[str, Counter[str]] = {
        category: Counter() for category in CATEGORIZED_PATTERNS
    }

    for text in corpus:
        for category, phrase_map in CATEGORIZED_PATTERNS.items():
            for phrase, patterns in phrase_map.items():
                matches = 0
                for pattern in patterns:
                    matches += len(pattern.findall(text))
                if matches:
                    counts_by_category[category][phrase] += matches

    return counts_by_category


def _rank_counts(
    counts_by_category: dict[str, Counter[str]],
    top_n_per_category: int,
) -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    for category, counter in counts_by_category.items():
        for phrase, count in counter.most_common(max(1, top_n_per_category)):
            rows.append((category, phrase, count))
    rows.sort(key=lambda item: item[2], reverse=True)
    return rows


def _write_counts_csv(path: Path, ranked_rows: list[tuple[str, str, int]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["category", "phrase", "count"])
        for category, phrase, count in ranked_rows:
            writer.writerow([category, phrase, count])


def _write_counts_json(path: Path, ranked_rows: list[tuple[str, str, int]]) -> None:
    ensure_dir(path.parent)
    payload = [
        {"category": category, "phrase": phrase, "count": count}
        for category, phrase, count in ranked_rows
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_bar_chart(path: Path, ranked_rows: list[tuple[str, str, int]]) -> bool:
    # Lazy import keeps CSV/JSON generation reliable in environments where matplotlib
    # cache/font setup is restricted.
    try:
        os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
        os.environ.setdefault("XDG_CACHE_HOME", "/tmp")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    try:
        ensure_dir(path.parent)
        labels = [f"{cat}: {phrase}" for cat, phrase, _ in ranked_rows]
        values = [count for _, _, count in ranked_rows]

        fig_h = max(6, min(18, 0.42 * len(labels)))
        plt.figure(figsize=(12, fig_h))
        bars = plt.barh(labels[::-1], values[::-1], color="#2f6db2")
        plt.xlabel("Mentions")
        plt.title("Floater Reddit: Common Phrase Signals by Category")
        plt.tight_layout()

        for bar in bars:
            width = bar.get_width()
            plt.text(width + 0.5, bar.get_y() + bar.get_height() / 2, f"{int(width)}", va="center")

        plt.savefig(path, dpi=200)
        plt.close()
        return True
    except Exception:
        return False


def run_symptom_phrase_graph(
    config: RedditResearchConfig,
    input_path: Path | None = None,
    output_prefix: str = "symptom_phrase_counts",
    top_n: int = 12,
    include_comments: bool = True,
) -> dict[str, Path | None]:
    source_path = input_path or (config.raw_dir / "reddit_threads.json")
    raw_threads = read_json(source_path)

    corpus = _collect_text_corpus(raw_threads, include_comments=include_comments)
    counts_by_category = _count_categorized_phrases(corpus)
    ranked_rows = _rank_counts(counts_by_category, top_n_per_category=top_n)

    csv_path = config.processed_dir / f"{output_prefix}.csv"
    json_path = config.processed_dir / f"{output_prefix}.json"
    png_path = config.reports_dir / f"{output_prefix}.png"

    _write_counts_csv(csv_path, ranked_rows)
    _write_counts_json(json_path, ranked_rows)
    wrote_chart = _write_bar_chart(png_path, ranked_rows)

    return {
        "csv": csv_path,
        "json": json_path,
        "png": png_path if wrote_chart else None,
    }
