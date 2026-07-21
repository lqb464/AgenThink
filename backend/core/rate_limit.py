import time
from collections import defaultdict, deque


class RateLimiter:
    """Simple sliding-window rate limiter (in-memory)."""

    def __init__(self, max_calls: int = 30, time_window_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period = time_window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str = "global") -> bool:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self.period:
            window.popleft()
        if len(window) >= self.max_calls:
            return False
        window.append(now)
        return True


rate_limiter = RateLimiter()
