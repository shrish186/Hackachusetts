#!/usr/bin/env python3
"""Refresh Fathom data snapshots from live public sources (Lane A).

Rewrites the bundled snapshots under ``data/snapshots/`` with freshly fetched
data and an honest ``metadata`` block (source, source_url, fetched_at, license,
synthetic flag, note). Each source degrades gracefully: if it is unreachable,
the existing snapshot is kept and a warning is printed, so running this never
produces half-written or dishonest data.

Usage (from repo root):
    python scripts/refresh_snapshots.py [--conditions] [--sightings] [--all]

With no flags, refreshes everything it can.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `import app...` work when run from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def refresh_conditions() -> bool:
    """Rewrite conditions.json from live NOAA NDBC buoys + NWS marine forecast.

    NDBC gives real point observations at the buoys; NWS gridpoint forecast adds
    real wave/wind coverage across the study area (the buoys alone cover only a
    few cells). Both are real; the snapshot is synthetic:false. Returns True if
    anything real was written.
    """
    from app.ingest.grid import build_grid_spec, land_mask_array
    from app.ingest.ndbc import STATIONS
    from app.ingest import ndbc, nws

    try:
        spec = build_grid_spec()
        land_mask_array(spec)
    except Exception as exc:  # noqa: BLE001
        print(f"[conditions] grid build FAILED, keeping existing snapshot: {exc}")
        return False

    now = _now_iso()
    records: list[dict] = []
    seen_cells: set[str] = set()

    # 1) NDBC buoy observations (preferred where available).
    try:
        obs = ndbc.fetch_all(timeout_s=15.0)
    except Exception as exc:  # noqa: BLE001
        print(f"[conditions] NDBC fetch failed ({exc}); continuing with NWS")
        obs = []
    for o in obs:
        if o.wave_m is None or o.wind_kn is None:
            continue
        ix, iy = spec.index_of(o.lon, o.lat)
        cid = spec.cell_id(ix, iy)
        if cid in seen_cells:
            continue
        seen_cells.add(cid)
        records.append(
            {
                "cell_id": cid,
                "time": o.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "wave_m": o.wave_m,
                "wind_kn": o.wind_kn,
                "sst_c": o.sst_c,
                "source": f"noaa_ndbc_{o.station_id}",
                "fetched_at": now,
            }
        )

    # 2) NWS gridpoint forecast at sample points for study-wide coverage.
    try:
        nws_rows = nws.fetch_all(timeout_s=15.0)
    except Exception as exc:  # noqa: BLE001
        print(f"[conditions] NWS fetch failed ({exc}); continuing with NDBC only")
        nws_rows = []
    for r in nws_rows:
        ix, iy = spec.index_of(r.lon, r.lat)
        cid = spec.cell_id(ix, iy)
        if cid in seen_cells:
            continue
        seen_cells.add(cid)
        records.append(
            {
                "cell_id": cid,
                "time": r.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "wave_m": r.wave_m,
                "wind_kn": r.wind_kn,
                "sst_c": None,
                "source": "nws_marine_forecast",
                "fetched_at": now,
            }
        )

    if not records:
        print("[conditions] no real rows fetched (NDBC + NWS both empty); keeping existing snapshot")
        return False

    n_ndbc = sum(1 for r in records if r["source"].startswith("noaa_ndbc"))
    n_nws = sum(1 for r in records if r["source"] == "nws_marine_forecast")
    payload = {
        "metadata": {
            "description": (
                "Real ocean conditions for the Fathom study area: NOAA NDBC buoy "
                "observations plus NWS marine gridpoint forecast samples for study-wide "
                "wave and wind coverage."
            ),
            "source": "NOAA NDBC realtime2 buoy feed + NWS (api.weather.gov) marine gridpoint forecast",
            "source_url": "https://www.ndbc.noaa.gov/station_page.php?station=44013",
            "license": "U.S. Government work / public domain (NOAA, NWS)",
            "note": (
                f"{n_ndbc} real buoy cell(s) + {n_nws} real NWS forecast sample cell(s). "
                "Buoy rows are observations; NWS rows are the current forecast. "
                "Wind converted to knots."
            ),
            "stations": {sid: {"lon": v[0], "lat": v[1], "name": v[2]} for sid, v in STATIONS.items()},
            "fetched_at": now,
            "synthetic": False,
        },
        "conditions": records,
    }
    _write(SNAPSHOT_DIR / "conditions.json", payload)
    print(f"[conditions] wrote {len(records)} real rows ({n_ndbc} NDBC + {n_nws} NWS) at {now}")
    return True


def refresh_sightings() -> bool:
    """Rewrite sightings.json from live OBIS right-whale occurrences.

    Keeps the most-recent real records observed in the whale-season window
    (Jan-May), so the 15 Mar demo replay shows the genuine seasonal presence
    pattern rather than off-season records. Falls back to the last Jan-May
    behaviour only via the live source; never fabricates data.
    """
    from app.ingest.obis import (
        fetch_sightings,
        OBIS_HOME,
        SCIENTIFIC_NAME,
        STUDY_BBOX,
        WHALE_SEASON_MONTHS,
    )

    try:
        rows = fetch_sightings(
            bbox=STUDY_BBOX, size=800, timeout_s=20.0, months=WHALE_SEASON_MONTHS
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[sightings] OBIS fetch FAILED, keeping existing snapshot: {exc}")
        return False
    if not rows:
        print("[sightings] OBIS returned no whale-season rows; keeping existing snapshot")
        return False

    now = _now_iso()
    # Keep the ~60 most recent whale-season records: representative of the
    # seasonal pattern, few enough that the per-cell risk model stays fast for
    # routing (Req 5.3 regenerates routes in < 3 s). OBIS has thousands in-bbox.
    rows = rows[:60]
    sightings = [
        {
            "lon": round(r.lon, 5),
            "lat": round(r.lat, 5),
            "observed_at": r.observed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": r.count,
            "source": r.source,
        }
        for r in rows
    ]
    span = (
        f"{min(s['observed_at'] for s in sightings)[:10]} to "
        f"{max(s['observed_at'] for s in sightings)[:10]}"
    )
    payload = {
        "metadata": {
            "description": (
                f"Real {SCIENTIFIC_NAME} (North Atlantic right whale) occurrence records "
                "for the Fathom study bbox from OBIS, restricted to the Jan-May whale "
                "season and limited to the most recent records."
            ),
            "source": "OBIS (Ocean Biodiversity Information System), aggregating NOAA/NMFS/NEFSC surveys",
            "source_url": OBIS_HOME,
            "license": "CC-BY 4.0 (OBIS); cite OBIS and the underlying datasets",
            "note": (
                "Real observations clipped to the study bbox and to the Jan-May whale "
                "season (months 1-5), newest first. These are historical seasonal "
                "sightings, not live/recent detections; on a March replay they drive "
                "the risk layer's seasonal presence term (recency of multi-year-old "
                f"records is ~0). Date span: {span}."
            ),
            "scientific_name": SCIENTIFIC_NAME,
            "season_months": list(WHALE_SEASON_MONTHS),
            "record_count": len(sightings),
            "fetched_at": now,
            "synthetic": False,
        },
        "sightings": sightings,
    }
    _write(SNAPSHOT_DIR / "sightings.json", payload)
    print(f"[sightings] wrote {len(sightings)} real OBIS whale-season records ({span}) at {now}")
    return True


def refresh_emolt() -> bool:
    """Rewrite emolt_bottom_temp.json from live eMOLT bottom-temperature data.

    eMOLT = Environmental Monitors on Lobster Traps: fishermen-collected hourly
    bottom temperatures via the NOAA/NMFS/NEFSC ERDDAP. Real; synthetic:false.
    Keeps the most recent reading per station in the study bbox. Falls back to
    the existing snapshot (never fabricates) on any failure.
    """
    from app.ingest.emolt import DATASET_PAGE, PROGRAM_URL, STUDY_BBOX, fetch_bottom_temps

    try:
        rows = fetch_bottom_temps(bbox=STUDY_BBOX, days=7, timeout_s=30.0)
    except Exception as exc:  # noqa: BLE001
        print(f"[emolt] fetch FAILED, keeping existing snapshot: {exc}")
        return False
    if not rows:
        print("[emolt] no rows in bbox/window; keeping existing snapshot")
        return False

    now = _now_iso()
    readings = [
        {
            "lon": round(r.lon, 5),
            "lat": round(r.lat, 5),
            "observed_at": r.observed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "depth_m": round(r.depth_m, 2) if r.depth_m is not None else None,
            "bottom_temp_c": round(r.bottom_temp_c, 3),
            "source": r.source,
        }
        for r in rows
    ]
    span = (
        f"{min(s['observed_at'] for s in readings)[:10]} to "
        f"{max(s['observed_at'] for s in readings)[:10]}"
    )
    payload = {
        "metadata": {
            "description": (
                "Real eMOLT (Environmental Monitors on Lobster Traps) BOTTOM-water "
                "temperature observations in the Fathom study bbox, most recent reading "
                "per station. Fishermen-collected via NOAA/NMFS/NEFSC."
            ),
            "source": "eMOLT via NOAA/NMFS/NEFSC ERDDAP (eMOLT_realtime_bottom_temps_and_profiles)",
            "source_url": DATASET_PAGE,
            "program_url": PROGRAM_URL,
            "license": "U.S. Government work / public domain (NOAA); cite eMOLT and NEFSC",
            "note": (
                "Real bottom-temperature observations (not sea-surface temperature). "
                f"One most-recent reading per station in the last 7 days. Span: {span}."
            ),
            "variable": "bottom_temp_c (degree_C)",
            "record_count": len(readings),
            "fetched_at": now,
            "synthetic": False,
        },
        "readings": readings,
    }
    _write(SNAPSHOT_DIR / "emolt_bottom_temp.json", payload)
    print(f"[emolt] wrote {len(readings)} real eMOLT bottom-temp readings ({span}) at {now}")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh Fathom data snapshots from live sources.")
    ap.add_argument("--conditions", action="store_true", help="Refresh conditions.json (NDBC+NWS).")
    ap.add_argument("--sightings", action="store_true", help="Refresh sightings.json (OBIS).")
    ap.add_argument("--emolt", action="store_true", help="Refresh emolt_bottom_temp.json (eMOLT).")
    ap.add_argument("--all", action="store_true", help="Refresh everything (default).")
    args = ap.parse_args(argv)

    do_all = args.all or not (args.conditions or args.sightings or args.emolt)
    ok = True
    if do_all or args.conditions:
        ok = refresh_conditions() and ok
    if do_all or args.sightings:
        ok = refresh_sightings() and ok
    if do_all or args.emolt:
        ok = refresh_emolt() and ok
    # Exit 0 even on graceful fallback; only crash on unexpected errors.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
