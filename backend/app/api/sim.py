"""Policy what-if simulator API (Lane D, design.md section 9, Req 6).

Endpoints::

    GET  /api/sim/scenarios   -> the preloaded candidate scenarios
    POST /api/sim/run         -> run a scenario id OR a custom candidate polygon

Input is validated with pydantic. The run accepts either a known ``scenario_id``
(checked against the preloaded allowlist) or a GeoJSON ``polygon`` that is
geometry-validated; it never builds a filesystem path from request input
(see docs/SECURITY_FINDINGS.md). Zones loaded as the current baseline come from
the bundled snapshot and carry their own synthetic/source flags.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.api import _snapshots as snap
from app.engine.simulator import (
    Scenario,
    Simulator,
    preloaded_scenarios,
)

router = APIRouter(tags=["sim"])


def _current_zones() -> list[dict]:
    """Load the zones active in the baseline from the bundled snapshot."""
    result = snap.load_snapshot("zones")
    return list(result.records)


class PolygonModel(BaseModel):
    """A validated GeoJSON Polygon for a custom candidate zone."""

    type: Literal["Polygon"] = Field(..., description='Must be "Polygon".')
    coordinates: list[list[list[float]]] = Field(..., description="Polygon rings.")

    @model_validator(mode="after")
    def _valid_ring(self) -> "PolygonModel":
        if not self.coordinates or not self.coordinates[0]:
            raise ValueError("polygon must have a non-empty outer ring")
        ring = self.coordinates[0]
        if len(ring) < 4:
            raise ValueError("polygon ring needs at least 4 positions (closed)")
        for pt in ring:
            if len(pt) < 2:
                raise ValueError("each position needs at least lon,lat")
            lon, lat = pt[0], pt[1]
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
    def _exactly_one(self) -> "SimRunRequest":
        if bool(self.scenario_id) == bool(self.polygon):
            raise ValueError("provide exactly one of scenario_id or polygon")
        return self


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


@router.post("/sim/run")
def run_sim(req: SimRunRequest) -> dict[str, Any]:
    """Run one scenario (by id) or a custom candidate polygon and return deltas.

    Returns the baseline, per-option percent deltas, the Pareto frontier flag,
    and trilingual plain-language summaries with identical numbers.
    """
    sim = Simulator(current_zones=_current_zones())

    if req.scenario_id:
        allow = {s.id: s for s in preloaded_scenarios()}
        scenario = allow.get(req.scenario_id)
        if scenario is None:
            raise HTTPException(
                status_code=422,
                detail=f"unknown scenario_id; valid ids: {sorted(allow)}",
            )
        # Run against the full preloaded set so the frontier is meaningful, then
        # surface the requested option alongside the comparison set.
        result = sim.run_all(preloaded_scenarios())
        result["requested"] = req.scenario_id
        return result

    # Custom polygon -> build an ad-hoc scenario.
    candidate = {
        "id": "custom_candidate",
        "name": "Custom candidate zone",
        "kind": "slow_zone" if not req.prohibited else "fishing_closure",
        "geometry": req.polygon.model_dump(),  # type: ignore[union-attr]
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
    # Compare the custom option against the preloaded ones for a useful frontier.
    result = sim.run_all([custom, *preloaded_scenarios()])
    result["requested"] = "custom_candidate"
    return result
