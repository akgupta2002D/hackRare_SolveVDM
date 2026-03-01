from __future__ import annotations

from pathlib import Path
from typing import Any

from .analyze import analyze_threads
from .collect import collect_threads
from .config import RedditResearchConfig
from .io_utils import read_json, write_csv, write_json
from .models import RedditComment, RedditThread
from .reddit_client import RedditClient
from .reporting import write_quotebook


def build_client(config: RedditResearchConfig) -> RedditClient:
    return RedditClient(
        base_url=config.base_url,
        user_agent=config.user_agent,
        timeout_s=config.timeout_s,
        max_retries=config.max_retries,
        backoff_base_s=config.backoff_base_s,
    )


def run_collection(
    config: RedditResearchConfig,
    limit: int | None = None,
    comments_per_post: int | None = None,
) -> Path:
    client = build_client(config)
    threads = collect_threads(
        client=client,
        subreddits=config.subreddits,
        search_queries=config.search_queries,
        listing_sorts=config.listing_sorts,
        limit=limit or config.default_limit,
        comments_per_post=comments_per_post or config.default_comments_per_post,
    )
    output_path = config.raw_dir / "reddit_threads.json"
    write_json(output_path, [thread.to_dict() for thread in threads])
    return output_path


def run_analysis(
    config: RedditResearchConfig,
    input_path: Path | None = None,
    anonymize_usernames: bool = False,
) -> dict[str, Path]:
    source_path = input_path or (config.raw_dir / "reddit_threads.json")
    raw_threads = read_json(source_path)
    threads = [_thread_from_dict(item) for item in raw_threads]
    outputs = analyze_threads(threads, max_themes=config.max_themes)

    post_csv = config.processed_dir / "post_analysis.csv"
    comment_csv = config.processed_dir / "comment_analysis.csv"
    theme_json = config.processed_dir / "theme_summary.json"
    summary_json = config.reports_dir / "summary.json"
    quotebook_md = config.reports_dir / "quotebook.md"

    write_csv(post_csv, outputs["post_rows"])
    write_csv(comment_csv, outputs["comment_rows"])
    write_json(theme_json, outputs["themes"])
    write_json(summary_json, outputs["summary"])
    write_quotebook(
        quotebook_md,
        summary=outputs["summary"],
        themes=outputs["themes"],
        quotes=outputs["quotes"],
        anonymize_usernames=anonymize_usernames,
    )

    return {
        "post_csv": post_csv,
        "comment_csv": comment_csv,
        "theme_json": theme_json,
        "summary_json": summary_json,
        "quotebook_md": quotebook_md,
    }


def _thread_from_dict(payload: dict[str, Any]) -> RedditThread:
    comments = [
        RedditComment(
            id=str(item.get("id") or ""),
            author=str(item.get("author") or "[deleted]"),
            body=str(item.get("body") or ""),
            created_utc=int(item.get("created_utc") or 0),
            score=int(item.get("score") or 0),
            depth=int(item.get("depth") or 0),
            permalink=str(item.get("permalink") or ""),
            parent_id=str(item.get("parent_id") or ""),
        )
        for item in payload.get("comments", [])
    ]
    return RedditThread(
        id=str(payload.get("id") or ""),
        subreddit=str(payload.get("subreddit") or ""),
        title=str(payload.get("title") or ""),
        author=str(payload.get("author") or "[deleted]"),
        selftext=str(payload.get("selftext") or ""),
        created_utc=int(payload.get("created_utc") or 0),
        score=int(payload.get("score") or 0),
        num_comments=int(payload.get("num_comments") or 0),
        permalink=str(payload.get("permalink") or ""),
        source=str(payload.get("source") or ""),
        query=str(payload.get("query") or ""),
        comments=comments,
    )
