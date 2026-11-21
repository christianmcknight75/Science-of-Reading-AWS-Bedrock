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


class FailureLimiter:
    """Blocks a key after too many recorded failures inside a window (sign-in attempts)."""

    def __init__(
        self, max_failures: int, window_s: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max = max_failures
        self._window = window_s
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        q = self._failures[key]
        now = self._clock()
        while q and now - q[0] >= self._window:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self._max

    def record_failure(self, key: str) -> None:
        self._prune(key).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
