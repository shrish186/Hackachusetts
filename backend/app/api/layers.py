"""Map layer endpoints: conditions, zones, and whale risk (task 1.5, design.md §9).

    GET /api/layers/conditions?bbox&time
    GET /api/layers/zones?bbox&time
    GET /api/layers/risk?bbox&time&speed

Data comes from Lane A's ingest modules (bundled snapshots in demo mode) and
the real risk model in ``app/engine/risk.py``. Every response has a
``provenance`` block (source, source_url, fetched_at, cached, synthetic,
demo_mode) and an ``items`` array whose elements match frontend/src/api/types.ts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from shapely.geometry import box

from app.ingest.conditions import demo_mode, get_conditions as ingest_conditions
from app.ingest.config import data_path
from app.ingest.grid import default_grid, land_mask_array
from app.ingest.zones import default_zones, is_active, restriction_summary, zone_shape
from app.engine.risk import load_sightings, risk_breakdown

router = APIRouter(tags=["layers"])

BBox = tuple[float, float, float, float]
SpeedQ = Annotated[float, Query(gt=0.0, le=40.0, description="Planned vessel speed, knots.")]
BBoxQ = Annotated[
    str | None,
    Query(max_length=100, description="min_lon,min_lat,max_lon,max_lat (decimal degrees)."),
]
TimeQ = Annotated[datetime | None, Query(description="UTC time of interest (ISO-8601).")]

#: Cells below this risk are left out of the risk layer to keep payloads small.
MIN_RISK_REPORTED = 0.001


def parse_bbox(raw: str | None) -> BBox | None:
    """Parse and bound-check 'min_lon,min_lat,max_lon,max_lat'. HTTP 422 if invalid."""
    if raw is None:
        return None
    try:
        parts = [float(p) for p in raw.split(",")]
    except ValueError:
        raise HTTPException(422, "bbox must be four numbers: min_lon,min_lat,max_lon,max_lat") from None
    if len(parts) != 4:
        raise HTTPException(422, "bbox must be four numbers: min_lon,min_lat,max_lon,max_lat")
    min_lon, min_lat, max_lon, max_lat = parts
    if not (-180 <= min_lon <= max_lon <= 180 and -90 <= min_lat <= max_lat <= 90):
        raise HTTPException(422, "bbox out of range or min greater than max")
    return (min_lon, min_lat, max_lon, max_lat)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def in_bbox(lon: float, lat: float, bbox: BBox | None) -> bool:
    if bbox is None:
        return True
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def cell_center(cell_id: str) -> tuple[float, float] | None:
    """(lon, lat) centroid of an "ix_iy" cell on the study grid, or None."""
    try:
        ix, iy = (int(p) for p in cell_id.split("_"))
    except ValueError:
        return None
    g = default_grid()
    if not (0 <= ix < g.nx and 0 <= iy < g.ny):
        return None
    return g.center(ix, iy)


@lru_cache(maxsize=1)
def land_mask():
    return land_mask_array(default_grid())


@lru_cache(maxsize=8)
def snapshot_meta(name: str) -> dict[str, Any]:
    """The ``metadata`` block of a bundled snapshot file ({} if absent)."""
    path = data_path("snapshots", name)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return payload.get("metadata", {}) if isinstance(payload, dict) else {}


def _iso(dt: datetime | None) -> str | None:
    return as_utc(dt).isoformat().replace("+00:00", "Z") if dt else None


def zones_provenance() -> dict[str, Any]:
    meta = snapshot_meta("zones.json")
    zones = default_zones()
    return {
        "source": meta.get("source", "zones.json (bundled snapshot)"),
        "source_url": meta.get("source_url"),
        "fetched_at": meta.get("fetched_at"),
        "cached": True,
        # The layer is synthetic if any zone in it is.
        "synthetic": any(z.synthetic for z in zones) or bool(meta.get("synthetic", False)),
        "demo_mode": demo_mode(),
    }


def sightings_provenance() -> dict[str, Any]:
    meta = snapshot_meta("sightings.json")
    return {
        "source": "app.engine.risk + " + str(meta.get("source", "sightings.json")),
        "source_url": meta.get("source_url"),
        "fetched_at": meta.get("fetched_at"),
        "cached": True,
        # Risk parameters are TODO-VERIFY (config/risk.yaml); treat as synthetic
        # unless both the sightings are real and the parameters are verified.
        "synthetic": True,
        "demo_mode": demo_mode(),
    }


def conditions_records(when: datetime | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Latest conditions per cell at or before ``when`` (or latest overall)."""
    result = ingest_conditions(prefer_live=False if demo_mode() else None)
    provenance = {
        "source": result.source,
        "source_url": result.source_url,
        "fetched_at": _iso(result.fetched_at),
        "cached": result.cached,
        "synthetic": result.synthetic,
        "demo_mode": demo_mode(),
    }
    when = as_utc(when)
    best: dict[str, Any] = {}
    for c in result.conditions:
        t = as_utc(c.time)
        if when is not None and t > when:
            continue
        cur = best.get(c.cell_id)
        if cur is None or t > as_utc(cur.time):
            best[c.cell_id] = c
    if when is not None and not best:
        # Nothing at or before the requested time: fall back to the earliest records.
        for c in result.conditions:
            cur = best.get(c.cell_id)
            if cur is None or as_utc(c.time) < as_utc(cur.time):
                best[c.cell_id] = c
    items = []
    for c in best.values():
        item = c.model_dump(mode="json")
        center = cell_center(c.cell_id)
        item["lon"], item["lat"] = center if center else (None, None)
        item["cached"] = result.cached
        item["synthetic"] = result.synthetic
        items.append(item)
    return items, provenance


