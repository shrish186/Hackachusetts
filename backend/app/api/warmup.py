"""Startup warm-up: preload snapshots, grid, risk surfaces and one dummy plan.

Runs in a daemon thread so the server accepts connections (and /api/health
answers) immediately. /api/ready returns 200 only after this finishes.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger("fathom.warmup")

_state: dict[str, object] = {"started": False, "ready": False, "error": None, "seconds": None}
_lock = threading.Lock()

#: Departure used by the frontend's demo trip; warming its risk slices makes the demo fast.
DEMO_DEPART = datetime(2026, 3, 15, 7, tzinfo=timezone.utc)


def run_warmup() -> None:
    """Load everything the first request would otherwise build lazily."""
    t0 = time.monotonic()
    try:
        from app.agent.agent import run_agent
        from app.api import layers
        from app.engine import routing

        layers.land_mask()
        routing._land()
        routing._wx_grids()
        routing._readings()
        for z in routing._zone_set(None):
            routing._zone_mask(z.geom_key)
        trip = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12,
                "depart_window": [DEMO_DEPART.isoformat(), DEMO_DEPART.isoformat()],
                "target_ground": "stellwagen_bank", "risk_pref": 0.8, "language": "en"}
        for _ in run_agent(trip):
            pass
        layers.risk_items(None, DEMO_DEPART, 9.0)
        _state["ready"] = True
    except Exception as exc:  # noqa: BLE001 - report, never crash the server
        log.exception("warm-up failed")
        _state["error"] = type(exc).__name__
    finally:
        _state["seconds"] = round(time.monotonic() - t0, 2)


def start_warmup() -> None:
    """Start the warm-up thread once (no-op if FATHOM_SKIP_WARMUP=true)."""
    with _lock:
        if _state["started"]:
            return
        _state["started"] = True
    if os.getenv("FATHOM_SKIP_WARMUP", "false").lower() in {"1", "true", "yes"}:
        _state["ready"] = True
        _state["seconds"] = 0.0
        return
    threading.Thread(target=run_warmup, name="fathom-warmup", daemon=True).start()


def status() -> dict[str, object]:
    return dict(_state)
