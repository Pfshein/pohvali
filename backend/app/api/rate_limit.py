"""In-memory fixed-window rate limiter.

The MVP runs a single backend instance (APScheduler pins replicas to 1), so a
process-local limiter is sufficient and avoids adding Redis. Keys are opaque
strings (the Telegram id); no IP addresses are stored.
"""

import time
from collections.abc import Callable


class FixedWindowRateLimiter:
    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: float,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._now = now
        self._hits: dict[str, tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        current = self._now()
        window_start, count = self._hits.get(key, (current, 0))

        if current - window_start >= self.window_seconds:
            window_start, count = current, 0

        if count >= self.max_requests:
            self._hits[key] = (window_start, count)
            return False

        self._hits[key] = (window_start, count + 1)
        return True

    def reset(self) -> None:
        self._hits.clear()
