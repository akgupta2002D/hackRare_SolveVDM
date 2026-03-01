from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RedditResearchConfig:
    base_url: str = "https://www.reddit.com"
    user_agent: str = "floater-research-bot/0.1 by codex"
    timeout_s: int = 20
    max_retries: int = 4
    backoff_base_s: float = 1.5
    subreddits: tuple[str, ...] = ("EyeFloaters",)
    search_queries: tuple[str, ...] = (
        "eye floaters",
        "floaters vision changes",
        "vitreous detachment floaters",
        "sudden floaters flashes",
    )
    listing_sorts: tuple[str, ...] = ("new", "top")
    default_limit: int = 25
    default_comments_per_post: int = 50
    max_themes: int = 6
    data_dir: Path = field(default_factory=lambda: Path("data"))

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"
