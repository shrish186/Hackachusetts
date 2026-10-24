"""Real eMOLT bottom-temperature ingest (Lane A).

eMOLT = Environmental Monitors on Lobster Traps (and Large Trawlers): ~100+
Northeast-US fishing vessels carry low-cost sensors that log hourly BOTTOM water
temperature (~0.2 degC accuracy) on their fishing grounds. This is a distinct,
fishermen-sourced layer -- bottom temperature, not sea-surface temperature --
served via the NOAA/NMFS/NEFSC ERDDAP. No API key required.

Dataset: eMOLT_realtime_bottom_temps_and_profiles
ERDDAP:  https://comet.nefsc.noaa.gov/erddap/
Program: https://www.emolt.org/ ; InPort: https://www.fisheries.noaa.gov/inport/item/25149
Units in the feed: time UTC, latitude/longitude degrees, depth m, temperature degC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ERDDAP_BASE = (
    "https://comet.nefsc.noaa.gov/erddap/tabledap/"
    "eMOLT_realtime_bottom_temps_and_profiles.json"
)
DATASET_PAGE = (
    "https://comet.nefsc.noaa.gov/erddap/info/"
    "eMOLT_realtime_bottom_temps_and_profiles/index.html"
)
PROGRAM_URL = "https://www.emolt.org/"

# Study-area bbox (min_lon, min_lat, max_lon, max_lat); mirrors study_area.yaml.
STUDY_BBOX = (-71.0, 41.0, -69.0, 43.5)


@dataclass
class EmoltReading:
    """One normalized eMOLT bottom-temperature observation."""

    lon: float
    lat: float
    observed_at: datetime
    depth_m: float | None
    bottom_temp_c: float
    source: str


def _parse_dt(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt.astimezone(timezone.utc)


def parse_erddap_table(table: dict) -> list[EmoltReading]:
    """Normalize an ERDDAP tabledap ``table`` dict into EmoltReading rows.

    Expects columns time, latitude, longitude, depth, temperature (the order we
    request). Drops rows with a missing coordinate/temperature.
    """
    cols = table.get("columnNames", [])
    idx = {name: i for i, name in enumerate(cols)}
    needed = ("time", "latitude", "longitude", "temperature")
    if not all(k in idx for k in needed):
        return []
    out: list[EmoltReading] = []
    for row in table.get("rows", []):
        when = _parse_dt(row[idx["time"]])
        lat = row[idx["latitude"]]
        lon = row[idx["longitude"]]
        temp = row[idx["temperature"]]
        if when is None or lat is None or lon is None or temp is None:
            continue
        depth = row[idx["depth"]] if "depth" in idx else None
        out.append(
            EmoltReading(
                lon=float(lon),
                lat=float(lat),
                observed_at=when,
                depth_m=float(depth) if depth is not None else None,
                bottom_temp_c=float(temp),
                source="eMOLT (NOAA/NMFS/NEFSC ERDDAP)",
            )
        )
    return out


def most_recent_per_station(
    rows: list[EmoltReading], round_deg: int = 2
) -> list[EmoltReading]:
    """Keep the single most-recent reading per ~station (lat/lon rounded)."""
    best: dict[tuple[float, float], EmoltReading] = {}
    for r in sorted(rows, key=lambda x: x.observed_at):
        key = (round(r.lat, round_deg), round(r.lon, round_deg))
        best[key] = r  # later (newer) overwrites
    return sorted(best.values(), key=lambda x: x.observed_at, reverse=True)


def fetch_bottom_temps(
    bbox: tuple[float, float, float, float] = STUDY_BBOX,
    days: int = 7,
    per_time_limit: int = 120,
    timeout_s: float = 30.0,
) -> list[EmoltReading]:
    """Download recent eMOLT bottom temps for ``bbox``. Raises on network error.

    Queries the last ``days`` days inside the bbox, then reduces to the most
    recent reading per station so the snapshot stays small and representative.
    """
    import httpx

    min_lon, min_lat, max_lon, max_lat = bbox
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    query = (
        "time,latitude,longitude,depth,temperature"
        f"&longitude>={min_lon}&longitude<={max_lon}"
        f"&latitude>={min_lat}&latitude<={max_lat}"
        f"&time>={since}"
        f'&orderByLimit("time,{per_time_limit}")'
    )
    resp = httpx.get(f"{ERDDAP_BASE}?{query}", timeout=timeout_s, follow_redirects=True)
    resp.raise_for_status()
    rows = parse_erddap_table(resp.json().get("table", {}))
    return most_recent_per_station(rows)
