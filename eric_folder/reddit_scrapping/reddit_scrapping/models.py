from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RedditComment:
    id: str
    author: str
    body: str
    created_utc: int
    score: int
    depth: int
    permalink: str
    parent_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedditThread:
    id: str
    subreddit: str
    title: str
    author: str
    selftext: str
    created_utc: int
    score: int
    num_comments: int
    permalink: str
    source: str
    query: str
    comments: list[RedditComment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["comments"] = [comment.to_dict() for comment in self.comments]
        return data
