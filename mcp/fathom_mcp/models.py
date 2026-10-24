"""Pydantic input models for the Fathom MCP tools.

These validate the *arguments* each tool accepts (design.md section 7). They are
intentionally small and self-contained so the MCP package does not depend on the
backend package at import time; where a tool takes a domain object (a trip
request or a route plan), it is accepted as a plain ``dict`` and validated
loosely here. The real engine (Lane A/B) owns the authoritative domain models in
``backend/app/models``.

All coordinates are decimal degrees (lon/lat). All times are UTC.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class BBox(BaseModel):
    """A geographic bounding box in decimal degrees (lon/lat, WGS84)."""

    min_lon: float = Field(..., ge=-180.0, le=180.0, description="West edge, degrees.")
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="South edge, degrees.")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="East edge, degrees.")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="North edge, degrees.")

    @model_validator(mode="after")
    def _ordered(self) -> "BBox":
        """West<=East and South<=North."""
        if self.max_lon < self.min_lon:
            raise ValueError("max_lon must be >= min_lon")
        if self.max_lat < self.min_lat:
            raise ValueError("max_lat must be >= min_lat")
        return self


class TimeRange(BaseModel):
    """An inclusive UTC time range [start, end]."""

    start: datetime = Field(..., description="UTC range start.")
    end: datetime = Field(..., description="UTC range end.")

    @model_validator(mode="after")
    def _ordered(self) -> "TimeRange":
        if self.end < self.start:
            raise ValueError("end must not be earlier than start")
        return self


# ---- Per-tool argument models -------------------------------------------------


class GetConditionsArgs(BaseModel):
    """Args for ``get_conditions``: wave/wind/SST per cell over a time range."""

    bbox: BBox
    time_range: TimeRange


class GetZonesArgs(BaseModel):
    """Args for ``get_zones``: active/inactive protection zones at a time."""

    bbox: BBox
    time: datetime = Field(..., description="UTC time to evaluate zone activity at.")


class GetWhaleRiskArgs(BaseModel):
    """Args for ``get_whale_risk``: risk grid for a speed at a time."""

    bbox: BBox
    time: datetime = Field(..., description="UTC time for the risk evaluation.")
    speed_kn: float = Field(..., gt=0.0, description="Planned vessel speed, knots.")


class PlanRoutesArgs(BaseModel):
    """Args for ``plan_routes``: a trip request (validated loosely as a dict).

    The authoritative schema is ``backend.app.models.trip.TripRequest``; we avoid
    importing it so this package stays standalone. We require the fields the
    router needs and leave full validation to the engine.
    """

    trip_request: dict = Field(..., description="A TripRequest-shaped object.")

    @field_validator("trip_request")
    @classmethod
    def _has_core_fields(cls, v: dict) -> dict:
        required = {"port", "vessel", "cruise_kn", "max_hours", "risk_pref"}
        missing = required - set(v)
        if missing:
            raise ValueError(f"trip_request missing required fields: {sorted(missing)}")
        return v


class GetEffortProxyArgs(BaseModel):
    """Args for ``get_effort_proxy``: normalized historical effort grid."""

    bbox: BBox
    month: int = Field(..., ge=1, le=12, description="Month of year, 1-12.")


class EstimateFuelArgs(BaseModel):
    """Args for ``estimate_fuel``: liters for a route and vessel class."""

    route: dict = Field(..., description="A RoutePlan-shaped object (needs waypoints).")
    vessel: Literal["small_boat", "mid_trawler", "scalloper"] = Field(
        ..., description="Vessel class."
    )

    @field_validator("route")
    @classmethod
    def _has_waypoints(cls, v: dict) -> dict:
        wps = v.get("waypoints")
        if not isinstance(wps, list) or len(wps) < 2:
            raise ValueError("route.waypoints must be a list of at least 2 (lon, lat) points")
        return v


class SimulateZoneArgs(BaseModel):
    """Args for ``simulate_zone``: Δrisk/Δtime/Δeffort for a candidate polygon."""

    candidate_polygon: dict = Field(
        ..., description="A GeoJSON Polygon for the candidate protection zone."
    )
    fleet_sample_id: str = Field(..., description="Id of the fleet sample to re-route.")

    @field_validator("candidate_polygon")
    @classmethod
    def _is_polygon(cls, v: dict) -> dict:
        if v.get("type") != "Polygon":
            raise ValueError('candidate_polygon must be a GeoJSON object with type "Polygon"')
        if not isinstance(v.get("coordinates"), list) or not v["coordinates"]:
            raise ValueError("candidate_polygon must have non-empty coordinates")
        return v


class ExportBriefArgs(BaseModel):
    """Args for ``export_brief``: render a one-page brief in a language."""

    route: dict = Field(..., description="A RoutePlan-shaped object to render.")
    language: Literal["en", "pt", "es"] = Field(..., description="Brief language.")

    @field_validator("route")
    @classmethod
    def _has_waypoints(cls, v: dict) -> dict:
        wps = v.get("waypoints")
        if not isinstance(wps, list) or len(wps) < 2:
            raise ValueError("route.waypoints must be a list of at least 2 (lon, lat) points")
        return v
