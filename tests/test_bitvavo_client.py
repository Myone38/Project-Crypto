import os
import pytest

import app.bitvavo_client as mod

class DummyResponse:
    def __init__(self, headers):
        self.headers = headers

class DummyBitvavo:
    def __init__(self, config):
        pass
    def balance(self):
        return []
    def ordersOpen(self):
        return []
    def getOrders(self):
        return []
    def tickerPrice(self, kwargs):
        return {'price': '123.45'}


def test_missing_credentials_raises(monkeypatch, tmp_path):
    # Ensure env vars are not set and no credentials file exists in cwd
    monkeypatch.delenv('BITVAVO_API_KEY', raising=False)
    monkeypatch.delenv('BITVAVO_API_SECRET', raising=False)

    # Change working dir to a temporary folder without config
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        mod.BitvavoClient()


def test_missing_dependency_raises(monkeypatch):
    # Provide env vars so credential check passes
    monkeypatch.setenv('BITVAVO_API_KEY', 'x')
    monkeypatch.setenv('BITVAVO_API_SECRET', 'y')

    # Simulate missing dependency
    monkeypatch.setattr(mod, '_HAS_BITVAVO', False)

    with pytest.raises(ImportError):
        mod.BitvavoClient()


def test_get_rate_limit_reads_headers(monkeypatch, tmp_path):
    monkeypatch.setenv('BITVAVO_API_KEY', 'x')
    monkeypatch.setenv('BITVAVO_API_SECRET', 'y')

    # Use dummy Bitvavo class to avoid network
    monkeypatch.setattr(mod, 'Bitvavo', DummyBitvavo)

    # Mock requests.get to return predictable headers
    def fake_get(url):
        return DummyResponse({
            'bitvavo-ratelimit-limit': '1000',
            'bitvavo-ratelimit-remaining': '900',
            'bitvavo-ratelimit-resetat': '123456'
        })

    monkeypatch.setattr(mod.requests, 'get', fake_get)

    client = mod.BitvavoClient()
    rl = client.get_rate_limit()

    assert rl['limit'] == '1000'
    assert rl['remaining'] == '900'
    assert rl['reset_at'] == '123456'
