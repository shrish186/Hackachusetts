"""Policy what-if simulator API (Lane D, design.md section 9, Req 6).

Endpoints::

    GET  /api/sim/scenarios   -> the preloaded candidate scenarios
    POST /api/sim/run         -> a preset scenario id (served precomputed) OR a
                                 custom candidate polygon (computed live, bounded)

**Performance (the critical live bug).** Running the live A* router over the
200-trip fleet for all preset scenarios took >20 s and returned a 504. Presets
never change, so they are precomputed at build time by
``scripts/precompute_sim.py`` into ``data/snapshots/sim_results.json`` and served
from there in well under 300 ms. The live path is kept **only** for user-drawn
custom polygons, and it is bounded:

* vertices capped at 200 and the polygon clipped to the study area,
* a hard wall-clock budget (``CUSTOM_BUDGET_S``) enforced in a worker thread; on
  overrun we return ``422 polygon too complex, simplify it`` rather than a 504,
* at most one live simulation per process (an ``asyncio`` semaphore); a second
  concurrent request gets ``429 busy, retry in a few seconds``.

Input is validated with pydantic; the run never builds a filesystem path from
request input (see docs/SECURITY_FINDINGS.md).
"""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.engine.simulator import (
    Scenario,
    Simulator,
    baseline_access_explanation,
    preloaded_scenarios,
)
from app.ingest.config import data_path
from app.ingest.zones import default_zones

router = APIRouter(tags=["sim"])

# Study-area bbox (config/study_area.yaml: 41N-43.5N, 71W-69W). Custom polygons
# are clipped to this; a polygon entirely outside it is rejected.
STUDY_BBOX = (-71.0, 41.0, -69.0, 43.5)
# Hard caps for custom-polygon requests (task 2).
MAX_VERTICES = 200
CUSTOM_BUDGET_S = 8.0
# Coarser fleet for the live custom path so it fits the budget; presets use 200.
CUSTOM_FLEET_SIZE = 80

# One live simulation at a time per process. A second concurrent request fails
# fast with 429 rather than piling up and timing out.
_SIM_SEMAPHORE = asyncio.Semaphore(1)
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sim")


@lru_cache(maxsize=1)
def _current_zones_cached() -> tuple[dict, ...]:
    """Baseline zones from Lane A's ingest as plain dicts (cached, immutable)."""
    zones: list[dict] = []
    for z in default_zones():
        zones.append(
            {
                "id": z.id,
                "name": z.name,
                "kind": z.kind,
                "geometry": z.geometry,
                "prohibited": z.prohibited,
                "speed_limit_kn": z.speed_limit_kn,
                "synthetic": z.synthetic,
            }
        )
    return tuple(zones)


def _current_zones() -> list[dict]:
    """Baseline zones as a fresh list (callers may mutate their own copy)."""
    return [dict(z) for z in _current_zones_cached()]


@lru_cache(maxsize=1)
def _precomputed() -> dict[str, Any] | None:
    """Load the committed preset results, or None if the snapshot is missing.

    Cached for the process lifetime: the file is a build artifact and does not
    change at runtime, so this keeps preset responses at a JSON lookup.
    """
    path = Path(data_path("snapshots", "sim_results.json"))
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


class PolygonModel(BaseModel):
    """A validated GeoJSON Polygon for a custom candidate zone."""

    type: Literal["Polygon"] = Field(..., description='Must be "Polygon".')
    coordinates: list[list[list[float]]] = Field(..., description="Polygon rings.")

    @model_validator(mode="after")
    def _valid_ring(self) -> PolygonModel:
        if not self.coordinates or not self.coordinates[0]:
            raise ValueError("polygon must have a non-empty outer ring")
        ring = self.coordinates[0]
        if len(ring) < 4:
            raise ValueError("polygon ring needs at least 4 positions (closed)")
        if len(ring) > MAX_VERTICES:
            raise ValueError(
                f"polygon has too many vertices ({len(ring)} > {MAX_VERTICES}); simplify it"
            )
        for pt in ring:
            if len(pt) < 2:
                raise ValueError("each position needs at least lon,lat")
            lon, lat = pt[0], pt[1]
            # Reject NaN/inf (a NaN comparison is always False, so test equality).
            if lon != lon or lat != lat:
                raise ValueError("coordinates must be finite numbers (no NaN)")
            if lon in (float("inf"), float("-inf")) or lat in (float("inf"), float("-inf")):
                raise ValueError("coordinates must be finite numbers (no inf)")
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                raise ValueError("coordinates out of range")
        if ring[0] != ring[-1]:
            raise ValueError("polygon ring must be closed (first == last)")
        return self


