from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests


@dataclass(frozen=True)
class FetchResult:
    text: str
    retrieved_at: str
    status_code: int | None
    from_cache: bool


class CachedHttpClient:
    """Small polite HTTP client with durable text caching and retry metadata."""

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        delay: float = 1.5,
        retries: int = 3,
        timeout: float = 30,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if delay < 0 or retries < 1 or timeout <= 0:
            raise ValueError("delay must be >= 0, retries >= 1, and timeout > 0")
        self.session = session or requests.Session()
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.sleep = sleep

    @staticmethod
    def metadata_path(cache_path: Path) -> Path:
        return cache_path.with_suffix(cache_path.suffix + ".meta.json")

    def fetch_text(self, url: str, cache_path: Path, *, force: bool = False) -> FetchResult:
        metadata_path = self.metadata_path(cache_path)
        if cache_path.exists() and not force:
            try:
                metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
            except (json.JSONDecodeError, OSError):
                metadata = {}
            retrieved_at = metadata.get("retrieved_at") or datetime.fromtimestamp(
                cache_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
            return FetchResult(
                text=cache_path.read_text(encoding="utf-8", errors="replace"),
                retrieved_at=retrieved_at,
                status_code=metadata.get("status_code"),
                from_cache=True,
            )

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                retrieved_at = datetime.now(timezone.utc).isoformat()
                text = response.text
                metadata = {
                    "source_url": url,
                    "retrieved_at": retrieved_at,
                    "status_code": response.status_code,
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                }
                temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
                temp_meta = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
                temp_path.write_text(text, encoding="utf-8")
                temp_meta.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                temp_path.replace(cache_path)
                temp_meta.replace(metadata_path)
                if self.delay:
                    self.sleep(self.delay)
                return FetchResult(text, retrieved_at, response.status_code, False)
            except (requests.RequestException, OSError) as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    retry_after = 0.0
                    response = getattr(exc, "response", None)
                    if response is not None:
                        try:
                            retry_after = float(response.headers.get("Retry-After", 0))
                        except (TypeError, ValueError):
                            retry_after = 0.0
                    self.sleep(max(retry_after, self.delay * (2**attempt)))
        raise RuntimeError(f"Failed after {self.retries} attempts: {url}") from last_error
