import time
import requests

from app.autothrottle import AutoThrottle
from app.candle_fetcher import CandleFetcher
from app.metrics import reset_metrics, get_metrics


class DummyRateLimiter:
    def __init__(self, capacity=10):
        self.capacity = capacity
        self.tokens = float(capacity)

    def wait_for_token(self, timeout=0):
        # For tests we assume tokens are always available
        return True


class FakeClient:
    BASE_URL = "https://api.test/"
    def _update_rate_limit(self, resp):
        return


class FakeDB:
    def save_candles(self, *args, **kwargs):
        return 0

    def get_latest_candle_timestamp(self, market, interval):
        return None


class FakeResp:
    def __init__(self, status=200, headers=None, json_data=None):
        self.status_code = status
        self.headers = headers or {}
        self._json = json_data or []

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_autothrottle_triggers_and_restores(monkeypatch):
    reset_metrics()

    rl = DummyRateLimiter(capacity=10)
    # Use low thresholds and cooldown for fast test
    # Use a cooldown longer than the fetcher's retry wait so capacity remains reduced until we assert
    at = AutoThrottle(rl, threshold=1, window_seconds=10, cooldown_seconds=1.0, reduction_factor=0.5)

    # Prepare CandleFetcher with our autothrottle
    cf = CandleFetcher(client=FakeClient(), db=FakeDB(), rate_limiter=rl, autothrottle=at)

    # Build a request sequence: first 429 then 200
    responses = [FakeResp(status=429), FakeResp(status=200, json_data=[])]

    def fake_get(url, params=None):
        return responses.pop(0)

    monkeypatch.setattr('requests.get', fake_get)

    # Call _fetch_range which should see a 429 and trigger autothrottle
    cf._fetch_range('BTC-EUR', '1m', limit=1)

    # AutoThrottle should have reduced capacity immediately
    assert rl.capacity == 5
    metrics = get_metrics()
    assert metrics.get('autothrottle_count', 0) == 1

    # Wait for cooldown to expire and restoration to happen
    time.sleep(1.1)
    assert rl.capacity == 10


def test_autothrottle_direct_usage():
    reset_metrics()
    rl = DummyRateLimiter(capacity=8)
    at = AutoThrottle(rl, threshold=3, window_seconds=2, cooldown_seconds=0.1, reduction_factor=0.25)

    # Feed 3 429 records rapidly
    at.record_429()
    at.record_429()
    at.record_429()

    # Should be throttled
    assert rl.capacity == max(1, int(8 * 0.25))
    metrics = get_metrics()
    assert metrics.get('autothrottle_count', 0) == 1

    # Wait for restore
    time.sleep(0.15)
    assert rl.capacity == 8


def test_autothrottle_telegram_notifications():
    reset_metrics()
    rl = DummyRateLimiter(capacity=6)

    class FakeTelegram:
        def __init__(self):
            self.sent = []

        def send(self, msg):
            self.sent.append(msg)

    tg = FakeTelegram()
    at = AutoThrottle(rl, threshold=1, window_seconds=10, cooldown_seconds=0.1, reduction_factor=0.5, telegram_thread=tg)

    at.record_429()
    # Throttle should send a message immediately
    assert len(tg.sent) >= 1
    assert 'AutoThrottle triggered' in tg.sent[0]

    # Wait for restore message
    time.sleep(0.15)
    assert any('AutoThrottle restored' in m for m in tg.sent)