class SimRunRequest(BaseModel):
    """Run request: exactly one of ``scenario_id`` or ``polygon``."""

    scenario_id: str | None = Field(None, description="A preloaded scenario id.")
    polygon: PolygonModel | None = Field(None, description="A custom candidate polygon.")
    prohibited: bool = Field(
        True, description="For a custom polygon: no-entry (True) or speed-limited (False)."
    )
    speed_limit_kn: float | None = Field(
        None, ge=0.0, description="Speed cap for a custom speed-limited polygon."
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> SimRunRequest:
        if bool(self.scenario_id) == bool(self.polygon):
            raise ValueError("provide exactly one of scenario_id or polygon")
        return self


def _polygon_area_deg2(ring: list[list[float]]) -> float:
    """Shoelace area (square degrees) of a polygon ring; always non-negative."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _bbox_overlaps_study(ring: list[list[float]]) -> bool:
    """True if the polygon's bounding box overlaps the study area."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    min_lon, min_lat, max_lon, max_lat = STUDY_BBOX
    return not (max(xs) < min_lon or min(xs) > max_lon or max(ys) < min_lat or min(ys) > max_lat)


def _validate_custom_geometry(ring: list[list[float]]) -> None:
    """Reject zero-area and fully-out-of-study-area polygons with a clear 422."""
    if _polygon_area_deg2(ring) <= 1e-9:
        raise HTTPException(status_code=422, detail="polygon has zero area; draw a real region")
    if not _bbox_overlaps_study(ring):
        raise HTTPException(
            status_code=422,
            detail="polygon is outside the study area (roughly 41-43.5N, 71-69W)",
        )


@router.get("/sim/scenarios")
def get_scenarios() -> dict[str, Any]:
    """List the preloaded what-if scenarios."""
    scenarios = preloaded_scenarios()
    return {
        "count": len(scenarios),
        "scenarios": [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in scenarios
        ],
    }


def _serve_preset(scenario_id: str) -> dict[str, Any]:
    """Return the precomputed result for a preset id (fast path).

    Falls back to a live full run only if the snapshot is missing (e.g. a dev
    checkout that never ran the precompute script); that path is the old,
    slower behavior and should not occur in a built deployment.
    """
    allow = {s.id for s in preloaded_scenarios()}
    if scenario_id not in allow:
        raise HTTPException(
            status_code=422,
            detail=f"unknown scenario_id; valid ids: {sorted(allow)}",
        )
    pre = _precomputed()
    if pre is not None:
        result = dict(pre)
        result["requested"] = scenario_id
        result["served_from"] = "precomputed"
        # Ensure the plain-language baseline access-loss note is present even if
        # the committed snapshot predates it (keeps the served shape current).
        if "baseline_explanation" not in result:
            base = result.get("baseline", {})
            result["baseline_explanation"] = baseline_access_explanation(
                int(base.get("access_lost", 0)), int(base.get("trips", 0))
            )
        return result
    # Fallback (snapshot missing): compute live. Keeps correctness over speed.
    sim = Simulator(current_zones=_current_zones())
    result = sim.run_all(preloaded_scenarios())
    result["requested"] = scenario_id
    result["served_from"] = "live-fallback (precompute snapshot missing)"
    return result


def _run_custom_blocking(req: SimRunRequest) -> dict[str, Any]:
    """Build and run the custom-polygon scenario (runs in a worker thread)."""
    polygon = req.polygon.model_dump()  # type: ignore[union-attr]
    candidate = {
        "id": "custom_candidate",
        "name": "Custom candidate zone",
        "kind": "slow_zone" if not req.prohibited else "fishing_closure",
        "geometry": polygon,
        "prohibited": req.prohibited,
        "speed_limit_kn": req.speed_limit_kn,
        "synthetic": True,
    }
    custom = Scenario(
        id="custom_candidate",
        name="Custom candidate zone",
        description="User-drawn candidate protection zone.",
        extra_zones=[candidate],
    )
    # Coarser fleet so the live run fits the time budget; compared against the
    # presets so the frontier stays meaningful.
    sim = Simulator(current_zones=_current_zones(), fleet_size=CUSTOM_FLEET_SIZE)
    result = sim.run_all([custom, *preloaded_scenarios()])
    result["requested"] = "custom_candidate"
    result["served_from"] = "live"
    return result


@router.post("/sim/run")
async def run_sim(req: SimRunRequest) -> dict[str, Any]:
    """Run one scenario (preset, precomputed) or a custom polygon (live, bounded).

    Presets are served from the committed precompute snapshot in milliseconds.
    Custom polygons run live under a hard time budget, single-flight, and return
    a clear 422 on overrun instead of a 504.
    """
    if req.scenario_id:
        return _serve_preset(req.scenario_id)

    # Custom polygon: validate geometry, then run live under guards.
    ring = req.polygon.coordinates[0]  # type: ignore[union-attr]
    _validate_custom_geometry(ring)

    if _SIM_SEMAPHORE.locked():
        raise HTTPException(status_code=429, detail="busy, retry in a few seconds")

    async with _SIM_SEMAPHORE:
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(_EXECUTOR, _run_custom_blocking, req)
        try:
            return await asyncio.wait_for(future, timeout=CUSTOM_BUDGET_S)
        except (TimeoutError, FuturesTimeout):
            # The worker thread keeps running to completion, but we stop waiting
            # and tell the caller to simplify rather than hang/504.
            raise HTTPException(
                status_code=422,
                detail="polygon too complex, simplify it",
            ) from None
