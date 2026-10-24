"""Geospatial domain models: grid cells, regulatory zones, whale sightings.

Longitudes/latitudes are WGS84 decimal degrees. Timestamps are UTC.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# The zone kinds Fathom understands. Kept as a type alias so the API, engine,
# and MCP tools validate against the same closed set.
ZoneKind = Literal[
    "whale_sma",          # seasonal management area (speed limit)
    "slow_zone",          # dynamic/voluntary slow zone
    "fishing_closure",    # regulated closure area
    "wind_lease",         # offshore wind lease area
    "wind_construction",  # active wind construction area
]


class Cell(BaseModel):
    """A single cell of the study-area grid.

    `id` encodes the integer grid index as "ix_iy". `lon`/`lat` are the cell
    centroid in decimal degrees.
    """

    id: str = Field(..., description='Grid id, formatted "ix_iy".')
    lon: float = Field(..., ge=-180.0, le=180.0, description="Centroid longitude, decimal degrees.")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Centroid latitude, decimal degrees.")
    is_land: bool = Field(..., description="True if the cell is land (never routed through).")


class Zone(BaseModel):
    """A regulatory or operational area with optional active time window.

    Per the data-and-safety steering rule: if there is no `source_url` for a
    zone, it must be marked `synthetic=True` so the UI can badge it.
    """

    id: str = Field(..., description="Stable zone identifier.")
    name: str = Field(..., description="Human-readable zone name.")
    kind: ZoneKind = Field(..., description="Zone category.")
    geometry: dict = Field(..., description="GeoJSON geometry (Polygon/MultiPolygon).")
    active_from: datetime | None = Field(
        None, description="UTC start of the active window; None means always active."
    )
    active_to: datetime | None = Field(
        None, description="UTC end of the active window; None means no end."
    )
    speed_limit_kn: float | None = Field(
        None, ge=0.0, description="Speed limit in knots inside the zone, if any."
    )
    prohibited: bool = Field(
        False, description="True if entry is prohibited entirely (impassable when active)."
    )
    source_url: str | None = Field(
        None, description="Authoritative source URL. None requires synthetic=True."
    )
    source_updated: datetime | None = Field(
        None, description="UTC timestamp the source was last updated."
    )
    synthetic: bool = Field(
        False, description="True if hand-digitized/seeded without an authoritative source."
    )

    @field_validator("active_to")
    @classmethod
    def _active_window_ordered(cls, v: datetime | None, info) -> datetime | None:
        """Ensure active_to is not before active_from when both are present."""
        start = info.data.get("active_from")
        if v is not None and start is not None and v < start:
            raise ValueError("active_to must not be earlier than active_from")
        return v

    @model_validator(mode="after")
    def _synthetic_or_sourced(self) -> "Zone":
        """A zone without a source_url must be flagged synthetic (data-and-safety)."""
        if not self.synthetic and not self.source_url:
            raise ValueError("zone without a source_url must set synthetic=True")
        return self


class Sighting(BaseModel):
    """A whale sighting observation, used to build presence/recency risk."""

    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude, decimal degrees.")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude, decimal degrees.")
    observed_at: datetime = Field(..., description="UTC time of the sighting.")
    count: int = Field(..., ge=0, description="Number of animals observed.")
    source: str = Field(..., description="Dataset/source name (or 'synthetic').")
