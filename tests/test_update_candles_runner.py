import types

import scripts.update_candles as runner


def test_runner_realtime_nonblocking(monkeypatch):
    # Replace BitvavoClient with dummy
    monkeypatch.setattr(runner, 'BitvavoClient', lambda: types.SimpleNamespace())

    # Monkeypatch RealTimeUpdater.start to record calls (since runner now uses RealTimeUpdater)
    calls = []
    def fake_realtime_start(self, block=True):
        calls.append({'markets': self.markets, 'interval': self.interval, 'poll_seconds': self.poll_seconds, 'block': block})
        return

    monkeypatch.setattr('app.realtime.RealTimeUpdater.start', fake_realtime_start)
    # Also patch CandleFetcher.ensure_history to avoid real API calls
    monkeypatch.setattr('app.candle_fetcher.CandleFetcher.ensure_history', lambda self, m, i: 0)

    # Run runner.main with realtime True but non-blocking
    runner.main(realtime=True, interval='1h', poll_seconds=5, block=False)

    # Should have started realtime for expected markets
    assert len(calls) == 1
    call = calls[0]
    assert 'BTC-EUR' in call['markets']
    assert 'TAO-EUR' in call['markets']
    assert call['interval'] == '1h'
    assert call['poll_seconds'] == 5
    assert call['block'] is False
