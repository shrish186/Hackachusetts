"""Agent tools (Lane B, task 6, design.md §7).

Plain Python functions with JSON schemas. The in-app agent calls them through
:func:`call_tool`, and the fathom MCP server can wrap ``TOOLS`` directly. Every
result is JSON-serializable and carries ``source``, ``fetched_at`` and a
``synthetic`` flag so citations can point at it. No LLM logic lives here.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

from app.api.layers import conditions_records, risk_items, sightings_provenance, zone_items, zones_provenance
from app.engine import routing
from app.engine.effort import SYNTHETIC as EFFORT_SYNTHETIC, effort_at
from app.ingest.grid import default_grid
from app.models import TripRequest

BBox = tuple[float, float, float, float]


def _bbox(v: Any) -> BBox | None:
    if v is None:
        return None
    if isinstance(v, dict):
        v = (v["min_lon"], v["min_lat"], v["max_lon"], v["max_lat"])
    b = tuple(float(x) for x in v)
    if len(b) != 4 or not (-180 <= b[0] <= b[2] <= 180 and -90 <= b[1] <= b[3] <= 90):
        raise ValueError("bbox must be [min_lon, min_lat, max_lon, max_lat]")
    return b  # type: ignore[return-value]


def _when(v: Any) -> datetime:
    if v is None:
        return datetime.now(timezone.utc)
    dt = v if isinstance(v, datetime) else datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def get_conditions(bbox: Any = None, time: Any = None) -> dict[str, Any]:
    """Wave (m), wind (kn), SST (C) per cell, latest at or before ``time``."""
    items, prov = conditions_records(_when(time) if time else None)
    b = _bbox(bbox)
    items = [i for i in items if i["lon"] is not None and (b is None or (b[0] <= i["lon"] <= b[2] and b[1] <= i["lat"] <= b[3]))]
    waves = [i["wave_m"] for i in items]
    winds = [i["wind_kn"] for i in items]
    return {
        **prov,
        "count": len(items),
        "max_wave_m": max(waves) if waves else None,
        "max_wind_kn": max(winds) if winds else None,
        "readings": [{k: i[k] for k in ("cell_id", "lon", "lat", "time", "wave_m", "wind_kn", "sst_c", "source")} for i in items],
    }


def get_zones(bbox: Any = None, time: Any = None) -> dict[str, Any]:
    """Zones with active state at ``time`` plus restriction text and source URL."""
    when = _when(time)
    items = zone_items(_bbox(bbox), when)
    return {
        **zones_provenance(),
        "time": _iso(when),
        "count": len(items),
        "active_count": sum(1 for z in items if z["active"]),
        "zones": [
            {k: z[k] for k in ("id", "name", "kind", "active", "prohibited", "speed_limit_kn",
                               "active_from", "active_to", "restriction", "source_url", "synthetic")}
            for z in items
        ],
    }


def get_whale_risk(bbox: Any = None, time: Any = None, speed_kn: float = 10.0, top_n: int = 5) -> dict[str, Any]:
    """Risk summary (max, mean) and the top ``top_n`` cells with factor breakdown."""
    if not (0 < float(speed_kn) <= 40):
        raise ValueError("speed_kn must be in (0, 40]")
    when = _when(time)
    items = risk_items(_bbox(bbox), when, float(speed_kn))
    risks = [c["risk"] for c in items]
    top = sorted(items, key=lambda c: c["risk"], reverse=True)[: max(1, min(int(top_n), 20))]
    return {
        **sightings_provenance(),
        "time": _iso(when),
        "speed_kn": float(speed_kn),
        "scale": [0, 1],
        "cells_reported": len(items),
        "max_risk": round(max(risks), 3) if risks else 0.0,
        "mean_risk": round(sum(risks) / len(risks), 3) if risks else 0.0,
        "top_cells": [{k: c[k] for k in ("cell_id", "lon", "lat", "risk", "factors")} for c in top],
    }


def plan_routes(trip_request: dict[str, Any]) -> dict[str, Any]:
    """2-3 ranked RoutePlans for a TripRequest, or a 'no legal route' message."""
    req = TripRequest.model_validate(trip_request)
    out = routing.plan_routes(req)
    return {
        "source": "app.engine.routing (A* on study grid) + " + str(out["data"]["source"]),
        "fetched_at": out["data"]["fetched_at"],
        # Fuel/vessel parameters are estimates (config/vessels.yaml synthetic: true).
        "synthetic": True,
        "estimate": True,
        **{k: out[k] for k in ("ok", "plans", "message", "origin", "dest", "depart", "port", "ground")},
        "zone_names": routing.zone_names(),
    }


def get_effort_proxy(bbox: Any = None, month: int | None = None, top_n: int = 5) -> dict[str, Any]:
    """Normalized fishing-effort proxy (0..1) over the grid. An ESTIMATE, not catch or revenue."""
    if month is not None and not (1 <= int(month) <= 12):
        raise ValueError("month must be 1..12")
    g = default_grid()
    b = _bbox(bbox)
    cells = []
    for iy in range(0, g.ny, 2):
        for ix in range(0, g.nx, 2):
            lon, lat = g.center(ix, iy)
            if b is None or (b[0] <= lon <= b[2] and b[1] <= lat <= b[3]):
                cells.append({"cell_id": g.cell_id(ix, iy), "lon": round(lon, 4), "lat": round(lat, 4),
                              "effort": round(effort_at(lon, lat), 3)})
    top = sorted(cells, key=lambda c: c["effort"], reverse=True)[: max(1, min(int(top_n), 20))]
    return {
        "source": "app.engine.effort (seeded from config/ports.yaml fishing grounds)",
        "fetched_at": None,
        "synthetic": bool(EFFORT_SYNTHETIC),
        "estimate": True,
        "month": month,
        "scale": [0, 1],
        "note": "Effort proxy is an estimate of fishing activity, not catch or revenue. Month is not yet used.",
        "max_effort": max((c["effort"] for c in cells), default=0.0),
        "top_cells": top,
    }


def estimate_fuel(route: dict[str, Any], vessel: str) -> dict[str, Any]:
    """Fuel estimate (liters) for a route's waypoints at the vessel's cruise speed."""
    vcfg = routing.vessels_config().get(vessel)
    if vcfg is None:
        raise ValueError(f"unknown vessel '{vessel}'")
    pts = [tuple(map(float, p)) for p in route.get("waypoints", [])]
    nm = 0.0
    for (lo1, la1), (lo2, la2) in zip(pts, pts[1:]):
        nm += 60.0 * math.hypot((lo2 - lo1) * math.cos(math.radians((la1 + la2) / 2)), la2 - la1)
    speed = float(route.get("cruise_kn") or vcfg["cruise_kn"])
    hours = nm / speed if speed > 0 else 0.0
    liters = float(vcfg["fuel_burn_l_per_h"]) * hours * (speed / float(vcfg["cruise_kn"])) ** 2
    return {
        "source": "config/vessels.yaml fuel_burn_l_per_h",
        "fetched_at": None,
        "synthetic": True,
        "estimate": True,
        "vessel": vessel,
        "distance_nm": round(nm, 1),
        "hours": round(hours, 2),
        "fuel_est_l": round(liters, 1),
    }


ToolFn = Callable[..., dict[str, Any]]

_BBOX_SCHEMA = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4,
                "description": "[min_lon, min_lat, max_lon, max_lat], decimal degrees"}
_TIME_SCHEMA = {"type": "string", "format": "date-time", "description": "UTC ISO-8601"}

TOOLS: dict[str, dict[str, Any]] = {
    "get_conditions": {
        "fn": get_conditions,
        "description": "Wave height, wind and sea-surface temperature readings with source and fetch time.",
        "input_schema": {"type": "object", "properties": {"bbox": _BBOX_SCHEMA, "time": _TIME_SCHEMA}},
    },
    "get_zones": {
        "fn": get_zones,
        "description": "Protection zones (whale SMAs, slow zones, closures, wind areas) with active state and source URLs.",
        "input_schema": {"type": "object", "properties": {"bbox": _BBOX_SCHEMA, "time": _TIME_SCHEMA}},
    },
    "get_whale_risk": {
        "fn": get_whale_risk,
        "description": "Whale encounter risk (0-1) summary and top cells with presence/recency/lethality factors.",
        "input_schema": {"type": "object", "properties": {
            "bbox": _BBOX_SCHEMA, "time": _TIME_SCHEMA,
            "speed_kn": {"type": "number", "exclusiveMinimum": 0, "maximum": 40},
            "top_n": {"type": "integer", "minimum": 1, "maximum": 20}}},
    },
    "plan_routes": {
        "fn": plan_routes,
        "description": "Plan 2-3 ranked routes for a trip request, avoiding land and active closed zones.",
        "input_schema": {"type": "object", "required": ["trip_request"], "properties": {
            "trip_request": TripRequest.model_json_schema()}},
    },
    "get_effort_proxy": {
        "fn": get_effort_proxy,
        "description": "Estimated fishing-effort proxy (0-1). Not catch or revenue.",
        "input_schema": {"type": "object", "properties": {
            "bbox": _BBOX_SCHEMA, "month": {"type": "integer", "minimum": 1, "maximum": 12},
            "top_n": {"type": "integer", "minimum": 1, "maximum": 20}}},
    },
    "estimate_fuel": {
        "fn": estimate_fuel,
        "description": "Estimated fuel in liters for a route's waypoints and a vessel class.",
        "input_schema": {"type": "object", "required": ["route", "vessel"], "properties": {
            "route": {"type": "object", "properties": {
                "waypoints": {"type": "array", "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}},
                "cruise_kn": {"type": "number", "exclusiveMinimum": 0}}},
            "vessel": {"type": "string", "enum": ["small_boat", "mid_trawler", "scalloper"]}}},
    },
}


def tool_schemas() -> list[dict[str, Any]]:
    """Tool specs in the Anthropic/MCP shape: name, description, input_schema."""
    return [{"name": n, "description": t["description"], "input_schema": t["input_schema"]} for n, t in TOOLS.items()]


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run a tool by name with keyword args. Raises KeyError for unknown tools."""
    return TOOLS[name]["fn"](**args)
