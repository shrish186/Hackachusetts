"""Whale encounter risk model (Lane A, Task 1.4, Req 3, design.md section 5).

Deterministic, testable Python. No LLM. All parameters come from
``config/risk.yaml`` so they are explainable and tweakable in the demo.

Model (design.md section 5), for cell ``c``, time ``t``, planned speed ``v`` kn:

    presence(c)      kernel-smoothed historical sighting density, mapped to 0..1
    recency(c, t)    1 - prod_s (1 - exp(-age_days(s)/tau) * exp(-dist(s,c)/rho))
    p_whale(c, t)    clip(alpha * presence + (1 - alpha) * recency, 0, 1)
    lethality(v)     1 / (1 + exp(-(v - v50) / k))
    risk(c, t, v)    p_whale(c, t) * lethality(v)    (0 in land cells)

Invariants (enforced by property tests, see testing-pbt steering):
  * risk is always within [0, 1]
  * risk is monotonic non-decreasing in speed
  * risk is 0 for land cells
  * adding a sighting never lowers risk in any cell

To keep the "adding a sighting never lowers risk" invariant, the presence term
is mapped to 0..1 with a fixed saturating transform ``1 - exp(-density/scale)``
rather than a data-dependent max-normalization (which would couple cells and
could *lower* another cell's value when a sighting is added).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Sequence

import numpy as np

from app.ingest.config import config_path, load_yaml
from app.models.geo import Sighting

# Mean earth radius (km) for the great-circle distance.
_EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class RiskParams:
    """Risk model parameters loaded from ``config/risk.yaml`` (units in comments)."""

    alpha: float            # weight on presence vs recency, [0, 1]
    presence_kernel_km: float
    tau_days: float
    rho_km: float
    radius_km: float
    v50_kn: float           # TODO-VERIFY against Vanderlaan & Taggart (2007)
    k: float                # TODO-VERIFY against Vanderlaan & Taggart (2007)
    risk_min: float
    risk_max: float
    # Fixed density scale for the saturating presence transform. Derived from
    # the kernel so a lone sighting produces a modest, stable presence value.
    presence_scale: float

    @classmethod
    def from_dict(cls, d: dict) -> "RiskParams":
        presence = d["presence"]
        recency = d["recency"]
        leth = d["lethality"]
        bounds = d["bounds"]
        kernel_km = float(presence["presence_kernel_km"])
        # Peak of a single 2-D Gaussian kernel contribution at distance 0 is 1;
        # use the kernel area scale so density is well-conditioned.
        presence_scale = float(presence.get("presence_scale", 1.0))
        return cls(
            alpha=float(presence["alpha"]),
            presence_kernel_km=kernel_km,
            tau_days=float(recency["tau_days"]),
            rho_km=float(recency["rho_km"]),
            radius_km=float(recency["radius_km"]),
            v50_kn=float(leth["v50_kn"]),
            k=float(leth["k"]),
            risk_min=float(bounds["risk_min"]),
            risk_max=float(bounds["risk_max"]),
            presence_scale=presence_scale,
        )


@lru_cache(maxsize=1)
def load_risk_params() -> RiskParams:
    """Load risk parameters from ``config/risk.yaml`` (cached)."""
    return RiskParams.from_dict(load_yaml(config_path("risk.yaml")))


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance between two lon/lat points, in kilometers."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def lethality(speed_kn: float, params: RiskParams | None = None) -> float:
    """Lethality of a strike at ``speed_kn`` knots, in [0, 1].

    Logistic curve ``1 / (1 + exp(-(v - v50) / k))``. Strictly increasing in
    speed, which gives the "monotonic in speed" invariant. Parameters are
    TODO-VERIFY (see config/risk.yaml).
    """
    p = params or load_risk_params()
    # Clamp the exponent to avoid overflow for extreme speeds.
    z = (speed_kn - p.v50_kn) / p.k
    z = max(min(z, 60.0), -60.0)
    return 1.0 / (1.0 + math.exp(-z))


def presence_at(
    lon: float,
    lat: float,
    sightings: Sequence[Sighting],
    params: RiskParams | None = None,
) -> float:
    """Seasonal presence prior at (lon, lat), mapped to [0, 1].

    Kernel-smoothed sighting density with a fixed saturating transform so the
    value is per-cell and monotonic non-decreasing in the sighting set.
    """
    p = params or load_risk_params()
    bw = p.presence_kernel_km
    density = 0.0
    for s in sightings:
        d = haversine_km(lon, lat, s.lon, s.lat)
        # Gaussian kernel weighted by observed count (count >= 0).
        density += max(s.count, 0) * math.exp(-(d * d) / (2.0 * bw * bw))
    # Saturating map to [0, 1); independent of other cells and other sightings.
    return 1.0 - math.exp(-density / p.presence_scale)


def recency_at(
    lon: float,
    lat: float,
    when: datetime,
    sightings: Sequence[Sighting],
    params: RiskParams | None = None,
) -> float:
    """Recent-sighting recency term at (lon, lat, when), in [0, 1].

    ``1 - prod_s (1 - exp(-age/tau) * exp(-dist/rho))`` over sightings within
    ``radius_km``. Each factor is in [0, 1], so the product shrinks (never
    grows) as sightings are added => the complement never decreases.
    """
    p = params or load_risk_params()
    when = _as_utc(when)
    prod = 1.0
    for s in sightings:
        d = haversine_km(lon, lat, s.lon, s.lat)
        if d > p.radius_km:
            continue
        age_days = max((when - _as_utc(s.observed_at)).total_seconds() / 86400.0, 0.0)
        contrib = math.exp(-age_days / p.tau_days) * math.exp(-d / p.rho_km)
        contrib = max(min(contrib, 1.0), 0.0)
        prod *= (1.0 - contrib)
    return 1.0 - prod


def p_whale(
    lon: float,
    lat: float,
    when: datetime,
    sightings: Sequence[Sighting],
    params: RiskParams | None = None,
) -> float:
    """Probability-like whale presence at (lon, lat, when), clipped to [0, 1]."""
    p = params or load_risk_params()
    pres = presence_at(lon, lat, sightings, p)
    rec = recency_at(lon, lat, when, sightings, p)
    val = p.alpha * pres + (1.0 - p.alpha) * rec
    return min(max(val, 0.0), 1.0)


def risk_at(
    lon: float,
    lat: float,
    when: datetime,
    speed_kn: float,
    sightings: Sequence[Sighting],
    *,
    is_land: bool = False,
    params: RiskParams | None = None,
) -> float:
    """Whale encounter risk at a point, in [0, 1]; 0 for land cells (Req 3).

    risk = p_whale * lethality(speed), clipped to [risk_min, risk_max].
    """
    p = params or load_risk_params()
    if is_land:
        return 0.0
    val = p_whale(lon, lat, when, sightings, p) * lethality(speed_kn, p)
    return min(max(val, p.risk_min), p.risk_max)


@dataclass
class RiskBreakdown:
    """Per-cell factor breakdown for the UI (Req 3.4)."""

    cell_id: str
    lon: float
    lat: float
    presence: float
    recency: float
    p_whale: float
    lethality: float
    risk: float

    def top_factors(self) -> list[tuple[str, float]]:
        """Factors ranked by contribution, for the 'why' panel."""
        factors = [
            ("seasonal_presence", self.presence),
            ("recent_sightings", self.recency),
            ("speed_lethality", self.lethality),
        ]
        return sorted(factors, key=lambda kv: kv[1], reverse=True)


def risk_breakdown(
    cell_id: str,
    lon: float,
    lat: float,
    when: datetime,
    speed_kn: float,
    sightings: Sequence[Sighting],
    *,
    is_land: bool = False,
    params: RiskParams | None = None,
) -> RiskBreakdown:
    """Compute the full factor breakdown for one cell (Req 3.4)."""
    p = params or load_risk_params()
    pres = 0.0 if is_land else presence_at(lon, lat, sightings, p)
    rec = 0.0 if is_land else recency_at(lon, lat, when, sightings, p)
    pw = 0.0 if is_land else min(max(p.alpha * pres + (1 - p.alpha) * rec, 0.0), 1.0)
    leth = lethality(speed_kn, p)
    r = 0.0 if is_land else min(max(pw * leth, p.risk_min), p.risk_max)
    return RiskBreakdown(cell_id, lon, lat, pres, rec, pw, leth, r)


def risk_grid(
    spec,
    when: datetime,
    speed_kn: float,
    sightings: Sequence[Sighting],
    land_mask: np.ndarray,
    params: RiskParams | None = None,
) -> np.ndarray:
    """Compute the risk field over a grid as a (ny, nx) array in [0, 1].

    ``spec`` is a GridSpec; ``land_mask[iy, ix]`` is True for land (risk 0).
    """
    p = params or load_risk_params()
    out = np.zeros((spec.ny, spec.nx), dtype=float)
    for iy in range(spec.ny):
        for ix in range(spec.nx):
            if land_mask[iy, ix]:
                continue
            lon, lat = spec.center(ix, iy)
            out[iy, ix] = risk_at(
                lon, lat, when, speed_kn, sightings, is_land=False, params=p
            )
    return out


def load_sightings(path=None) -> list[Sighting]:
    """Load the bundled sightings snapshot into validated Sighting objects."""
    import json

    from app.ingest.config import data_path

    if path is None:
        path = data_path("snapshots", "sightings.json")
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    raw = payload.get("sightings", payload) if isinstance(payload, dict) else payload
    return [Sighting.model_validate(s) for s in raw]
