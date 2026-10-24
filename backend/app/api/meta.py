"""Meta endpoints: data source listing and demo-mode flag.

See design.md section 9: ``GET /api/meta/sources`` returns the source list,
their timestamps, and the demo-mode flag. Every dataset must carry a
``source_url``, ``fetched_at``, and a cached/synthetic flag (steering: tech.md).
"""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


def _demo_mode() -> bool:
    """Return True when the app should run from bundled snapshots only."""
    return os.getenv("FATHOM_DEMO_MODE", "false").lower() in {"1", "true", "yes"}


@router.get("/meta/sources")
def get_sources() -> dict[str, object]:
    """List data sources with provenance and the current demo-mode flag.

    Timestamps are UTC ISO-8601. ``fetched_at`` is populated by the ingest
    jobs (Lane A); until then these entries describe candidate sources from
    design.md section 3 and are flagged ``synthetic`` where no snapshot exists.
    """
    sources = [
        {
            "layer": "conditions",
            "name": "NOAA NDBC buoys / NWS marine forecast",
            "source_url": "https://www.ndbc.noaa.gov/",
            "fetched_at": None,
            "cached": False,
            "synthetic": True,
        },
        {
            "layer": "zones",
            "name": "NOAA Fisheries right whale zones / slow zones / closures",
            "source_url": "https://www.fisheries.noaa.gov/",
            "fetched_at": None,
            "cached": False,
            "synthetic": True,
        },
        {
            "layer": "wind_lease",
            "name": "BOEM offshore wind lease areas",
            "source_url": "https://www.boem.gov/",
            "fetched_at": None,
            "cached": False,
            "synthetic": True,
        },
        {
            "layer": "sightings",
            "name": "OBIS / public whale sightings sample",
            "source_url": "https://obis.org/",
            "fetched_at": None,
            "cached": False,
            "synthetic": True,
        },
    ]
    return {"demo_mode": _demo_mode(), "sources": sources}
