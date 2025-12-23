import os
import threading
import time

class RateLimiter:
    """A simple token-bucket rate limiter.

    Rate configured via MAX_REQS_PER_MIN env var (default 120).
    """

    def __init__(self, max_req_per_min: int = None):
        if max_req_per_min is None:
            env = os.getenv('MAX_REQS_PER_MIN')
            max_req_per_min = int(env) if env else 120
        self.max_req_per_min = max_req_per_min
        self.capacity = self.max_req_per_min
        # Start conservatively: allow a single immediate token to avoid large bursts
        self.tokens = min(1.0, float(self.capacity))
        self.fill_rate = self.max_req_per_min / 60.0  # tokens per second
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def _add_tokens(self):
        now = time.monotonic()
        elapsed = now - self.last
        if elapsed <= 0:
            return
        with self.lock:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            self.last = now

    def get_tokens(self) -> float:
        self._add_tokens()
        return self.tokens

    def try_acquire(self) -> bool:
        self._add_tokens()
        with self.lock:
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def wait_for_token(self, timeout: float = None) -> bool:
        """Block until a token is available or timeout (seconds) passes. Returns True if token acquired."""
        start = time.monotonic()
        while True:
            if self.try_acquire():
                return True
            if timeout is not None and (time.monotonic() - start) >= timeout:
                return False
            # Sleep a short while proportional to refill time
            time.sleep(max(0.01, 1.0 / max(1.0, self.fill_rate)))