@router.get("/layers/conditions")
def get_conditions(bbox: BBoxQ = None, time: TimeQ = None) -> dict[str, Any]:
    """Conditions per cell (Req 1). bbox is applied via the grid cell centroid."""
    bounds = parse_bbox(bbox)
    items, provenance = conditions_records(time)
    items = [i for i in items if i["lon"] is not None and in_bbox(i["lon"], i["lat"], bounds)]
    return {
        "layer": "conditions",
        "query": {"bbox": bbox, "time": _iso(time)},
        "provenance": provenance,
        "count": len(items),
        "items": items,
    }


def zone_items(bounds: BBox | None, when: datetime) -> list[dict[str, Any]]:
    clip = box(*bounds) if bounds else None
    items = []
    for z in default_zones():
        if clip is not None and not zone_shape(z).intersects(clip):
            continue
        item = z.model_dump(mode="json")
        item["active"] = is_active(z, when)
        item["restriction"] = restriction_summary(z)
        item["cached"] = True
        items.append(item)
    return items


@router.get("/layers/zones")
def get_zones(bbox: BBoxQ = None, time: TimeQ = None) -> dict[str, Any]:
    """Zones with active state at ``time`` (default: now). Inactive zones are kept (Req 2.3)."""
    bounds = parse_bbox(bbox)
    when = as_utc(time) or datetime.now(timezone.utc)
    items = zone_items(bounds, when)
    return {
        "layer": "zones",
        "query": {"bbox": bbox, "time": _iso(when)},
        "provenance": zones_provenance(),
        "count": len(items),
        "items": items,
    }


@lru_cache(maxsize=1)
def _sightings():
    return tuple(load_sightings())


def risk_items(bounds: BBox | None, when: datetime, speed_kn: float) -> list[dict[str, Any]]:
    g = default_grid()
    mask = land_mask()
    sightings = _sightings()
    items = []
    for iy in range(g.ny):
        for ix in range(g.nx):
            if mask[iy, ix]:
                continue
            lon, lat = g.center(ix, iy)
            if not in_bbox(lon, lat, bounds):
                continue
            b = risk_breakdown(g.cell_id(ix, iy), lon, lat, when, speed_kn, sightings)
            if b.risk < MIN_RISK_REPORTED:
                continue
            items.append(
                {
                    "cell_id": b.cell_id,
                    "lon": round(lon, 4),
                    "lat": round(lat, 4),
                    "risk": round(b.risk, 4),
                    "factors": {
                        "presence": round(b.presence, 4),
                        "recency": round(b.recency, 4),
                        "lethality": round(b.lethality, 4),
                    },
                    "cached": True,
                    "synthetic": True,
                }
            )
    return items


@router.get("/layers/risk")
def get_risk(bbox: BBoxQ = None, time: TimeQ = None, speed: SpeedQ = 10.0) -> dict[str, Any]:
    """Whale-risk grid from app/engine/risk.py with per-cell factors (Req 3, 3.4)."""
    bounds = parse_bbox(bbox)
    when = as_utc(time) or datetime.now(timezone.utc)
    items = risk_items(bounds, when, speed)
    return {
        "layer": "risk",
        "query": {"bbox": bbox, "time": _iso(when), "speed_kn": speed},
        "provenance": sightings_provenance(),
        "count": len(items),
        "items": items,
    }
