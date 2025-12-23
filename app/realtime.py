import time
import threading
from typing import List

from .candle_fetcher import CandleFetcher
from .bitvavo_client import BitvavoClient
from .database import Database
from .metrics import increment


class RealTimeUpdater:
    """Run a resilient realtime updater for a set of markets.

    On start: ensures history (backfill), then polls latest candle periodically.
    On transient errors, uses exponential backoff and keeps running. Metrics are emitted via app.metrics.increment().
    """

    def __init__(self, markets: List[str], interval: str = "1m", poll_seconds: int = 60, client: BitvavoClient = None, db: Database = None):
        self.markets = markets
        self.interval = interval
        self.poll_seconds = poll_seconds
        self.client = client or BitvavoClient()
        self.db = db or Database()
        self.fetcher = CandleFetcher(self.client, self.db)
        self.threads: List[threading.Thread] = []
        self.stop_event = threading.Event()

    def _worker(self, market: str):
        # Ensure history once at start
        try:
            inserted = self.fetcher.ensure_history(market, self.interval)
            increment(f"backfill_inserted_{market}", inserted)
        except Exception as e:
            print(f"⚠️ Error during initial backfill for {market}: {e}")

        # Poll loop with simple backoff on error
        backoff_base = 1.0
        while not self.stop_event.is_set():
            try:
                inserted = 0
                ok = self.fetcher.poll_latest_once(market, self.interval)
                if ok:
                    increment(f"latest_inserted_{market}")
                    inserted = 1
                # Reset backoff on success
                backoff_base = 1.0
            except Exception as e:
                print(f"⚠️ Realtime worker error for {market}: {e}")
                # Increase backoff
                time.sleep(backoff_base)
                backoff_base = min(backoff_base * 2, 300)
                continue

            # wait before next poll, or exit early if stop_event set
            for _ in range(int(max(1, self.poll_seconds))):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def start(self, block: bool = True):
        """Start worker threads for all markets."""
        print(f"▶️ Starting RealTimeUpdater for markets: {self.markets} interval={self.interval} poll_seconds={self.poll_seconds}")
        self.stop_event.clear()
        for m in self.markets:
            t = threading.Thread(target=self._worker, args=(m,), daemon=True)
            t.start()
            self.threads.append(t)

        if block:
            try:
                while not self.stop_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Interrupted; stopping RealTimeUpdater")
                self.stop()

    def stop(self):
        self.stop_event.set()
        for t in self.threads:
            t.join(timeout=5)
        print("⏹️ RealTimeUpdater stopped")
