"""
writers.py

Output layer.

Responsibilities:
- Convert domain objects into file formats.
- Handle JSON / CSV serialization.
- No knowledge of Reddit or HTTP.
"""

import csv
import json
from dataclasses import asdict
from typing import List

from fetch_posts import RedditPost


def to_json(posts: List[RedditPost]) -> str:
    """
    Convert list of RedditPost objects into JSON string.
    """
    return json.dumps(
        [asdict(p) for p in posts],
        ensure_ascii=False,
        indent=2,
    )


def write_json_file(posts: List[RedditPost], filepath: str) -> None:
    """
    Write posts to JSON file.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(to_json(posts))


def write_csv_file(posts: List[RedditPost], filepath: str) -> None:
    """
    Write posts to CSV file.

    Field order is explicitly controlled for stability.
    """
    fieldnames = [
        "id", "title", "author", "created_utc",
        "created_iso", "score", "num_comments",
        "permalink", "selftext"
    ]

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for p in posts:
            writer.writerow(asdict(p))