"""GET /api/meta/ports: ports and fishing grounds with closure state at a time.

Ports and grounds come from config/ports.yaml through the Lane A loader
(app.ingest.ports). A ground is closed when an active prohibited zone covers it,
using the same test the router uses for ``access_lost``.
"""
from __future__ import annotations

import threading
import time as _time
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.trip import MAX_FUTURE, earliest_departure
from app.engine.routing import ground_status
from app.ingest.ports import load_grounds, load_ports

router = APIRouter(tags=["meta"])

CACHE_TTL_S = 30.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()

TimeQ = Annotated[datetime | None, Query(description="UTC time (ISO-8601). Default: now.")]


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _bad_time(msg: str) -> RequestValidationError:
    return RequestValidationError([{"type": "value_error", "loc": ("query", "time"), "msg": msg, "input": None}])


def closed_reason(st: dict[str, Any]) -> str | None:
    """Plain text for a closed ground (same wording family as the router's access_lost)."""
    if not st["closed"]:
        return None
    if st["code"] == "closed_zone":
        until = f" until {st['zone_active_to'][:10]}" if st.get("zone_active_to") else ""
        return f"Inside active closed zone {st['zone_name']}{until}."
    if st["code"] == "land":
        return "The ground point is on land in the study grid."
    return "The ground point is outside the study area."


def build_ports(when: datetime) -> dict[str, Any]:
    grounds = load_grounds()
    status = {gid: ground_status((float(g["lon"]), float(g["lat"])), when) for gid, g in grounds.items()}
    ground_list = [
        {
            "id": gid,
            "name": g.get("name", gid),
            "lon": float(g["lon"]),
            "lat": float(g["lat"]),
            "closed": status[gid]["closed"],
            "closed_reason": closed_reason(status[gid]),
            "zone_id": status[gid]["zone_id"],
        }
        for gid, g in grounds.items()
    ]
    ports = [
        {
            "id": pid,
            "name": p.get("name", pid),
            "state": p.get("state", "MA"),
            "lon": float(p["lon"]),
            "lat": float(p["lat"]),
            "grounds": [dict(g) for g in ground_list],
        }
        for pid, p in load_ports().items()
    ]
    return {"time": _iso(when), "ports": ports}


@router.get("/meta/ports")
def get_ports(time: TimeQ = None) -> JSONResponse:
    """Ports and grounds, each ground flagged closed/open at ``time`` (default now)."""
    now = datetime.now(timezone.utc)
    when = _utc(time) if time is not None else now.replace(second=0, microsecond=0)
    if when < earliest_departure(now):
        raise _bad_time("time is more than 7 days in the past")
    if when > now + MAX_FUTURE:
        raise _bad_time("time is too far in the future")
    key = _iso(when)
    t = _time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit is None or t - hit[0] > CACHE_TTL_S:
            if len(_cache) > 512:
                _cache.clear()
            hit = (t, build_ports(when))
            _cache[key] = hit
    return JSONResponse(hit[1], headers={"Cache-Control": f"public, max-age={int(CACHE_TTL_S)}"})


__all__ = ["build_ports", "router"]
