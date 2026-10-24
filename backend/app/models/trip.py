"""Trip planning request model (Captain mode input)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Vessel classes the engine knows how to cost (fuel, comfort wave height, etc.).
Vessel = Literal["small_boat", "mid_trawler", "scalloper"]

# Languages for captain-facing briefs. Numbers and zone names must be identical
# across all three (data-and-safety steering rule).
Language = Literal["en", "pt", "es"]


class TripRequest(BaseModel):
    """A request to plan a trip from a port out to fishing grounds and back."""

    port: str = Field(..., description="Departure port identifier.")
    vessel: Vessel = Field(..., description="Vessel class.")
    cruise_kn: float = Field(..., gt=0.0, description="Intended cruise speed, knots.")
    max_hours: float = Field(..., gt=0.0, description="Maximum trip duration, hours.")
    depart_window: tuple[datetime, datetime] = Field(
        ..., description="UTC (earliest, latest) departure times."
    )
    target_ground: str | None = Field(
        None, description="Optional target fishing-ground identifier."
    )
    risk_pref: float = Field(
        ..., ge=0.0, le=1.0, description="0 = fastest route, 1 = safest route."
    )
    language: Language = Field("en", description="Output language for the brief.")

    @field_validator("depart_window")
    @classmethod
    def _window_ordered(cls, v: tuple[datetime, datetime]) -> tuple[datetime, datetime]:
        """The earliest departure must not be after the latest departure."""
        start, end = v
        if end < start:
            raise ValueError("depart_window end must not be earlier than start")
        return v
