"""
main.py

Entry point.

Responsibilities:
- Parse CLI arguments
- Construct config + client
- Call business logic
- Trigger output writers

This file wires everything together.
"""

import argparse
from typing import Optional

from config import RedditConfig
from reddit_client import RedditClient
from fetch_posts import fetch_subreddit_posts
from writers import write_json_file, write_csv_file


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Define CLI arguments for flexible runtime configuration.
    """
    parser = argparse.ArgumentParser(
        description="Scrape posts from a subreddit via Reddit public JSON."
    )

    parser.add_argument("--subreddit", help="Subreddit name")
    parser.add_argument("--sort", help="Sort mode: new|hot|top|rising")
    parser.add_argument("--limit", type=int, help="Number of posts")
    parser.add_argument("--out-json", help="Output JSON file path")
    parser.add_argument("--out-csv", help="Output CSV file path")

    return parser


def resolve(value: Optional[str], default: str) -> str:
    """
    Return CLI value if provided, else fallback to config default.
    """
    return value if value is not None else default


def resolve_int(value: Optional[int], default: int) -> int:
    """
    Integer-specific resolver.
    """
    return value if value is not None else default


def main() -> None:
    """
    Program entry point.
    """

    cfg = RedditConfig()
    args = build_arg_parser().parse_args()

    subreddit = resolve(args.subreddit, cfg.subreddit)
    sort = resolve(args.sort, cfg.sort)
    limit = resolve_int(args.limit, cfg.limit)

    # Construct client using config
    client = RedditClient(
        base_url=cfg.base_url,
        user_agent=cfg.user_agent,
        timeout_s=cfg.timeout_s,
        max_retries=cfg.max_retries,
        backoff_base_s=cfg.backoff_base_s,
    )

    # Fetch posts
    posts = fetch_subreddit_posts(
        client=client,
        subreddit=subreddit,
        sort=sort,
        limit=limit,
    )

    # Print simple console summary
    for i, post in enumerate(posts, start=1):
        print(f"{i}. {post.title} ({post.permalink})")

    # Optional file outputs
    if args.out_json:
        write_json_file(posts, args.out_json)

    if args.out_csv:
        write_csv_file(posts, args.out_csv)


if __name__ == "__main__":
    main()