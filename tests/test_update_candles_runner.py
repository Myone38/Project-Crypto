import types
from unittest.mock import patch

import scripts.update_candles as runner


def test_runner_realtime_nonblocking(monkeypatch):
    # Replace BitvavoClient with dummy
    monkeypatch.setattr(runner, 'BitvavoClient', lambda: types.SimpleNamespace())

    # Monkeypatch CandleFetcher.start_realtime to record calls
    calls = []
    def fake_start_realtime(self, market, interval, poll_seconds, stop_event=None):
        calls.append((market, interval, poll_seconds))
        return

    monkeypatch.setattr('app.candle_fetcher.CandleFetcher.start_realtime', fake_start_realtime)
    # Also patch CandleFetcher.ensure_history to avoid real API calls
    monkeypatch.setattr('app.candle_fetcher.CandleFetcher.ensure_history', lambda self, m, i: 0)

    # Run runner.main with realtime True but non-blocking
    runner.main(realtime=True, interval='1h', poll_seconds=5, block=False)

    # Should have started realtime for expected markets
    markets_started = [c[0] for c in calls]
    assert 'BTC-EUR' in markets_started
    assert 'TAO-EUR' in markets_started