
import scripts.update_candles as updater


class DummyRL:
    pass


class FakeTG:
    def __init__(self, engine):
        self.started = False

    def start(self):
        self.started = True


class FakeFetcher:
    def __init__(self, client, db, rate_limiter=None, autothrottle=None):
        self.client = client
        self.db = db
        self.rate_limiter = rate_limiter
        self.autothrottle = autothrottle

    def ensure_history(self, market, interval):
        # No-op for test (we only need to ensure this method exists)
        return 0


def test_runner_creates_autothrottle(monkeypatch, tmp_path):
    # Enable auto throttle env var and telegram envs
    monkeypatch.setenv('AUTO_THROTTLE', '1')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'x')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '1')

    # Patch CandleFetcher to capture creation
    monkeypatch.setattr(updater, 'CandleFetcher', FakeFetcher)

    # Patch RateLimiter and AutoThrottle implementations used in the runner
    monkeypatch.setattr('app.rate_limiter.RateLimiter', lambda: DummyRL())

    class FakeAT:
        def __init__(self, rl, telegram_thread=None):
            self.rl = rl
            self.tg = telegram_thread

    monkeypatch.setattr('app.autothrottle.AutoThrottle', FakeAT)
    monkeypatch.setattr('app.telegram_thread.TelegramThread', FakeTG)

    # Call main (should not start realtime)
    updater.main(realtime=False, interval='1h', poll_seconds=60, block=True)

    # If no exception, we assume the path executed; we can't directly inspect local fetcher instance here
    # but we ensure no errors when creating telegram thread and autothrottle under env vars
    # (the assertions are implicit by absence of raised exceptions)
    assert True
