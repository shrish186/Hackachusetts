"""Startup warm-up: preload snapshots, grid, risk surfaces and a matrix of plans.

Runs in a daemon thread so the server accepts connections (and /api/health
answers) immediately. /api/ready returns 200 only after this finishes.

Warmed:
  * snapshots, land mask, wave field, zone masks
  * whale surfaces (30-minute buckets) for the replay day and the next 24 h from now
  * one plan per port x vessel at default settings, for the replay date and for now
  * the risk layer at the frontend's default speeds
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("fathom.warmup")

_state: dict[str, object] = {"started": False, "ready": False, "error": None, "seconds": None, "plans": 0}
_lock = threading.Lock()

#: Frontend "Replay whale season" instant (frontend/src/lib/time.ts).
REPLAY_DEPART = datetime(2026, 3, 15, 13, tzinfo=timezone.utc)
DEMO_DEPART = REPLAY_DEPART
PORTS = ("gloucester", "boston", "plymouth", "provincetown", "new_bedford")
VESSELS = ("small_boat", "mid_trawler", "scalloper")
#: Frontend form defaults (CaptainPanel.tsx): 9.5 kn, 14 h, risk 0.6, Stellwagen Bank.
DEFAULTS = {"cruise_kn": 9.5, "max_hours": 14, "risk_pref": 0.6, "target_ground": "stellwagen_bank"}
#: "Try the demo trip" button.
DEMO_TRIP = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12,
             "target_ground": "stellwagen_bank", "risk_pref": 0.8}


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def warm_plans(departures: list[datetime]) -> int:
    """Run the agent for every port x vessel (defaults) plus the demo trip."""
    from app.agent.agent import run_agent

    n = 0
    for dep in departures:
        trips = [{**DEFAULTS, "port": p, "vessel": v} for p in PORTS for v in VESSELS] + [DEMO_TRIP]
        for t in trips:
            for _ in run_agent({**t, "depart_window": [_iso(dep), _iso(dep)], "language": "en"}):
                pass
            n += 1
    return n


def run_warmup() -> None:
    """Load everything the first request would otherwise build lazily."""
    t0 = time.monotonic()
    try:
        from app.api import layers
        from app.engine import routing

        layers.land_mask()
        routing._land()
        routing._wx_grids()
        routing._readings()
        for z in routing._zone_set(None):
            routing._zone_mask(z.geom_key)
        now = routing.risk_bucket(datetime.now(timezone.utc)) + timedelta(minutes=30)
        for start in (REPLAY_DEPART - timedelta(hours=2), now):
            for k in range(0, 24 * 2 + 1):
                routing.whale_surface(routing.risk_bucket(start + timedelta(minutes=30 * k)))
        _state["plans"] = warm_plans([REPLAY_DEPART, now])
        for speed in (9.0, 9.5, 10.0):
            layers.risk_items(None, REPLAY_DEPART, speed)
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
