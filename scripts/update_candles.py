"""Small runner to backfill BTC-EUR and TAO-EUR and optionally start realtime polling."""
import argparse

from app.bitvavo_client import BitvavoClient
from app.database import get_database
from app.candle_fetcher import CandleFetcher


def main(realtime: bool, interval: str, poll_seconds: int, block: bool = True):
    client = BitvavoClient()
    db = get_database()

    # Optionally enable AutoThrottle (set AUTO_THROTTLE=1 or true in env)
    import os
    auto_throttle_enabled = os.getenv('AUTO_THROTTLE', '').lower() in ('1', 'true', 'yes')
    fetcher = None
    if auto_throttle_enabled:
        from app.rate_limiter import RateLimiter
        from app.autothrottle import AutoThrottle
        rl = RateLimiter()
        telegram_thread = None
        # If Telegram env vars are present, create and start the Telegram thread to receive alerts
        if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
            try:
                from app.telegram_thread import TelegramThread
                telegram_thread = TelegramThread(None)
                telegram_thread.start()
            except Exception:
                telegram_thread = None
        at = AutoThrottle(rl, telegram_thread=telegram_thread)
        fetcher = CandleFetcher(client, db, rate_limiter=rl, autothrottle=at)
    else:
        fetcher = CandleFetcher(client, db)

    markets = ["BTC-EUR", "TAO-EUR"]

    # Ensure history for each market
    for m in markets:
        print(f"--- Ensuring history for {m} {interval}")
        fetcher.ensure_history(m, interval)

    # Optionally start realtime
    if realtime:
        # Use RealTimeUpdater for robust realtime behavior and metrics
        from app.realtime import RealTimeUpdater
        updater = RealTimeUpdater(markets, interval=interval, poll_seconds=poll_seconds, client=client, db=db)
        updater.start(block=block)
        return



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill and optionally run realtime candle updater.')
    parser.add_argument('--realtime', action='store_true', help='Start realtime polling after backfill')
    parser.add_argument('--interval', default='1h', help='Candle interval (e.g., 1m,5m,1h)')
    parser.add_argument('--poll-seconds', type=int, default=60, help='Polling interval seconds for realtime')
    parser.add_argument('--no-block', action='store_true', help='Do not block when starting realtime threads (useful for tests)')
    args = parser.parse_args()
    main(args.realtime, args.interval, args.poll_seconds, block=not args.no_block)
