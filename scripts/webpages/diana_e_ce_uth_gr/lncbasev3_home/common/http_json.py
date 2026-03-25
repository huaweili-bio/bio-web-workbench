"""HTTP and JSON helpers local to the DIANA-LncBase v3 webpage package."""

from __future__ import annotations

import http.client
import json
import time
from typing import Any
from urllib import error, request


DEFAULT_USER_AGENT = "bio-script-lncbasev3/1.0"


class RemoteServiceError(RuntimeError):
    """Raised when an upstream webpage or API cannot be queried safely."""


class JsonHttpClient:
    """Small retrying JSON client built on urllib."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        accept: str = "application/json",
        timeout: float = 60.0,
        max_retries: int = 4,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._opener = request.build_opener()

        headers = [
            ("User-Agent", user_agent),
            ("Accept", accept),
            ("Connection", "close"),
        ]
        for key, value in (extra_headers or {}).items():
            headers.append((key, value))
        self._opener.addheaders = headers

    def read_json(self, url: str) -> Any:
        payload = self.read_text(url)
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RemoteServiceError(f"Non-JSON response from {url}: {payload[:400]}") from exc

    def read_text(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with self._opener.open(url, timeout=self.timeout) as response:
                    return response.read().decode("utf-8")
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code >= 500 and attempt < self.max_retries:
                    last_error = exc
                    time.sleep(min(2**attempt, 15))
                    continue
                raise RemoteServiceError(f"HTTP {exc.code} for {url}: {body[:400]}") from exc
            except (error.URLError, TimeoutError, http.client.IncompleteRead, OSError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 15))
                    continue
                raise RemoteServiceError(f"Request failed for {url}: {exc}") from exc

        raise RemoteServiceError(f"Request failed for {url}: {last_error}")
