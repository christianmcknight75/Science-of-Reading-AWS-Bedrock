"""Per-user sliding-window rate limit. In memory: per instance, which is enough for the PoC."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self, max_calls: int, window_s: float = 60.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max = max_calls
        self._window = window_s
        self._clock = clock
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self._clock()
        q = self._calls[key]
        while q and now - q[0] >= self._window:
            q.popleft()
        if len(q) >= self._max:
            return False
        q.append(now)
        return True
