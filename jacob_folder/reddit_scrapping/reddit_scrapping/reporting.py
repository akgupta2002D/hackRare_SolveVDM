from __future__ import annotations

from pathlib import Path

from .io_utils import ensure_dir


def write_quotebook(
    path: Path,
    summary: dict[str, object],
    themes: list[dict[str, object]],
    quotes: list[dict[str, object]],
    anonymize_usernames: bool = False,
) -> None:
    ensure_dir(path.parent)
    lines: list[str] = [
        "# Eye Floater Reddit Quotebook",
        "",
        "## Snapshot",
        "",
        f"- Threads analyzed: {summary['thread_count']}",
        f"- Comments analyzed: {summary['comment_count']}",
        f"- Quote categories: {summary['quote_category_counts']}",
        f"- Age mentions captured: {summary['age_mentions_count']}",
        f"- Average age mention: {summary['average_age_mention']}",
        "",
        "## Theme Clusters",
        "",
    ]

    if themes:
        for theme in themes:
            terms = ", ".join(theme["top_terms"])
            lines.append(f"- Theme {theme['theme_id']}: {terms} ({theme['size']} posts)")
    else:
        lines.append("- Not enough documents for clustering.")

    emotional_quotes = [quote for quote in quotes if quote.get("quote_category") == "emotional_testimony"]
    other_quotes = [quote for quote in quotes if quote.get("quote_category") != "emotional_testimony"]

    lines.extend(["", "## Emotional Testimonies", ""])
    if emotional_quotes:
        for index, quote in enumerate(emotional_quotes, start=1):
            _append_quote_block(lines, index, quote, anonymize_usernames)
    else:
        lines.append("- No emotional testimonies met the threshold in this run.")

    lines.extend(["", "## Other Relevant Quotes", ""])
    if other_quotes:
        for index, quote in enumerate(other_quotes, start=1):
            _append_quote_block(lines, index, quote, anonymize_usernames)
    else:
        lines.append("- No additional quotes selected.")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _append_quote_block(
    lines: list[str],
    index: int,
    quote: dict[str, object],
    anonymize_usernames: bool,
) -> None:
    author = str(quote["author"])
    if anonymize_usernames:
        author = f"user_{index:02d}"
    lines.extend(
        [
            f"### Quote {index}",
            "",
            f"- Author: {author}",
            f"- Kind: {quote['kind']}",
            f"- Category: {quote['quote_category']}",
            f"- Emotional score: {quote['emotional_score']}",
            f"- Severity: {quote['severity_label']}",
            f"- Sentiment: {quote['sentiment_label']}",
            f"- Link: {quote['permalink']}",
            "",
            f"> {quote['quote']}",
            "",
        ]
    )
