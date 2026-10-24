"""Zone ingest and normalization (Lane A, Task 1.2, Req 2).

Loads protection/regulatory zones from the bundled snapshot into validated
``Zone`` objects, and provides helpers for active-at-time filtering and
point-in-zone tests used by the router and the risk breakdown.

Every zone carries a source_url + source_updated, or is flagged synthetic
(enforced by the Zone model). Times are UTC.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from app.ingest.config import data_path
from app.models.geo import Zone

_DEFAULT_SNAPSHOT = ("snapshots", "zones.json")


def _as_utc(dt: datetime) -> datetime:
    """Return ``dt`` as timezone-aware UTC (assume UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_zones(path: Path | None = None) -> list[Zone]:
    """Load and validate all zones from the snapshot file.

    Raises pydantic ValidationError if a zone is malformed (e.g. a zone with no
    source_url that is not flagged synthetic).
    """
    if path is None:
        path = data_path(*_DEFAULT_SNAPSHOT)
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    raw = payload.get("zones", payload) if isinstance(payload, dict) else payload
    return [Zone.model_validate(z) for z in raw]


def is_active(zone: Zone, when: datetime) -> bool:
    """True if ``zone`` is active at ``when`` (UTC).

    A None ``active_from``/``active_to`` means unbounded on that side, so a zone
    with both None is always active (Req 2.3: inactive zones are dimmed, not
    hidden, so callers still get the full list and ask this per zone).
    """
    when = _as_utc(when)
    if zone.active_from is not None and when < _as_utc(zone.active_from):
        return False
    if zone.active_to is not None and when > _as_utc(zone.active_to):
        return False
    return True


def active_zones(zones: list[Zone], when: datetime) -> list[Zone]:
    """Subset of ``zones`` active at ``when`` (UTC)."""
    return [z for z in zones if is_active(z, when)]


@lru_cache(maxsize=64)
def _zone_geometry(zone_id: str, geom_json: str) -> BaseGeometry:
    """Cache a shapely geometry keyed by zone id + serialized geometry."""
    return shape(json.loads(geom_json))


def zone_shape(zone: Zone) -> BaseGeometry:
    """Return the shapely geometry for a zone (cached)."""
    return _zone_geometry(zone.id, json.dumps(zone.geometry, sort_keys=True))


def zones_containing(zones: list[Zone], lon: float, lat: float) -> list[Zone]:
    """Return zones whose polygon contains the point (lon, lat), degrees."""
    pt = Point(lon, lat)
    return [z for z in zones if zone_shape(z).covers(pt)]


def restriction_summary(zone: Zone) -> str:
    """Short, plain-language restriction summary for popups (Req 2.2).

    Never claims legal compliance; just states the known restriction.
    """
    if zone.prohibited:
        return "No entry while active."
    if zone.speed_limit_kn is not None:
        return f"Speed limit {zone.speed_limit_kn:g} kn while active."
    return "Advisory area; no speed or entry restriction recorded."


@lru_cache(maxsize=1)
def default_zones() -> tuple[Zone, ...]:
    """All zones from the bundled snapshot (cached, immutable tuple)."""
    return tuple(load_zones())
