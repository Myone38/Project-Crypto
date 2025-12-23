import threading
from typing import Dict

_metrics_lock = threading.Lock()
_metrics: Dict[str, int] = {}


def increment(metric: str, value: int = 1) -> None:
    with _metrics_lock:
        _metrics[metric] = _metrics.get(metric, 0) + value


def get_metrics() -> Dict[str, int]:
    with _metrics_lock:
        return dict(_metrics)


def reset_metrics() -> None:
    with _metrics_lock:
        _metrics.clear()

# Helper metric names used by the fetcher
REQS_MADE = 'requests_made'
REQS_429 = 'requests_429'
BACKOFF_SEC = 'backoff_seconds_total'
