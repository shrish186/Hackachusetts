"""Real NOAA NDBC buoy ingest for the Fathom conditions layer (Lane A).

Downloads the realtime standard meteorological feed for Massachusetts Bay /
Cape Cod Bay buoys and normalizes the latest valid observation into the
``Conditions`` shape. No API key required.

Feed format (space-delimited, two comment header rows):
  #YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
Units: WSPD/GST m/s, WVHT m, WTMP/ATMP degC. Missing values are "MM".

Reference: https://www.ndbc.noaa.gov/measdes.shtml
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

# Verified station locations (NDBC station pages, Oct 2026).
STATIONS: dict[str, tuple[float, float, str]] = {
    # id: (lon, lat, human name) -- coordinates from each NDBC station page.
    "44013": (-70.651, 42.346, "Boston (Massachusetts Bay)"),
    "44029": (-70.566, 42.523, "Massachusetts Bay (NERACOOS)"),
    "44098": (-70.169, 42.800, "Jeffreys Ledge (NERACOOS)"),
    "44090": (-70.329, 41.840, "Cape Cod Bay"),
}

NDBC_REALTIME = "https://www.ndbc.noaa.gov/data/realtime2/{sid}.txt"

_MS_TO_KN = 1.9438445  # 1 m/s in knots


@dataclass
class BuoyObservation:
    """One normalized buoy observation (SI-ish units converted for Fathom)."""

    station_id: str
    lon: float
    lat: float
    time: datetime
    wave_m: float | None
    wind_kn: float | None
    sst_c: float | None
    source_url: str


def _f(token: str) -> float | None:
    """Parse an NDBC token; 'MM' (missing) -> None."""
    if token == "MM":
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _rows(text: str, station_id: str):
    """Yield parsed BuoyObservation rows (newest first), including None fields."""
    lon, lat, _ = STATIONS[station_id]
    url = NDBC_REALTIME.format(sid=station_id)
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        p = line.split()
        if len(p) < 15:
            continue
        yr, mo, dy, hr, mn = (int(x) for x in p[:5])
        wspd, wvht, wtmp = _f(p[6]), _f(p[8]), _f(p[14])
        yield BuoyObservation(
            station_id=station_id,
            lon=lon,
            lat=lat,
            time=datetime(yr, mo, dy, hr, mn, tzinfo=timezone.utc),
            wave_m=wvht,
            wind_kn=round(wspd * _MS_TO_KN, 1) if wspd is not None else None,
            sst_c=wtmp,
            source_url=url,
        )


def parse_latest(text: str, station_id: str) -> BuoyObservation | None:
    """Return the most recent row that has BOTH a real wave and wind reading.

    Requiring both avoids presenting a defaulted/zero value as a real
    observation (honesty rule). Falls back to the newest row with at least one
    of the two if no fully-complete row exists in the feed window.
    """
    newest_partial: BuoyObservation | None = None
    for obs in _rows(text, station_id):
        if obs.wave_m is not None and obs.wind_kn is not None:
            return obs
        if newest_partial is None and (obs.wave_m is not None or obs.wind_kn is not None):
            newest_partial = obs
    return newest_partial


def fetch_station(station_id: str, timeout_s: float = 15.0) -> BuoyObservation | None:
    """Download and parse the latest observation for one station.

    Raises on network error so the caller can decide to fall back to cache.
    """
    import httpx

    url = NDBC_REALTIME.format(sid=station_id)
    resp = httpx.get(url, timeout=timeout_s, follow_redirects=True)
    resp.raise_for_status()
    return parse_latest(resp.text, station_id)


def fetch_all(timeout_s: float = 15.0) -> list[BuoyObservation]:
    """Fetch the latest observation for every configured MA Bay station."""
    out: list[BuoyObservation] = []
    for sid in STATIONS:
        obs = fetch_station(sid, timeout_s)
        if obs is not None:
            out.append(obs)
    return out
