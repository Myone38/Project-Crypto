import types
from datetime import datetime, timezone, timedelta

from app.candle_fetcher import CandleFetcher


def test_long_pagination_many_pages(monkeypatch):
    client = types.SimpleNamespace()
    inserted = []

    class FakeDB:
        def save_candles(self, market, interval, candles):
            inserted.extend(list(candles))
            return len(candles)

    db = FakeDB()
    fetcher = CandleFetcher(client, db, page_limit=2, sleep_between_pages=0)

    # Simulate 5 pages of 2 candles each -> 10 total
    pages = [
        [[1609459200000 + i * 3600000 + p * 2 * 3600000, 1,2,3,4,5] for i in range(2)]
        for p in range(5)
    ]

    calls = {'count': 0}

    def fake_get(url, params=None):
        idx = calls['count']
        calls['count'] += 1
        if idx < len(pages):
            return types.SimpleNamespace(status_code=200, headers={}, json=lambda p=pages[idx]: p, raise_for_status=lambda: None)
        return types.SimpleNamespace(status_code=200, headers={}, json=lambda: [], raise_for_status=lambda: None)

    monkeypatch.setattr('requests.get', fake_get)

    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    end = datetime(2021, 1, 6, tzinfo=timezone.utc)
    result = fetcher.backfill_market('BTC-EUR', '1h', start, end)

    assert result == 10
    assert len(inserted) == 10