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
    cond_meta = snapshot_meta("conditions.json")
    zones = zones_provenance()
    zones_meta = snapshot_meta("zones.json")
    sight = snapshot_meta("sightings.json")
    land = snapshot_meta("land_mask.geojson")

    # Every layer carries: name, source_url, fetched_at, cached, synthetic,
    # license, and a short honest note (task: data-honesty on /api/meta/sources).
    sources = [
        {"layer": "conditions", "name": cond["source"], "source_url": cond["source_url"],
         "fetched_at": cond["fetched_at"], "cached": cond["cached"], "synthetic": cond["synthetic"],
         "license": cond_meta.get("license", "U.S. Government work / public domain (NOAA, NWS)"),
         "note": cond_meta.get("note", "NOAA NDBC buoy observations + NWS marine forecast samples.")},
        {"layer": "zones", "name": zones["source"], "source_url": zones["source_url"],
         "fetched_at": zones["fetched_at"], "cached": True, "synthetic": zones["synthetic"],
         "license": zones_meta.get("license", "Underlying facts U.S. Government work / public domain; polygons are ours."),
         "note": zones_meta.get("note", "Hand-drawn approximations of official NOAA/BOEM areas; dates verified.")},
        {"layer": "sightings", "name": sight.get("source", "sightings.json"), "source_url": sight.get("source_url"),
         "fetched_at": sight.get("fetched_at"), "cached": True, "synthetic": bool(sight.get("synthetic", True)),
         "license": sight.get("license", "CC-BY 4.0 (OBIS)"),
         "note": sight.get("note", "Real OBIS right whale occurrences clipped to the study bbox.")},
        {"layer": "risk",
         "name": "app.engine.risk screening model (real OBIS sightings + Vanderlaan & Taggart 2007 lethality curve)",
         "source_url": "https://doi.org/10.1111/j.1748-7692.2007.00048.x",
         "fetched_at": sight.get("fetched_at"), "cached": True, "synthetic": True,
         "license": "Lethality curve (c) authors; Fathom model code MIT.",
         "note": ("Transparent screening model, not a measured strike probability. "
                  "Params verified: v50=11.8 kn, k=2.415 (Vanderlaan & Taggart 2007).")},
        {"layer": "land_mask",
         "name": land.get("source", "hand-drawn approximation of the NOAA / Natural Earth coastline"),
         "source_url": land.get("source_url"),
         "fetched_at": land.get("fetched_at"), "cached": True, "synthetic": bool(land.get("synthetic", True)),
         "license": land.get("license", "Natural Earth public domain; simplified polygons are ours."),
         "note": land.get("note", "Simplified coastline for the land mask; not for navigation.")},
    ]
    stamps = [s["fetched_at"] for s in sources if s["fetched_at"]]
    return {"demo_mode": demo_mode(), "data_timestamp": max(stamps) if stamps else None, "sources": sources}
