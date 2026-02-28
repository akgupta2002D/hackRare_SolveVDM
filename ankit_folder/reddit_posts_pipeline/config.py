"""
config.py

Centralized configuration for the Reddit scraper.

Design principle:
- All tunable values live here.
- No hardcoded constants scattered across the codebase.
- Frozen dataclass prevents accidental mutation at runtime.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RedditConfig:
    """
    Immutable configuration container.

    If you want to change defaults (subreddit, retry policy, etc.),
    you do it here and nowhere else.
    """

    # Base Reddit JSON endpoint
    base_url: str = "https://www.reddit.com"

    # Default scraping target
    subreddit: str = "eyefloaters"

    # Sorting mode: new | hot | top | rising
    sort: str = "new"

    # Number of posts to fetch
    limit: int = 10

    # Reddit requires a meaningful User-Agent
    user_agent: str = "eyefloaters-scraper/1.0 (contact: ankit.98.gupta.52@gmail.com)"

    # Networking behavior
    timeout_s: int = 20
    max_retries: int = 4

    # Exponential backoff base (used for retry delay)
    backoff_base_s: float = 1.2