"""Real OBIS North Atlantic right whale sighting ingest (Lane A).

Pulls Eubalaena glacialis (North Atlantic right whale) occurrence records for
the Fathom study bbox from OBIS (Ocean Biodiversity Information System), which
aggregates public NOAA/NMFS/NEFSC survey data. No API key required.

OBIS API: https://api.obis.org/  (CC-BY; cite OBIS and the underlying datasets)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

# North Atlantic right whale.
SCIENTIFIC_NAME = "Eubalaena glacialis"
OBIS_OCCURRENCE_URL = "https://api.obis.org/v3/occurrence"
OBIS_HOME = "https://obis.org/"

# Study-area bbox (min_lon, min_lat, max_lon, max_lat); mirrors study_area.yaml.
STUDY_BBOX = (-71.0, 41.0, -69.0, 43.5)


@dataclass
class ObisSighting:
    """One normalized OBIS occurrence."""

    lon: float
    lat: float
    observed_at: datetime
    count: int
    source: str


def _bbox_polygon(bbox: tuple[float, float, float, float]) -> str:
    """OBIS geometry WKT polygon from a bbox."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.split("/")[0].strip()  # some records give a range "start/end"
    v = v.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        # Try date-only.
        try:
            dt = datetime.strptime(v[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _count(value) -> int:
    try:
        n = int(float(value))
        return max(n, 1)
    except (TypeError, ValueError):
        return 1


def parse_records(results: list[dict]) -> list[ObisSighting]:
    """Normalize raw OBIS results into ObisSighting rows (dropping unusable ones)."""
    out: list[ObisSighting] = []
    for rec in results:
        lon = rec.get("decimalLongitude")
        lat = rec.get("decimalLatitude")
        when = _parse_date(rec.get("eventDate"))
        if lon is None or lat is None or when is None:
            continue
        inst = rec.get("institutionCode") or rec.get("datasetName") or "OBIS"
        out.append(
            ObisSighting(
                lon=float(lon),
                lat=float(lat),
                observed_at=when,
                count=_count(rec.get("individualCount")),
                source=f"OBIS ({inst})",
            )
        )
    return out


def fetch_sightings(
    bbox: tuple[float, float, float, float] = STUDY_BBOX,
    size: int = 500,
    timeout_s: float = 20.0,
) -> list[ObisSighting]:
    """Download right-whale occurrences for ``bbox``. Raises on network error.

    Returns the most recent ``size`` records (OBIS returns newest-biased pages;
    we additionally sort by date descending here).
    """
    import httpx

    params = {
        "scientificname": SCIENTIFIC_NAME,
        "geometry": _bbox_polygon(bbox),
        "size": size,
    }
    resp = httpx.get(OBIS_OCCURRENCE_URL, params=params, timeout=timeout_s)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    rows = parse_records(results)
    rows.sort(key=lambda r: r.observed_at, reverse=True)
    return rows
