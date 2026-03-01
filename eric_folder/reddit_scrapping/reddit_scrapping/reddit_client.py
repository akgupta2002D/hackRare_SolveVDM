from __future__ import annotations

import random
import time
from typing import Any

import requests


class RedditClient:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout_s: int = 20,
        max_retries: int = 3,
        backoff_base_s: float = 1.5,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        self.session = session or requests.Session()

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"User-Agent": self.user_agent}
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout_s,
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}",
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                sleep_s = (self.backoff_base_s ** (attempt - 1)) + random.random()
                time.sleep(sleep_s)

        raise RuntimeError(
            f"Failed to fetch {url} after {self.max_retries} retries: {last_error}"
        )
