"""
fetch_posts.py

Business logic layer.

Responsibilities:
- Convert raw Reddit JSON into structured domain objects.
- Normalize data.
- Hide Reddit's messy JSON structure from the rest of the codebase.

This module knows:
- What a RedditPost is.
- How to extract it from Reddit JSON.

It does NOT:
- Handle networking.
- Write files.
- Handle CLI.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reddit_client import RedditClient


@dataclass(frozen=True)
class RedditPost:
    """
    Clean domain model representing a Reddit post.

    Using a dataclass:
    - Improves readability
    - Makes data strongly structured
    - Easier to extend later
    """
    id: str
    title: str
    author: str
    created_utc: int
    created_iso: str
    score: int
    num_comments: int
    permalink: str
    selftext: str


def _to_iso(ts_utc: Optional[int]) -> str:
    """
    Convert Unix timestamp to ISO string.
    Keeps time formatting logic isolated.
    """
    if not ts_utc:
        return ""
    return datetime.fromtimestamp(ts_utc, tz=timezone.utc).isoformat()


def fetch_subreddit_posts(
    client: RedditClient,
    subreddit: str,
    sort: str = "new",
    limit: int = 10,
) -> List[RedditPost]:
    """
    Fetch posts from Reddit and return structured RedditPost objects.

    This function:
    - Calls the HTTP client
    - Extracts relevant fields
    - Converts them into typed objects
    """

    path = f"/r/{subreddit}/{sort}.json"
    raw: Dict[str, Any] = client.get_json(path, params={"limit": limit})

    children = raw.get("data", {}).get("children", [])
    posts: List[RedditPost] = []

    for child in children:
        data = child.get("data", {}) or {}

        created_utc = int(data.get("created_utc") or 0)
        permalink_path = data.get("permalink") or ""

        posts.append(
            RedditPost(
                id=str(data.get("id") or ""),
                title=str(data.get("title") or ""),
                author=str(data.get("author") or ""),
                created_utc=created_utc,
                created_iso=_to_iso(created_utc),
                score=int(data.get("score") or 0),
                num_comments=int(data.get("num_comments") or 0),
                permalink="https://www.reddit.com" + permalink_path,
                selftext=str(data.get("selftext") or "").strip(),
            )
        )

    return posts