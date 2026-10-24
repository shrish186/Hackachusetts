"""Startup warm-up in two phases, in one daemon thread.

Phase 1, "basic" (sets ``ready``; /api/ready returns 200 after it):
  snapshots, land mask, wave field, zone masks, whale surfaces for the replay
  window and the next few hours, and one demo plan. Kept small so a free-tier
  wake-up is ready in seconds.

Phase 2, "full" (runs after ready, in the background):
  whale surfaces for the replay day and the next 24 h; one plan per core port x
  vessel at form defaults for the replay date and now; one small-boat plan from
  every other port id (planner_only ports included); the risk layer at the
  frontend's default speeds. Short sleeps between plans let user requests
  interleave.

/api/health never waits on either phase.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("fathom.warmup")

_state: dict[str, object] = {"started": False, "ready": False, "error": None, "seconds": None,
                             "plans": 0, "full_ready": False, "full_seconds": None}
_lock = threading.Lock()

#: Frontend "Replay whale season" instant (frontend/src/lib/time.ts).
REPLAY_DEPART = datetime(2026, 3, 15, 13, tzinfo=timezone.utc)
DEMO_DEPART = REPLAY_DEPART
#: Ports in the 32-plan matrix (the original five; the simulator fleet sails from these).
PORTS = ("gloucester", "boston", "plymouth", "provincetown", "new_bedford")
VESSELS = ("small_boat", "mid_trawler", "scalloper")
#: Frontend form defaults (CaptainPanel.tsx): 9.5 kn, 14 h, risk 0.6, Stellwagen Bank.
DEFAULTS = {"cruise_kn": 9.5, "max_hours": 14, "risk_pref": 0.6, "target_ground": "stellwagen_bank"}
#: "Try the demo trip" button; also the per-port warm-up trip.
DEMO_TRIP = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12,
             "target_ground": "stellwagen_bank", "risk_pref": 0.8}
#: Pause between background plans so live requests get the CPU (GIL).
YIELD_S = 0.02


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _plan(trip: dict, dep: datetime) -> None:
    from app.agent.agent import run_agent

    for _ in run_agent({**trip, "depart_window": [_iso(dep), _iso(dep)], "language": "en"}):
        pass


def warm_plans(departures: list[datetime], pause: float = 0.0) -> int:
    """Run the agent for every core port x vessel (defaults) plus the demo trip."""
    n = 0
    for dep in departures:
        trips = [{**DEFAULTS, "port": p, "vessel": v} for p in PORTS for v in VESSELS] + [DEMO_TRIP]
        for t in trips:
            _plan(t, dep)
            n += 1
            if pause:
                time.sleep(pause)
    return n


#: Total time allowed for the per-port warm-up (plan time only, pauses excluded).
ALL_PORTS_BUDGET_S = 5.0


def warm_all_ports(departures: list[datetime], pause: float = 0.0, budget_s: float = ALL_PORTS_BUDGET_S) -> int:
    """One small-boat demo-settings plan from every configured port id not in PORTS.

    Stops once ``budget_s`` of planning time is used, so adding many ports can
    never make the warm-up expensive; ports not reached are planned on demand.
    """
    from app.engine.routing import ports_config

    n = 0
    spent = 0.0
    for dep in departures:
        for pid in sorted(ports_config()["ports"]):
            if pid in PORTS:
                continue
            if spent >= budget_s:
                log.info("per-port warm-up stopped at its %.1f s budget after %d plans", budget_s, n)
                return n
            t0 = time.monotonic()
            _plan({**DEMO_TRIP, "port": pid}, dep)
            spent += time.monotonic() - t0
            n += 1
            if pause:
                time.sleep(pause)
    return n


def _now_bucket() -> datetime:
    from app.engine import routing

    return routing.risk_bucket(datetime.now(timezone.utc)) + timedelta(minutes=30)


def _surfaces(start: datetime, hours: float) -> None:
    from app.engine import routing

    for k in range(int(hours * 2) + 1):
        routing.whale_surface(routing.risk_bucket(start + timedelta(minutes=30 * k)))


def run_basic() -> None:
    """Phase 1: just enough for a fast first request."""
    from app.api import layers
    from app.engine import routing

    layers.land_mask()
    routing._land()
    routing._wx_grids()
    routing._readings()
    for z in routing._zone_set(None):
        routing._zone_mask(z.geom_key)
    _surfaces(REPLAY_DEPART - timedelta(hours=1), 8)
    _surfaces(_now_bucket(), 6)
    _plan(DEMO_TRIP, REPLAY_DEPART)


def run_full(pause: float = YIELD_S) -> int:
    """Phase 2: the wide warm-up (surfaces for 24 h, 32-plan matrix, every port)."""
    from app.api import layers

    now = _now_bucket()
    _surfaces(REPLAY_DEPART - timedelta(hours=2), 24)
    _surfaces(now, 24)
    n = warm_plans([REPLAY_DEPART, now], pause)
    n += warm_all_ports([REPLAY_DEPART, now], pause)
    for speed in (9.0, 9.5, 10.0):
        layers.risk_items(None, REPLAY_DEPART, speed)
    return n


def run_warmup(full: bool = True) -> None:
    """Both phases in order (the full phase can be skipped)."""
    t0 = time.monotonic()
    try:
        run_basic()
        _state["ready"] = True
    except Exception as exc:  # noqa: BLE001 - report, never crash the server
        log.exception("basic warm-up failed")
        _state["error"] = type(exc).__name__
        _state["seconds"] = round(time.monotonic() - t0, 2)
        return
    _state["seconds"] = round(time.monotonic() - t0, 2)
    if not full:
        return
    t1 = time.monotonic()
    try:
        _state["plans"] = run_full()
        _state["full_ready"] = True
    except Exception:  # noqa: BLE001 - the basics are warm; keep serving
        log.exception("full warm-up failed")
    finally:
        _state["full_seconds"] = round(time.monotonic() - t1, 2)


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
