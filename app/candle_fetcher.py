import time
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .bitvavo_client import BitvavoClient
from .database import Database


class CandleFetcher:
    """Fetch and backfill candles from Bitvavo and persist to Database."""

    DEFAULT_PAGE_LIMIT = 1000

    def __init__(self, client: BitvavoClient, db: Database, page_limit: int = DEFAULT_PAGE_LIMIT, sleep_between_pages: float = 0.2):
        self.client = client
        self.db = db
        self.page_limit = page_limit
        self.sleep_between_pages = sleep_between_pages

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _interval_to_millis(interval: str) -> int:
        # Support common intervals used by Bitvavo
        if interval.endswith('m'):
            minutes = int(interval[:-1])
            return minutes * 60 * 1000
        if interval.endswith('h'):
            hours = int(interval[:-1])
            return hours * 60 * 60 * 1000
        if interval.endswith('d'):
            days = int(interval[:-1])
            return days * 24 * 60 * 60 * 1000
        raise ValueError(f"Unsupported interval: {interval}")

    # ------------------------------------------------------------------
    # Low-level HTTP fetch
    # ------------------------------------------------------------------
    def _fetch_range(self, market: str, interval: str, start_ms: Optional[int] = None, end_ms: Optional[int] = None, limit: Optional[int] = None) -> List[List]:
        """Fetch candles from Bitvavo REST API. Returns list like [[ts_ms, open, high, low, close, volume], ...]"""
        url = f"{self.client.BASE_URL}/candles/{market}/{interval}"
        params = {}
        if limit:
            params['limit'] = limit
        if start_ms is not None:
            params['start'] = int(start_ms)
        if end_ms is not None:
            params['end'] = int(end_ms)

        resp = requests.get(url, params=params)
        try:
            # Update client's rate-limit info if available
            self.client._update_rate_limit(resp)
        except Exception:
            pass

        resp.raise_for_status()
        data = resp.json()

        # Data format expected: [[timestamp, open, high, low, close, volume], ...]
        return data

    # ------------------------------------------------------------------
    # Backfill logic
    # ------------------------------------------------------------------
    def backfill_market(self, market: str, interval: str, from_dt: datetime, to_dt: datetime) -> int:
        """Backfill candles for market between from_dt and to_dt (both UTC datetimes). Returns inserted count."""
        inserted_total = 0
        start_ms = int(from_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(to_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        page_limit = self.page_limit
        interval_ms = self._interval_to_millis(interval)

        current_start = start_ms
        while current_start <= end_ms:
            try:
                # Fetch a page starting from current_start
                page = self._fetch_range(market, interval, start_ms=current_start, end_ms=end_ms, limit=page_limit)

                if not page:
                    break

                # Convert to DB format (timestamps in ms)
                # Save page into DB using existing save_candles which expects ms timestamps
                inserted = self.db.save_candles(market, interval, page)
                inserted_total += inserted

                # Determine the last timestamp received and move cursor forward
                last_ts = page[-1][0]
                # Advance to next candle to avoid infinite loop on same data
                current_start = last_ts + interval_ms

                # Sleep between pages to respect rate limits
                time.sleep(self.sleep_between_pages)

            except requests.HTTPError as e:
                print(f"❌ HTTP error while fetching candles for {market} {interval}: {e}")
                break
            except Exception as e:
                print(f"❌ Unexpected error during backfill for {market} {interval}: {e}")
                break

        print(f"✅ Backfill complete for {market} {interval}: inserted {inserted_total} candles")
        return inserted_total

    # ------------------------------------------------------------------
    # High-level ensure history
    # ------------------------------------------------------------------
    def ensure_history(self, market: str, interval: str, years: int = 3) -> int:
        """Ensure there is at least `years` years of history for a market+interval. Returns total inserted."""
        now = datetime.now(timezone.utc)
        start_target = now - timedelta(days=365 * years)

        earliest = self.db.get_earliest_candle_timestamp(market, interval)
        latest = self.db.get_latest_candle_timestamp(market, interval)

        total_inserted = 0

        # If no data at all, backfill full range
        if earliest is None:
            print(f"ℹ️ No candles for {market} {interval} found. Backfilling full range ({start_target} → {now})")
            total_inserted += self.backfill_market(market, interval, start_target, now)
            return total_inserted

        # If earliest is after target, backfill older range
        if earliest > start_target:
            print(f"ℹ️ Found earliest {earliest} for {market} {interval}, backfilling older range ({start_target} → {earliest - timedelta(milliseconds=1)})")
            total_inserted += self.backfill_market(market, interval, start_target, earliest - timedelta(milliseconds=1))

        # If latest is before now, backfill newer range
        if latest < now - timedelta(milliseconds=1):
            print(f"ℹ️ Latest {latest} is older than now, backfilling recent range ({latest + timedelta(milliseconds=1)} → {now})")
            total_inserted += self.backfill_market(market, interval, latest + timedelta(milliseconds=1), now)

        # Optionally: check for internal gaps (not implemented here)

        return total_inserted

    # ------------------------------------------------------------------
    # Real-time polling
    # ------------------------------------------------------------------
    def poll_latest_once(self, market: str, interval: str) -> bool:
        """Fetch the latest candle and insert it if newer than DB latest. Returns True if inserted."""
        latest_db = self.db.get_latest_candle_timestamp(market, interval)
        try:
            page = self._fetch_range(market, interval, limit=1)
            if not page:
                return False
            latest_candle = page[-1]
            ts_ms = int(latest_candle[0])
            ts_dt = datetime.utcfromtimestamp(ts_ms / 1000)

            if latest_db is None or ts_dt > latest_db:
                # Insert this single candle
                inserted = self.db.insert_candle(
                    market, interval, ts_dt, float(latest_candle[1]), float(latest_candle[2]), float(latest_candle[3]), float(latest_candle[4]), float(latest_candle[5])
                )
                if inserted:
                    print(f"✅ Inserted latest candle for {market} {interval} @ {ts_dt}")
                return inserted
            return False
        except Exception as e:
            print(f"❌ Error polling latest candle for {market} {interval}: {e}")
            return False

    def start_realtime(self, market: str, interval: str, poll_seconds: int = 60, stop_event=None):
        """Start a blocking loop that polls every `poll_seconds` (use in a thread). If stop_event (threading.Event) is provided, it will stop when set."""
        print(f"▶️ Starting realtime polling for {market} {interval} every {poll_seconds}s")
        try:
            while True:
                if stop_event and stop_event.is_set():
                    print(f"⏹️ Stopping realtime polling for {market} {interval}")
                    break
                try:
                    self.poll_latest_once(market, interval)
                except Exception as e:
                    print(f"⚠️ Error during poll loop: {e}")
                time.sleep(poll_seconds)
        except KeyboardInterrupt:
            print("Interrupted; stopping realtime polling")
