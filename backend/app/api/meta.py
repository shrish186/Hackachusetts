"""GET /api/meta/sources: source list, timestamps, and demo-mode flag (design.md §9)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.layers import conditions_records, snapshot_meta, zones_provenance
from app.ingest.conditions import demo_mode

router = APIRouter(tags=["meta"])


@router.get("/meta/sources")
def get_sources() -> dict[str, Any]:
    """Return ``MetaResponse`` (frontend/src/api/types.ts)."""
    _, cond = conditions_records(None)
    zones = zones_provenance()
    sight = snapshot_meta("sightings.json")
    land = snapshot_meta("land_mask.geojson")
    sources = [
        {"layer": "conditions", "name": cond["source"], "source_url": cond["source_url"],
         "fetched_at": cond["fetched_at"], "cached": cond["cached"], "synthetic": cond["synthetic"]},
        {"layer": "zones", "name": zones["source"], "source_url": zones["source_url"],
         "fetched_at": zones["fetched_at"], "cached": True, "synthetic": zones["synthetic"]},
        {"layer": "sightings", "name": sight.get("source", "sightings.json"), "source_url": sight.get("source_url"),
         "fetched_at": sight.get("fetched_at"), "cached": True, "synthetic": bool(sight.get("synthetic", True))},
        {"layer": "risk", "name": "Vanderlaan & Taggart (2007) vessel-strike lethality curve",
         "source_url": "https://doi.org/10.1111/j.1748-7692.2007.00048.x",
         "fetched_at": sight.get("fetched_at"), "cached": True, "synthetic": True},
        {"layer": "land_mask", "name": "land_mask.geojson", "source_url": land.get("source_url"),
         "fetched_at": land.get("fetched_at"), "cached": True, "synthetic": bool(land.get("synthetic", True))},
    ]
    stamps = [s["fetched_at"] for s in sources if s["fetched_at"]]
    return {"demo_mode": demo_mode(), "data_timestamp": max(stamps) if stamps else None, "sources": sources}
