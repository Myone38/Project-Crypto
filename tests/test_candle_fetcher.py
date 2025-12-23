import pytest
from datetime import datetime, timezone, timedelta

import types

from app.candle_fetcher import CandleFetcher


class DummyClient:
    BASE_URL = "https://api.bitvavo.com/v2"
    def _update_rate_limit(self, resp):
        pass


class DummyResponse:
    def __init__(self, data, headers=None, status_code=200):
        self._data = data
        self.headers = headers or {}
        self.status_code = status_code
    def json(self):
        return self._data
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_fetch_range(monkeypatch):
    client = DummyClient()
    db = types.SimpleNamespace()
    fetcher = CandleFetcher(client, db)

    def fake_get(url, params=None):
        assert 'candles' in url
        # Return two candles
        return DummyResponse([[1609459200000, '1', '2', '3', '4', '5'], [1609462800000, '2', '3', '4', '5', '6']])

    monkeypatch.setattr('requests.get', fake_get)
    data = fetcher._fetch_range('BTC-EUR', '1h', start_ms=1609459200000, end_ms=1609466400000, limit=100)
    assert isinstance(data, list)
    assert len(data) == 2


def test_backfill_pagination(monkeypatch):
    client = DummyClient()
    inserted_pages = []
    class FakeDB:
        def save_candles(self, market, interval, candles):
            inserted_pages.append(candles)
            return len(candles)

    db = FakeDB()
    fetcher = CandleFetcher(client, db, page_limit=2, sleep_between_pages=0)

    calls = {'count': 0}

    def fake_get(url, params=None):
        calls['count'] += 1
        # First page returns 2 candles, second page returns empty
        if calls['count'] == 1:
            return DummyResponse([[1609459200000, '1','2','3','4','5'], [1609462800000, '2','3','4','5','6']])
        return DummyResponse([])

    monkeypatch.setattr('requests.get', fake_get)

    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    end = datetime(2021, 1, 2, tzinfo=timezone.utc)
    inserted = fetcher.backfill_market('BTC-EUR', '1h', start, end)
    assert inserted == 2
    assert len(inserted_pages) == 1


def test_ensure_history_calls_backfill(monkeypatch):
    client = DummyClient()
    db = types.SimpleNamespace()
    # No data in DB
    db.get_earliest_candle_timestamp = lambda m, i: None
    fetcher = CandleFetcher(client, db)

    called = {'backfilled': False}
    def fake_backfill_market(market, interval, from_dt, to_dt):
        called['backfilled'] = True
        return 10

    fetcher.backfill_market = fake_backfill_market
    inserted = fetcher.ensure_history('BTC-EUR', '1h', years=1)
    assert called['backfilled'] is True
    assert inserted == 10


def test_poll_latest_once_inserts(monkeypatch):
    client = DummyClient()
    class FakeDB:
        def __init__(self):
            self.latest = datetime(2021, 1, 1, tzinfo=timezone.utc)
            self.inserted = False
        def get_latest_candle_timestamp(self, market, interval):
            return self.latest
        def insert_candle(self, market, interval, timestamp, o, h, l, c, v):
            self.inserted = True
            return True

    db = FakeDB()
    fetcher = CandleFetcher(client, db)

    def fake_fetch_range(market, interval, start_ms=None, end_ms=None, limit=None):
        # Return a single newer candle
        return [[1609545600000, '10','11','12','13','14']]

    monkeypatch.setattr(fetcher, '_fetch_range', fake_fetch_range)
    inserted = fetcher.poll_latest_once('BTC-EUR', '1h')
    assert inserted is True
    assert db.inserted is True