import types
from datetime import datetime, timezone, timedelta
import requests

import pytest

from app.candle_fetcher import CandleFetcher
from app.candle_fetcher import CandleFetcher as CF


def test_timestamp_roundtrip(tmp_path):
    # Use real Database to test round-trip timestamp storage
    from app.database import Database

    db_path = tmp_path / "data" / "test.db"
    db = Database(str(db_path))

    now = datetime(2022, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    candles = [
        [int(now.timestamp() * 1000), 1, 2, 0.5, 1.5, 10],
        [int((now + timedelta(minutes=1)).timestamp() * 1000), 1.5, 2.5, 1.2, 2.0, 8]
    ]

    inserted = db.save_candles('BTC-EUR', '1m', candles)
    assert inserted == 2

    res = db.get_candles('BTC-EUR', '1m', limit=10)
    assert len(res) == 2

    # Round-trip: parse timestamps and compare to original datetimes
    for i, c in enumerate(res):
        ts_str = c['timestamp']
        assert ts_str.endswith('Z')
        parsed = datetime.fromisoformat(ts_str.rstrip('Z')).replace(tzinfo=timezone.utc)
        orig_dt = datetime.fromtimestamp(candles[i][0] / 1000, timezone.utc)
        assert parsed == orig_dt


def test_ensure_history_backfills_old_and_recent(monkeypatch):
    client = types.SimpleNamespace()
    # Make earliest in DB be 200 days ago, latest be 1 day ago
    now = datetime.now(timezone.utc)
    earliest = now - timedelta(days=200)
    latest = now - timedelta(days=1)

    class FakeDB:
        def get_earliest_candle_timestamp(self, market, interval):
            return earliest
        def get_latest_candle_timestamp(self, market, interval):
            return latest

    db = FakeDB()
    fetcher = CandleFetcher(client, db)

    calls = []
    def fake_backfill_market(market, interval, from_dt, to_dt):
        calls.append((market, interval, from_dt, to_dt))
        return 5

    fetcher.backfill_market = fake_backfill_market

    inserted = fetcher.ensure_history('BTC-EUR', '1h', years=1)
    # Should call backfill twice (older and newer ranges)
    assert len(calls) == 2
    assert inserted == 10


def test_backfill_handles_http_errors(monkeypatch):
    client = types.SimpleNamespace()
    class FakeDB:
        pass
    db = FakeDB()
    fetcher = CandleFetcher(client, db)

    def raise_http(*args, **kwargs):
        raise requests.HTTPError("429 Too Many Requests")

    monkeypatch.setattr(fetcher, '_fetch_range', raise_http)

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    inserted = fetcher.backfill_market('BTC-EUR', '1h', start, now)
    assert inserted == 0


def test_runner_calls_ensure_history(monkeypatch):
    import scripts.update_candles as runner

    # Replace BitvavoClient with a dummy to avoid credential checks
    monkeypatch.setattr(runner, 'BitvavoClient', lambda: types.SimpleNamespace())

    called = []
    def fake_ensure_history(self_market, interval):
        called.append(self_market)
        return 1

    # Monkeypatch CandleFetcher.ensure_history on the class used by runner
    monkeypatch.setattr('app.candle_fetcher.CandleFetcher.ensure_history', lambda self, m, i: fake_ensure_history(m, i))

    runner.main(realtime=False, interval='1h', poll_seconds=1)

    # Should have ensured history for both markets
    assert 'BTC-EUR' in called
    assert 'TAO-EUR' in called