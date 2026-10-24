"""Real NWS (api.weather.gov) marine forecast ingest (Lane A).

Samples the National Weather Service gridpoint forecast at several points across
the study area to get real wave height and wind speed with study-wide coverage
(the NDBC buoys alone cover only 2-4 cells). No API key required; the NWS API
asks for a descriptive User-Agent.

API: https://api.weather.gov/   (U.S. Government work / public domain)
Units in the feed: waveHeight m, windSpeed km/h. We convert wind to knots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
NWS_HOME = "https://www.weather.gov/"
USER_AGENT = "fathom-ocean-copilot (hackachusetts demo)"

_KMH_TO_KN = 0.5399568

# Sample points across the study area (lon, lat). Chosen to sit over water in
# Massachusetts Bay, Cape Cod Bay, and the eastern approaches.
SAMPLE_POINTS: tuple[tuple[float, float], ...] = (
    (-70.40, 42.35),   # central Massachusetts Bay
    (-70.25, 42.60),   # north, toward Cape Ann approaches
    (-70.10, 42.10),   # off the outer Cape
    (-70.35, 41.90),   # Cape Cod Bay
    (-69.60, 42.40),   # eastern approaches / offshore
)


@dataclass
class NwsReading:
    """One normalized NWS gridpoint reading."""

    lon: float
    lat: float
    time: datetime
    wave_m: float | None
    wind_kn: float | None
    source_url: str


def _first_value(block: dict) -> tuple[float | None, str | None]:
    """Return (value, validTime-start) of the first entry of an NWS property block."""
    values = (block or {}).get("values") or []
    if not values:
        return None, None
    v = values[0]
    vt = (v.get("validTime") or "").split("/")[0] or None
    return v.get("value"), vt


def _parse_vt(vt: str | None) -> datetime:
    if not vt:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(vt.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_point(lon: float, lat: float, timeout_s: float = 15.0) -> NwsReading | None:
    """Fetch the current wave/wind forecast at (lon, lat). Raises on network error."""
    import httpx

    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    pts = httpx.get(
        NWS_POINTS_URL.format(lat=round(lat, 4), lon=round(lon, 4)),
        timeout=timeout_s,
        headers=headers,
        follow_redirects=True,
    )
    pts.raise_for_status()
    grid_url = pts.json()["properties"].get("forecastGridData")
    if not grid_url:
        return None
    g = httpx.get(grid_url, timeout=timeout_s, headers=headers, follow_redirects=True)
    g.raise_for_status()
    gp = g.json()["properties"]
    wave_m, vt = _first_value(gp.get("waveHeight"))
    wind_kmh, _ = _first_value(gp.get("windSpeed"))
    wind_kn = round(wind_kmh * _KMH_TO_KN, 1) if wind_kmh is not None else None
    return NwsReading(
        lon=lon,
        lat=lat,
        time=_parse_vt(vt),
        wave_m=round(wave_m, 2) if wave_m is not None else None,
        wind_kn=wind_kn,
        source_url=grid_url,
    )


def fetch_all(timeout_s: float = 15.0) -> list[NwsReading]:
    """Fetch forecasts at every sample point (skipping any that fail)."""
    out: list[NwsReading] = []
    for lon, lat in SAMPLE_POINTS:
        try:
            r = fetch_point(lon, lat, timeout_s)
        except Exception:  # noqa: BLE001 - skip a failing point, keep the rest
            continue
        if r is not None and r.wave_m is not None and r.wind_kn is not None:
            out.append(r)
    return out
