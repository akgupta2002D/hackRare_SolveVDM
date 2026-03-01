from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .models import RedditComment, RedditThread
from .reddit_client import RedditClient

TITLE_SIGNAL_PATTERN = re.compile(
    r"\b(floaters?|vitreous|pvd|posterior vitreous detachment|visual snow|flashes?|retinal|retina)\b",
    re.IGNORECASE,
)
BODY_SIGNAL_PATTERN = re.compile(
    r"\b(floaters?|vitreous|pvd|posterior vitreous detachment|visual snow|flashes?|retinal|retina|ophthalmologist|optometrist|vision)\b",
    re.IGNORECASE,
)
VISION_CHANGE_PATTERN = re.compile(r"\bvision changes?\b", re.IGNORECASE)
EXPERIENCE_PATTERN = re.compile(
    r"\b(i|i'm|ive|i've|my|me|mine)\b",
    re.IGNORECASE,
)


def collect_threads(
    client: RedditClient,
    subreddits: Iterable[str],
    search_queries: Iterable[str],
    listing_sorts: Iterable[str],
    limit: int,
    comments_per_post: int,
) -> list[RedditThread]:
    threads_by_id: dict[str, RedditThread] = {}

    for subreddit in subreddits:
        for sort in listing_sorts:
            path = f"/r/{subreddit}/{sort}.json"
            listing = client.get_json(path, params={"limit": limit})
            for child in listing.get("data", {}).get("children", []):
                if not _is_relevant_post(child.get("data", {}), subreddit_context=subreddit):
                    continue
                thread = _thread_from_listing(
                    child.get("data", {}),
                    source=f"subreddit:{subreddit}:{sort}",
                    query="",
                )
                if thread.id:
                    threads_by_id.setdefault(thread.id, thread)

    for query in search_queries:
        listing = client.get_json(
            "/search.json",
            params={"q": query, "sort": "relevance", "limit": limit, "t": "all"},
        )
        for child in listing.get("data", {}).get("children", []):
            if not _is_relevant_post(child.get("data", {}), search_query=query):
                continue
            thread = _thread_from_listing(
                child.get("data", {}),
                source="global_search",
                query=query,
            )
            if thread.id:
                threads_by_id.setdefault(thread.id, thread)

    threads: list[RedditThread] = []
    for thread in threads_by_id.values():
        comments = fetch_comments(client, thread.subreddit, thread.id, comments_per_post)
        threads.append(
            RedditThread(
                id=thread.id,
                subreddit=thread.subreddit,
                title=thread.title,
                author=thread.author,
                selftext=thread.selftext,
                created_utc=thread.created_utc,
                score=thread.score,
                num_comments=thread.num_comments,
                permalink=thread.permalink,
                source=thread.source,
                query=thread.query,
                comments=comments,
            )
        )

    return sorted(threads, key=lambda thread: thread.created_utc, reverse=True)


def fetch_comments(
    client: RedditClient,
    subreddit: str,
    post_id: str,
    comments_per_post: int,
) -> list[RedditComment]:
    response = client.get_json(
        f"/r/{subreddit}/comments/{post_id}.json",
        params={
            "limit": comments_per_post,
            "depth": 6,
            "sort": "top",
            "raw_json": 1,
        },
    )
    if not isinstance(response, list) or len(response) < 2:
        return []

    listing = response[1].get("data", {}).get("children", [])
    comments: list[RedditComment] = []
    for child in listing:
        comments.extend(_flatten_comment_tree(child, permalink_seed=f"/r/{subreddit}/comments/{post_id}"))
        if len(comments) >= comments_per_post:
            break
    return comments[:comments_per_post]


def _flatten_comment_tree(node: dict[str, Any], permalink_seed: str) -> list[RedditComment]:
    kind = node.get("kind")
    data = node.get("data", {}) or {}
    if kind != "t1":
        return []

    comment = RedditComment(
        id=str(data.get("id") or ""),
        author=str(data.get("author") or "[deleted]"),
        body=str(data.get("body") or "").strip(),
        created_utc=int(data.get("created_utc") or 0),
        score=int(data.get("score") or 0),
        depth=int(data.get("depth") or 0),
        permalink="https://www.reddit.com" + str(data.get("permalink") or permalink_seed),
        parent_id=str(data.get("parent_id") or ""),
    )
    items = [comment]
    replies = data.get("replies")
    if isinstance(replies, dict):
        for child in replies.get("data", {}).get("children", []):
            items.extend(_flatten_comment_tree(child, permalink_seed))
    return items


def _thread_from_listing(data: dict[str, Any], source: str, query: str) -> RedditThread:
    permalink_path = str(data.get("permalink") or "")
    return RedditThread(
        id=str(data.get("id") or ""),
        subreddit=str(data.get("subreddit") or ""),
        title=str(data.get("title") or "").strip(),
        author=str(data.get("author") or "[deleted]"),
        selftext=str(data.get("selftext") or "").strip(),
        created_utc=int(data.get("created_utc") or 0),
        score=int(data.get("score") or 0),
        num_comments=int(data.get("num_comments") or 0),
        permalink="https://www.reddit.com" + permalink_path,
        source=source,
        query=query,
        comments=[],
    )


def _is_relevant_post(
    data: dict[str, Any],
    subreddit_context: str | None = None,
    search_query: str | None = None,
) -> bool:
    subreddit = str(data.get("subreddit") or subreddit_context or "").lower()
    title = str(data.get("title") or "").strip()
    selftext = str(data.get("selftext") or "").strip()
    combined = " ".join(part for part in [title, selftext] if part)

    if subreddit == "eyefloaters":
        return True

    title_hits = len(TITLE_SIGNAL_PATTERN.findall(title))
    body_hits = len(BODY_SIGNAL_PATTERN.findall(combined))
    experience_hits = len(EXPERIENCE_PATTERN.findall(combined))
    vision_change_in_title = bool(VISION_CHANGE_PATTERN.search(title))

    if title_hits >= 1 and body_hits >= 2:
        return True

    if title_hits >= 1 and experience_hits >= 3:
        return True

    if vision_change_in_title and body_hits >= 4 and experience_hits >= 4:
        return True

    if search_query:
        query_terms = [term for term in search_query.lower().split() if len(term) > 3]
        matched_terms = sum(term in combined.lower() for term in query_terms)
        if (title_hits >= 1 or vision_change_in_title) and matched_terms >= max(1, len(query_terms) // 2):
            return True

    return False
