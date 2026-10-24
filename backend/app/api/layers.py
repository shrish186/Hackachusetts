"""Map layer endpoints: conditions, zones, and whale risk.

Implements design.md section 9:

    GET /api/layers/conditions?bbox&time
    GET /api/layers/zones?bbox&time
    GET /api/layers/risk?bbox&time&speed

Data is read from ``data/snapshots/`` via :mod:`app.api._snapshots`, honoring
``FATHOM_DEMO_MODE``. Every response carries a ``provenance`` block with
``source``, ``fetched_at``, and ``cached`` / ``synthetic`` flags so the UI can
badge cached and synthetic data (data-and-safety steering rule).

Records are validated through Anant's pydantic models in ``app.models`` so the
API and the engine speak the same language.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from app.api import _snapshots as snap
from app.api._risk_stub import stub_risk
from app.models import Conditions, Sighting, Zone

router = APIRouter(tags=["layers"])


def _parse_bbox_or_422(bbox: str | None) -> tuple[float, float, float, float] | None:
    """Parse the bbox query param, raising HTTP 422 on malformed input."""
    try:
        return snap.parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _zone_active_at(zone: Zone, when: datetime | None) -> bool:
    """Return True if the zone's active window contains ``when``.

    A zone with no bounds is always active. A ``None`` time means "ignore the
    time filter"; such zones are reported with ``active=True``.
    """
    if when is None:
        return True
    if zone.active_from is not None and when < zone.active_from:
        return False
    if zone.active_to is not None and when > zone.active_to:
        return False
    return True


@router.get("/layers/conditions")
def get_conditions(
    bbox: str | None = Query(
        None, description="min_lon,min_lat,max_lon,max_lat (decimal degrees)."
    ),
    time: datetime | None = Query(
        None, description="UTC time of interest (ISO-8601). Reserved for time filtering."
    ),
) -> dict[str, object]:
    """Return ocean/weather conditions for cells, with provenance.

    Conditions carry per-cell lon/lat only once the grid snapshot exists; until
    then we filter nothing spatially when a record has no coordinates. Each
    record is validated through :class:`app.models.Conditions`.
    """
    result = snap.load_snapshot("conditions")
    bounds = _parse_bbox_or_422(bbox)

    features: list[dict[str, object]] = []
    for raw in result.records:
        try:
            cond = Conditions.model_validate(raw)
        except ValidationError:
            continue
        # Conditions records key by cell_id; spatial filtering happens once the
        # grid snapshot (cell_id -> lon/lat) is joined by Lane A. Pass through.
        features.append(cond.model_dump(mode="json"))

    return {
        "layer": "conditions",
        "query": {"bbox": bbox, "time": time.isoformat() if time else None},
        "provenance": result.provenance(),
        "count": len(features),
        "features": features,
    }


@router.get("/layers/zones")
def get_zones(
    bbox: str | None = Query(
        None, description="min_lon,min_lat,max_lon,max_lat (decimal degrees)."
    ),
    time: datetime | None = Query(
        None, description="UTC time; zones outside their active window are returned as inactive."
    ),
) -> dict[str, object]:
    """Return regulatory/operational zones with active/inactive state.

    Inactive zones are returned (not hidden) with ``active=False`` so the UI can
    dim them (Req 2.3). Each record is validated through :class:`app.models.Zone`.
    """
    result = snap.load_snapshot("zones")
    _parse_bbox_or_422(bbox)  # validated; polygon-vs-bbox clipping is a later task

    features: list[dict[str, object]] = []
    for raw in result.records:
        try:
            zone = Zone.model_validate(raw)
        except ValidationError:
            continue
        payload = zone.model_dump(mode="json")
        payload["active"] = _zone_active_at(zone, time)
        features.append(payload)

    return {
        "layer": "zones",
        "query": {"bbox": bbox, "time": time.isoformat() if time else None},
        "provenance": result.provenance(),
        "count": len(features),
        "features": features,
    }


@router.get("/layers/risk")
def get_risk(
    bbox: str | None = Query(
        None, description="min_lon,min_lat,max_lon,max_lat (decimal degrees)."
    ),
    time: datetime | None = Query(
        None, description="UTC time of interest (ISO-8601)."
    ),
    speed: float = Query(
        10.0, gt=0.0, description="Planned vessel speed, knots (risk is monotonic in speed)."
    ),
) -> dict[str, object]:
    """Return a whale-risk grid for the given speed, with provenance.

    NOTE: risk is computed by a TEMPORARY stub (see ``_risk_stub.py``); the real
    model is Lane A's ``engine/risk.py`` (design.md section 5). While the stub is
    in use the response is flagged ``synthetic: true`` and must not be presented
    as calibrated.
    """
    bounds = _parse_bbox_or_422(bbox)
    sightings_snap = snap.load_snapshot("sightings")

    # Build a crude presence prior from sightings: each sighting contributes to
    # its own location. The real model does kernel smoothing + recency decay.
    cells: list[dict[str, object]] = []
    for raw in sightings_snap.records:
        try:
            s = Sighting.model_validate(raw)
        except ValidationError:
            continue
        if not snap.in_bbox(s.lon, s.lat, bounds):
            continue
        presence = min(1.0, s.count / 5.0)  # TODO(Lane A): real presence prior
        score = stub_risk(presence=presence, speed_kn=speed, is_land=False)
        cells.append(
            {
                "lon": s.lon,
                "lat": s.lat,
                "risk": round(score, 4),
                "factors": {
                    "presence": round(presence, 4),
                    "speed_kn": speed,
                },
            }
        )

    provenance = sightings_snap.provenance()
    # The stub is never calibrated data; force the synthetic flag on this layer.
    provenance["synthetic"] = True
    provenance["source"] = f"{provenance['source']} + risk stub (uncalibrated)"

    return {
        "layer": "risk",
        "query": {
            "bbox": bbox,
            "time": time.isoformat() if time else None,
            "speed_kn": speed,
        },
        "provenance": provenance,
        "count": len(cells),
        "cells": cells,
    }
