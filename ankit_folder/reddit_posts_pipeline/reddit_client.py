"""
reddit_client.py

Low-level HTTP client for Reddit public JSON endpoints.

Responsibilities:
- Construct HTTP requests
- Apply retry policy
- Handle rate limiting
- Return parsed JSON

It does NOT:
- Know about posts
- Know about business logic
- Know about output formatting

Single responsibility: networking.
"""

import time
import random
from typing import Any, Dict, Optional

import requests


class RedditClient:
    """
    Thin wrapper around requests.Session for Reddit JSON fetching.

    Encapsulates:
    - Retry logic
    - Exponential backoff
    - Rate-limit handling
    """

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout_s: int = 20,
        max_retries: int = 3,
        backoff_base_s: float = 1.5,
        session: Optional[requests.Session] = None,
    ) -> None:
        """
        Initialize the HTTP client.

        Parameters:
            base_url: Root URL for Reddit
            user_agent: Required by Reddit API policy
            timeout_s: HTTP timeout in seconds
            max_retries: How many retry attempts before failing
            backoff_base_s: Base multiplier for exponential backoff
            session: Optional injected session (useful for testing)
        """
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        self.session = session or requests.Session()

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform GET request and return parsed JSON.

        Includes:
        - Retry handling
        - Exponential backoff
        - Rate limit handling (HTTP 429)
        """

        url = f"{self.base_url}{path}"
        headers = {"User-Agent": self.user_agent}

        last_err: Optional[Exception] = None

        # Retry loop
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout_s,
                )

                # Handle transient server / rate errors
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}: transient error",
                        response=response,
                    )

                # Raise for non-200 responses
                response.raise_for_status()

                # Parse JSON safely
                return response.json()

            except (requests.RequestException, ValueError) as e:
                last_err = e

                # If final attempt, break and raise
                if attempt == self.max_retries:
                    break

                # Exponential backoff + jitter
                sleep_s = (self.backoff_base_s ** (attempt - 1)) + random.random()
                time.sleep(sleep_s)

        raise RuntimeError(
            f"Failed to GET {url} after {self.max_retries} retries: {last_err}"
        )