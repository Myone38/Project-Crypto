import types
from datetime import datetime, timezone

from app.candle_fetcher import CandleFetcher
from app.metrics import get_metrics, reset_metrics, REQS_MADE, REQS_429, BACKOFF_SEC
from datetime import timedelta


def test_fetcher_increments_metrics_on_429(monkeypatch):
    client = types.SimpleNamespace()
    class FakeDB:
        pass

    db = FakeDB()
    fetcher = CandleFetcher(client, db, page_limit=1, sleep_between_pages=0)

    calls = {'count': 0}
    def fake_get(url, params=None):
        calls['count'] += 1
        if calls['count'] == 1:
            return types.SimpleNamespace(status_code=429, headers={'Retry-After':'0.01'}, json=lambda: [], raise_for_status=lambda: (_ for _ in ()).throw(Exception('429')))
        return types.SimpleNamespace(status_code=200, headers={}, json=lambda: [[1609459200000,1,2,3,4,5]], raise_for_status=lambda: None)

    monkeypatch.setattr('requests.get', fake_get)
    reset_metrics()
    fetcher.backfill_market('BTC-EUR', '1h', datetime.now(timezone.utc) - timedelta(hours=1), datetime.now(timezone.utc))

    metrics = get_metrics()
    # At least one request attempted and at least one 429 recorded
    assert metrics.get(REQS_MADE, 0) >= 1
    assert metrics.get(REQS_429, 0) >= 1
    assert metrics.get(BACKOFF_SEC, 0) >= 0
