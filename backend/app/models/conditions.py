"""Environmental conditions per grid cell and time slice."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Conditions(BaseModel):
    """Ocean/weather conditions for one cell at one time.

    Every conditions record carries its `source` and `fetched_at` so the UI can
    badge data as cached/synthetic (tech + data-and-safety steering rules).
    """

    cell_id: str = Field(..., description='Grid cell id, formatted "ix_iy".')
    time: datetime = Field(..., description="UTC time the conditions apply to.")
    wave_m: float = Field(..., ge=0.0, description="Significant wave height, meters.")
    wind_kn: float = Field(..., ge=0.0, description="Wind speed, knots.")
    sst_c: float | None = Field(None, description="Sea-surface temperature, degrees Celsius.")
    source: str = Field(..., description="Data source name (or 'synthetic').")
    fetched_at: datetime = Field(..., description="UTC time the data was fetched/cached.")
