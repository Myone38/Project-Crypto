import pytest
from datetime import datetime, timezone, timedelta
import types
import requests

from app.candle_fetcher import CandleFetcher


def test_backfill_pagination_multi_page(monkeypatch):
    client = types.SimpleNamespace()
    inserted_pages = []

    class FakeDB:
        def save_candles(self, market, interval, candles):
            inserted_pages.append(list(candles))
            return len(candles)

    db = FakeDB()
    fetcher = CandleFetcher(client, db, page_limit=2, sleep_between_pages=0)

    # Simulate paginated responses depending on start param
    calls = {'count': 0}

    def fake_get(url, params=None):
        calls['count'] += 1
        # First call returns 2 candles, second returns 2, third empty
        if calls['count'] == 1:
            return types.SimpleNamespace(status_code=200, headers={}, json=lambda: [[1609459200000,1,2,3,4,5],[1609462800000,2,3,4,5,6]], raise_for_status=lambda: None)
        if calls['count'] == 2:
            return types.SimpleNamespace(status_code=200, headers={}, json=lambda: [[1609466400000,3,4,5,6,7],[1609470000000,4,5,6,7,8]], raise_for_status=lambda: None)
        return types.SimpleNamespace(status_code=200, headers={}, json=lambda: [], raise_for_status=lambda: None)

    monkeypatch.setattr('requests.get', fake_get)

    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    end = datetime(2021, 1, 2, tzinfo=timezone.utc)
    inserted = fetcher.backfill_market('BTC-EUR', '1h', start, end)

    assert inserted == 4
    assert len(inserted_pages) == 2


def test_detect_and_backfill_gaps(monkeypatch):
    client = types.SimpleNamespace()
    now = datetime(2021,1,1,12,0,0,tzinfo=timezone.utc)

    # Create fake DB with candles missing a piece
    class FakeDB:
        def __init__(self):
            self.candles = []
            # Create candles at 0,1,2,5,6 minutes (gap between 2 and 5)
            base_ts = now
            for i in [0,1,2,5,6]:
                ts = (base_ts + timedelta(minutes=i)).replace(microsecond=0).isoformat() + 'Z'
                self.candles.append({'timestamp': ts, 'open':1,'high':2,'low':0.5,'close':1.5,'volume':10})
        def get_earliest_candle_timestamp(self, m,i):
            return datetime.fromisoformat(self.candles[0]['timestamp'].rstrip('Z')).replace(tzinfo=timezone.utc)
        def get_latest_candle_timestamp(self, m,i):
            return datetime.fromisoformat(self.candles[-1]['timestamp'].rstrip('Z')).replace(tzinfo=timezone.utc)
        def get_candles_range(self, market, interval, start, end):
            return self.candles

    db = FakeDB()
    fetcher = CandleFetcher(client, db)

    calls = []
    def fake_backfill_market(market, interval, from_dt, to_dt):
        calls.append((from_dt, to_dt))
        return 2

    monkeypatch.setattr(fetcher, 'backfill_market', fake_backfill_market)

    inserted = fetcher.detect_and_backfill_gaps('BTC-EUR', '1m')
    assert inserted == 2
    assert len(calls) == 1
    # Ensure the gap start is after the third candle and end is before the fourth
    gap_from, gap_to = calls[0]
    assert gap_from < gap_to


def test_rate_limit_backoff(monkeypatch):
    client = types.SimpleNamespace()
    inserted_pages = []
    class FakeDB:
        def save_candles(self, market, interval, candles):
            inserted_pages.append(list(candles))
            return len(candles)

    db = FakeDB()
    fetcher = CandleFetcher(client, db, page_limit=2, sleep_between_pages=0)

    calls = {'count': 0}

    def fake_get(url, params=None):
        calls['count'] += 1
        if calls['count'] <= 2:
            # Simulate 429 with Retry-After header
            return types.SimpleNamespace(status_code=429, headers={'Retry-After':'0.01'}, json=lambda: [], raise_for_status=lambda: (_ for _ in ()).throw(requests.HTTPError('429')))
        # third call succeeds
        return types.SimpleNamespace(status_code=200, headers={}, json=lambda: [[1609459200000,1,2,3,4,5]], raise_for_status=lambda: None)

    monkeypatch.setattr('requests.get', fake_get)

    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    end = datetime(2021, 1, 1, tzinfo=timezone.utc)
    inserted = fetcher.backfill_market('BTC-EUR', '1h', start, end)

    assert inserted == 1
    assert calls['count'] >= 3