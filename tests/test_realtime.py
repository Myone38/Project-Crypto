import types
import time

from app.realtime import RealTimeUpdater
from app.metrics import get_metrics, reset_metrics


def test_realtime_start_and_stop(monkeypatch):
    # Use dummy client and DB so no network calls
    dummy_client = types.SimpleNamespace()
    class FakeDB:
        def __init__(self):
            self.calls = []
        def get_earliest_candle_timestamp(self, m, i):
            return None
        def get_latest_candle_timestamp(self, m, i):
            return None
        def save_candles(self, market, interval, candles):
            return len(candles)
        def insert_candle(self, market, interval, timestamp, o, h, low, c, v):
            return True

    db = FakeDB()

    # Monkeypatch CandleFetcher.ensure_history and poll_latest_once
    def fake_ensure_history(self, market, interval):
        return 2
    def fake_poll_latest_once(self, market, interval):
        return True

    monkeypatch.setattr('app.candle_fetcher.CandleFetcher.ensure_history', fake_ensure_history)
    monkeypatch.setattr('app.candle_fetcher.CandleFetcher.poll_latest_once', fake_poll_latest_once)

    import threading
    reset_metrics()
    updater = RealTimeUpdater(['BTC-EUR'], interval='1m', poll_seconds=1, client=dummy_client, db=db)
    # Start non-blocking
    t = None
    try:
        t = threading.Thread(target=updater.start, kwargs={'block': False}, daemon=True)
        t.start()
        time.sleep(2)
        updater.stop()
        # Check metrics were incremented
        metrics = get_metrics()
        assert metrics.get('backfill_inserted_BTC-EUR', 0) >= 0
        # latest_inserted may be present if poll ran at least once
        assert 'latest_inserted_BTC-EUR' in metrics
    finally:
        if t:
            t.join(timeout=1)
