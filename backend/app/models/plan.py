"""Route plan output model and its citation records."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A traceable source for a factual claim in agent/plan output.

    Every number, zone name, or date surfaced to the user must trace back to a
    tool result via `tool_call_id` (product + agent steering rules).
    """

    tool_call_id: str = Field(..., description='Tool call that produced the fact (e.g. "call_7").')
    tool: str = Field(..., description="Tool name that produced the fact.")
    claim: str = Field(..., description="The specific fact being cited.")
    source_url: str | None = Field(None, description="Underlying data source URL, if any.")


class RoutePlan(BaseModel):
    """A planned route with ETA, exposure, and supporting citations."""

    waypoints: list[tuple[float, float]] = Field(
        ..., description="Ordered (lon, lat) waypoints in decimal degrees."
    )
    eta_hours: float = Field(..., ge=0.0, description="Estimated time of arrival, hours.")
    fuel_est_l: float = Field(..., ge=0.0, description="Estimated fuel burn, liters (an estimate).")
    zones_crossed: list[str] = Field(
        default_factory=list, description="Ids of zones the route passes through."
    )
    max_wave_m: float = Field(..., ge=0.0, description="Maximum significant wave height en route, meters.")
    risk_exposure: float = Field(
        ..., ge=0.0, description="Integrated whale risk exposure = sum(risk * hours)."
    )
    effort_proxy: float = Field(
        ..., ge=0.0, description="Normalized historical effort access at destination (an estimate, not revenue)."
    )
    citations: list[Citation] = Field(
        default_factory=list, description="Sources backing the numbers in this plan."
    )
