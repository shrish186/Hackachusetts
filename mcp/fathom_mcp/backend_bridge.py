"""Bridge from the MCP tools to the real backend engine (Lane D, task 7).

The MCP server and the FastAPI backend are separate packages. This module makes
the backend importable from the MCP process and exposes thin helpers that call
the real deterministic engine (risk, zones, effort, the what-if simulator).

Everything here degrades gracefully: if the backend package or its config/data
is not importable (e.g. the MCP server is run standalone), ``available()``
returns False and the tools fall back to their clearly-labelled placeholders.
No tool ever raises because the backend is missing.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

# mcp/fathom_mcp/backend_bridge.py -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"


def _ensure_backend_on_path() -> None:
    """Put the backend package root on sys.path so ``import app...`` works."""
    p = str(_BACKEND)
    if _BACKEND.is_dir() and p not in sys.path:
        sys.path.insert(0, p)


@lru_cache(maxsize=1)
def available() -> bool:
    """True if the backend engine can be imported in this process."""
    _ensure_backend_on_path()
    try:  # pragma: no cover - environment dependent
        import app.engine.effort
        import app.engine.risk
        import app.ingest.zones  # noqa: F401

        return True
    except Exception:
        return False


def zones_at(when_iso: str) -> list[dict[str, Any]]:
    """Return all zones with their active flag at ``when_iso`` (real engine)."""
    _ensure_backend_on_path()
    from datetime import datetime

    from app.ingest.zones import default_zones, is_active, restriction_summary

    when = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
    out: list[dict[str, Any]] = []
    for z in default_zones():
        out.append({
            "id": z.id,
            "name": z.name,
            "kind": z.kind,
            "active": is_active(z, when),
            "prohibited": z.prohibited,
            "speed_limit_kn": z.speed_limit_kn,
            "restriction": restriction_summary(z),
            "source_url": z.source_url,
            "synthetic": z.synthetic,
        })
    return out


def whale_risk_points(when_iso: str, speed_kn: float) -> list[dict[str, Any]]:
    """Return per-sighting whale-risk points at a speed (real risk model)."""
    _ensure_backend_on_path()
    from datetime import datetime

    from app.engine.risk import load_sightings, risk_breakdown

    when = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
    sightings = load_sightings()
    out: list[dict[str, Any]] = []
    for i, s in enumerate(sightings):
        bd = risk_breakdown(f"s{i}", s.lon, s.lat, when, speed_kn, sightings)
        out.append({
            "lon": s.lon,
            "lat": s.lat,
            "risk": round(bd.risk, 4),
            "top_factors": [{"factor": f, "value": round(v, 4)} for f, v in bd.top_factors()],
        })
    return out


def effort_grid(bbox: dict, step: float = 0.1) -> list[dict[str, Any]]:
    """Sample the synthetic effort-proxy field over a bbox (real effort model)."""
    _ensure_backend_on_path()
    from app.engine.effort import effort_at

    cells: list[dict[str, Any]] = []
    lat = bbox["min_lat"]
    while lat <= bbox["max_lat"]:
        lon = bbox["min_lon"]
        while lon <= bbox["max_lon"]:
            cells.append({"lon": round(lon, 3), "lat": round(lat, 3),
                          "effort": round(effort_at(lon, lat), 4)})
            lon += step
        lat += step
    return cells


def conditions_readings(bbox: dict, time_iso: str | None) -> dict[str, Any]:
    """Return wave/wind/SST readings for a bbox at a time (real ingest)."""
    _ensure_backend_on_path()
    from app.agent.tools import get_conditions as _get_conditions

    b = [bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]]
    return _get_conditions(bbox=b, time=time_iso)


def plan_routes_real(trip_request: dict) -> dict[str, Any]:
    """Plan 2-3 routes for a trip request via the real A* router."""
    _ensure_backend_on_path()
    from app.agent.tools import plan_routes as _plan_routes

    return _plan_routes(trip_request=trip_request)


def estimate_fuel_real(route: dict, vessel: str) -> dict[str, Any]:
    """Estimate fuel for a route via the real vessel-burn model."""
    _ensure_backend_on_path()
    from app.agent.tools import estimate_fuel as _estimate_fuel

    return _estimate_fuel(route=route, vessel=vessel)


def render_brief_html(route: dict, language: str) -> str:
    """Render the one-page trip brief HTML for a route via the real renderer."""
    _ensure_backend_on_path()
    from app.api.trip import BriefBody, render_brief

    body = BriefBody.model_validate({"plan": route, "language": language})
    return render_brief(body)


def simulate_candidate(polygon: dict, prohibited: bool = True) -> dict[str, Any]:
    """Run the what-if simulator for a custom candidate polygon (real engine)."""
    _ensure_backend_on_path()
    from app.engine.simulator import Scenario, Simulator

    candidate = {
        "id": "mcp_candidate",
        "name": "MCP candidate zone",
        "kind": "fishing_closure" if prohibited else "slow_zone",
        "geometry": polygon,
        "prohibited": prohibited,
        "speed_limit_kn": None if prohibited else 10.0,
        "synthetic": True,
    }
    scenario = Scenario(
        id="mcp_candidate",
        name="MCP candidate zone",
        description="Candidate zone supplied via the MCP simulate_zone tool.",
        extra_zones=[candidate],
    )
    sim = Simulator()
    return sim.run_all([scenario])
