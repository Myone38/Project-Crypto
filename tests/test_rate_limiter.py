import time
from app.rate_limiter import RateLimiter


def test_rate_limiter_basic():
    rl = RateLimiter(max_req_per_min=60)  # 1 req/s
    # First token available
    assert rl.try_acquire() is True
    # Immediately after, tokens depleted
    assert rl.try_acquire() is False
    # Wait ~1 second and token should become available
    time.sleep(1.1)
    assert rl.try_acquire() is True


def test_wait_for_token_timeout():
    rl = RateLimiter(max_req_per_min=1)  # 1 per minute -> slow
    # Consume token
    assert rl.try_acquire() is True
    # next token available only after ~60s, but with short timeout we should fail
    assert rl.wait_for_token(timeout=0.1) is False
