"""Core Fathom data models (pydantic v2).

These are the shared domain types used across the data, engine, and agent
layers. Keeping them in one place guarantees the API, the risk/routing engine,
and the MCP tools all speak the same language. See design.md section 4.

All times are UTC internally (display is converted to America/New_York in the
UI). Units are stated in each field's description: knots (kn), meters (m),
hours (h), liters (l), degrees Celsius (c).
"""

from app.models.geo import Cell, Zone, Sighting, ZoneKind
from app.models.conditions import Conditions
from app.models.trip import TripRequest, Vessel, Language
from app.models.plan import Citation, RoutePlan

__all__ = [
    "Cell",
    "Zone",
    "ZoneKind",
    "Sighting",
    "Conditions",
    "TripRequest",
    "Vessel",
    "Language",
    "RoutePlan",
    "Citation",
]
