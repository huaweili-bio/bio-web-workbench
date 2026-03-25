"""HTTP helpers local to the NCBI gene package."""

from __future__ import annotations

import http.client
import json
import time
from typing import Any
from urllib import error, request


DEFAULT_USER_AGENT = "bio-script-ncbi/1.0"


class RemoteServiceError(RuntimeError):
    """Raised when the NCBI service cannot be queried safely."""


class HttpClient:
    """Small retrying HTTP client built on urllib."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 60.0,
        max_retries: int = 4,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._opener = request.build_opener()

        headers = [
            ("User-Agent", user_agent),
            ("Accept", "*/*"),
            ("Connection", "close"),
        ]
        for key, value in (extra_headers or {}).items():
            headers.append((key, value))
        self._opener.addheaders = headers

    def _read_bytes(self, url: str) -> bytes:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with self._opener.open(url, timeout=self.timeout) as response:
                    return response.read()
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

    def read_text(self, url: str) -> str:
        return self._read_bytes(url).decode("utf-8", errors="replace")

    def read_json(self, url: str) -> dict[str, Any]:
        try:
            payload = json.loads(self.read_text(url))
        except json.JSONDecodeError as exc:
            raise RemoteServiceError(f"Response from {url} is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise RemoteServiceError(f"Response from {url} is not a JSON object.")
        return payload
