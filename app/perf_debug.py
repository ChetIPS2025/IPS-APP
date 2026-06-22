"""Gated performance timing for Streamlit reruns (enable with ``IPS_DEBUG_PERFORMANCE=1``)."""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

_LOG = logging.getLogger("ips.perf")


def perf_enabled() -> bool:
    try:
        from app.config import settings

        return bool(getattr(settings, "debug_performance", False))
    except Exception:
        return False


@contextmanager
def perf_span(name: str) -> Iterator[None]:
    """Log wall time for a block when performance debugging is on."""
    if not perf_enabled():
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        _LOG.warning("[perf] %s: %.1f ms", name, dt_ms)


def perf_log(name: str, dt_seconds: float) -> None:
    if perf_enabled():
        _LOG.warning("[perf] %s: %.1f ms", name, dt_seconds * 1000.0)


def perf_now() -> float:
    return time.perf_counter()
