"""HTTP text helpers local to the miRDB webpage package."""

from __future__ import annotations

import http.client
import time
from urllib import error, request


DEFAULT_USER_AGENT = "bio-script-mirdb/1.0"


class RemoteServiceError(RuntimeError):
    """Raised when the miRDB website cannot be queried safely."""


class TextHttpClient:
    """Small retrying text client built on urllib."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        accept: str = "text/html,*/*",
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

    def read_text(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with self._opener.open(url, timeout=self.timeout) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return response.read().decode(charset, errors="replace")
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
