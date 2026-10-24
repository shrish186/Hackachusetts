"""Fishing-effort proxy grid (Lane A, task 5).

Effort proxy is a 0..1 stand-in for historical fishing activity (NOT catch or
revenue -- always labeled an estimate, per product steering). If real AIS were
downloaded we would derive it from slow-speed + turning vessel behavior; no AIS
was available, so this is SYNTHETIC: a smooth field peaked on the known fishing
grounds in config/ports.yaml.

Public API:
    effort_at(lon, lat) -> float in [0, 1]
    effort_access(waypoints) -> float in [0, 1]   (mean effort along a route)
"""

from __future__ import annotations

import math
from functools import lru_cache

from app.ingest.config import config_path, load_yaml

# This layer is synthetic until real AIS/effort data is ingested.
SYNTHETIC = True

# Gaussian bandwidth (km) of the effort bump around each fishing ground.
_GROUND_BANDWIDTH_KM = 25.0
_EARTH_RADIUS_KM = 6371.0088


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def _grounds() -> list[tuple[float, float, float]]:
    """Return (lon, lat, weight) for each fishing ground from config/ports.yaml."""
    cfg = load_yaml(config_path("ports.yaml"))
    grounds = cfg.get("fishing_grounds", {})
    # Equal weight per ground; weight is the peak effort contribution (<= 1).
    return [(g["lon"], g["lat"], 1.0) for g in grounds.values()]


def effort_at(lon: float, lat: float) -> float:
    """Synthetic fishing-effort proxy at a point, in [0, 1].

    Sum of Gaussian bumps centered on known fishing grounds, saturated to [0, 1].
    Independent of other points; deterministic. This is an ESTIMATE, not catch
    or revenue.
    """
    total = 0.0
    bw = _GROUND_BANDWIDTH_KM
    for glon, glat, w in _grounds():
        d = _haversine_km(lon, lat, glon, glat)
        total += w * math.exp(-(d * d) / (2.0 * bw * bw))
    # Saturating map keeps the result in [0, 1) even where bumps overlap.
    return 1.0 - math.exp(-total)


def effort_access(waypoints: list[tuple[float, float]]) -> float:
    """Mean effort proxy along a route's waypoints, in [0, 1].

    ``waypoints`` are (lon, lat) pairs. Empty routes return 0.0. This is a
    coarse 'how much good fishing ground does this route reach' estimate.
    """
    if not waypoints:
        return 0.0
    vals = [effort_at(lon, lat) for lon, lat in waypoints]
    return sum(vals) / len(vals)
