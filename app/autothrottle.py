import threading
import time

from .metrics import increment


class AutoThrottle:
    """Automatic throttling based on recent 429 errors.

    - threshold: number of 429s within window_seconds to trigger throttling
    - window_seconds: timeframe to consider recent 429s
    - cooldown_seconds: how long to keep reduced capacity before restoring
    - reduction_factor: multiply capacity by this factor when throttled
    """

    def __init__(self, rate_limiter, threshold: int = 5, window_seconds: int = 60, cooldown_seconds: int = 300, reduction_factor: float = 0.5, telegram_thread=None):
        self.rate_limiter = rate_limiter
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.reduction_factor = reduction_factor
        self.telegram_thread = telegram_thread
        self.lock = threading.Lock()
        self._events = []  # list of epoch seconds for recent 429s
        self._throttled = False
        self._original_capacity = None
        self._reset_timer = None

    def _now(self):
        return time.time()

    def record_429(self):
        now = self._now()
        with self.lock:
            self._events.append(now)
            # purge old
            cutoff = now - self.window_seconds
            self._events = [t for t in self._events if t >= cutoff]

            if not self._throttled and len(self._events) >= self.threshold:
                # Trigger throttling
                self._throttle()

    def _throttle(self):
        if self.rate_limiter is None:
            return
        self._throttled = True
        self._original_capacity = self.rate_limiter.capacity
        new_capacity = max(1, int(self.rate_limiter.capacity * self.reduction_factor))
        self.rate_limiter.capacity = new_capacity
        self.rate_limiter.tokens = min(self.rate_limiter.tokens, float(new_capacity))

        # schedule restore
        if self._reset_timer and self._reset_timer.is_alive():
            self._reset_timer.cancel()
        self._reset_timer = threading.Timer(self.cooldown_seconds, self._restore)
        self._reset_timer.daemon = True
        self._reset_timer.start()

        increment('autothrottle_count')
        msg = f"⚠️ AutoThrottle triggered: 429s >= {self.threshold} in {self.window_seconds}s. Capacity {self._original_capacity} -> {new_capacity} for {self.cooldown_seconds}s"
        print(msg)
        if self.telegram_thread:
            try:
                self.telegram_thread.send(msg)
            except Exception as e:
                print(f"[AutoThrottle] Telegram send failed: {e}")

    def _restore(self):
        with self.lock:
            if not self._throttled:
                return
            try:
                self.rate_limiter.capacity = self._original_capacity
                self.rate_limiter.tokens = min(self.rate_limiter.tokens, float(self._original_capacity))
            except Exception as e:
                print(f"[AutoThrottle] restore failed: {e}")
            self._throttled = False
            self._events = []
            msg = f"✅ AutoThrottle restored capacity to {self._original_capacity}"
            print(msg)
            if self.telegram_thread:
                try:
                    self.telegram_thread.send(msg)
                except Exception as e:
                    print(f"[AutoThrottle] Telegram send failed: {e}")

    def stop(self):
        if self._reset_timer and self._reset_timer.is_alive():
            self._reset_timer.cancel()
