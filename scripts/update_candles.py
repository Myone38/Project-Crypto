"""Small runner to backfill BTC-EUR and TAO-EUR and optionally start realtime polling."""
import argparse
import threading
from datetime import datetime, timezone

from app.bitvavo_client import BitvavoClient
from app.database import get_database
from app.candle_fetcher import CandleFetcher


def main(realtime: bool, interval: str, poll_seconds: int, block: bool = True):
    client = BitvavoClient()
    db = get_database()
    fetcher = CandleFetcher(client, db)

    markets = ["BTC-EUR", "TAO-EUR"]

    # Ensure history for each market
    for m in markets:
        print(f"--- Ensuring history for {m} {interval}")
        fetcher.ensure_history(m, interval)

    # Optionally start realtime
    if realtime:
        stop_event = threading.Event()
        threads = []
        for m in markets:
            t = threading.Thread(target=fetcher.start_realtime, args=(m, interval, poll_seconds, stop_event), daemon=True)
            t.start()
            threads.append(t)
        if block:
            try:
                while True:
                    pass
            except KeyboardInterrupt:
                print("Stopping realtime threads...")
                stop_event.set()
                for t in threads:
                    t.join()
        else:
            # Non-blocking mode: return immediately (useful for tests)
            return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill and optionally run realtime candle updater.')
    parser.add_argument('--realtime', action='store_true', help='Start realtime polling after backfill')
    parser.add_argument('--interval', default='1h', help='Candle interval (e.g., 1m,5m,1h)')
    parser.add_argument('--poll-seconds', type=int, default=60, help='Polling interval seconds for realtime')
    parser.add_argument('--no-block', action='store_true', help='Do not block when starting realtime threads (useful for tests)')
    args = parser.parse_args()
    main(args.realtime, args.interval, args.poll_seconds, block=not args.no_block)