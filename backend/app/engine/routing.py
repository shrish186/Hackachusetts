"""A* router on the 8-connected water grid (Lane B, tasks 2.1-2.4, design.md §6).

Edge cost (hours-equivalent) for moving into cell c at effective speed v:

    time_h + lam_risk * risk(c, t, v) * time_h + lam_wx * wave_penalty(c) * time_h

* ``v = min(cruise_kn, zone.speed_limit_kn)`` inside active speed-limited zones,
  so the slower transit is part of the ETA (Req 5.2).
* Cells in active ``prohibited`` zones are impassable (Req 5.1).
* Land cells are impassable, and diagonal moves may not cut a land corner.
* Waves: no penalty below the vessel's comfort height, a steep quadratic
  penalty up to its hard limit, impassable above it (config/vessels.yaml).
* Time dependence: whale risk is looked up in the 30-minute bucket of the
  estimated arrival time at each cell (cached per bucket).

Inputs are bundled snapshots only (Lane A's ingest + risk model), so routing is
deterministic and works offline. Fuel, ETA and waves are ESTIMATES: the wave
field is an inverse-distance interpolation of a few buoy readings and fuel
burn comes from config/vessels.yaml (synthetic: true).

Public interface:
    route_one(origin_lonlat, dest_lonlat, speed_kn, vessel, when, risk_pref, extra_zones=None) -> dict
    plan_routes(trip_request) -> dict  (2-3 alternates or a "no legal route" message)
"""
from __future__ import annotations

import heapq
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Iterable, Sequence

from itertools import pairwise

import numpy as np
from shapely.geometry import LineString, Point, shape
from shapely.prepared import prep

from app.engine.effort import effort_at
from app.engine.risk import lethality, load_risk_params, load_sightings, presence_field
from app.ingest.conditions import get_conditions as ingest_conditions
from app.ingest.config import config_path, load_yaml
from app.ingest.grid import GridSpec, default_grid, land_mask_array
from app.ingest.zones import default_zones

LonLat = tuple[float, float]
SLICE_HOURS = 3
RISK_PREF_SWEEP = (0.1, 0.5, 0.9)
PLAN_ORDER = ("Fastest", "Balanced", "Safest")
#: Corridor costs (hours-equivalent per hour) on earlier tracks, tried in order for diversity.
DIVERSITY_PENALTIES = (0.4, 1.0, 2.5)
#: Tracks overlapping more than this share within DEDUPE_BUFFER_CELLS are duplicates.
DEDUPE_OVERLAP = 0.90
DEDUPE_BUFFER_CELLS = 1.0
#: Stronger whale-risk weights tried when an option duplicates an earlier track.
WIDE_BERTH_SCALES = (3.0, 8.0)
#: Hours-equivalent weights. lam_risk scales with risk_pref; lam_wx is fixed.
LAM_RISK_MAX = 40.0
LAM_WX = 3.0
_NEIGHBORS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


class RoutingError(ValueError):
    """Bad routing input (unknown vessel, port, or ground)."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def vessels_config() -> dict[str, dict[str, float]]:
    return load_yaml(config_path("vessels.yaml"))["vessels"]


@lru_cache(maxsize=1)
def ports_config() -> dict[str, Any]:
    return load_yaml(config_path("ports.yaml"))


_COORD_RE = re.compile(r"^\s*(-?\d{1,3}(?:\.\d{1,6})?)\s*,\s*(-?\d{1,2}(?:\.\d{1,6})?)\s*$")


def parse_coord(text: str | None) -> LonLat | None:
    """Parse a "lon,lat" ground (the frontend's "plan to nearest open water")."""
    m = _COORD_RE.match(text or "")
    if not m:
        return None
    lon, lat = float(m.group(1)), float(m.group(2))
    g = default_grid()
    if not (g.min_lon <= lon <= g.max_lon and g.min_lat <= lat <= g.max_lat):
        return None
    return (lon, lat)


def ground_lonlat(ground: str) -> LonLat:
    """A named fishing ground or a "lon,lat" point inside the study area."""
    c = parse_coord(ground)
    return c if c is not None else place_lonlat("fishing_grounds", ground)


def ground_name(ground: str) -> str:
    c = parse_coord(ground)
    if c is not None:
        return f"open water at {c[1]:g}, {c[0]:g}"
    return ports_config()["fishing_grounds"][ground]["name"]


def place_lonlat(kind: str, name: str) -> LonLat:
    """Look up a port ('ports') or ground ('fishing_grounds') by id."""
    table = ports_config().get(kind, {})
    if name not in table:
        raise RoutingError(f"unknown {kind[:-1].replace('_', ' ')} '{name}'")
    return (float(table[name]["lon"]), float(table[name]["lat"]))


# ---------------------------------------------------------------------------
# Grid layers (cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _land() -> np.ndarray:
    return land_mask_array(default_grid())


@lru_cache(maxsize=1)
def _centers() -> tuple[np.ndarray, np.ndarray]:
    g = default_grid()
    lons = g.min_lon + (np.arange(g.nx) + 0.5) * g.cell_deg
    lats = g.min_lat + (np.arange(g.ny) + 0.5) * g.cell_deg
    return np.meshgrid(lons, lats)  # each (ny, nx)


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


#: Risk surfaces are cached per 30-minute time bucket (evaluated at the bucket middle).
RISK_BUCKET_MIN = 30


def risk_bucket(dt: datetime) -> datetime:
    """Start of the 30-minute bucket containing ``dt`` (UTC)."""
    dt = _as_utc(dt)
    return dt.replace(minute=dt.minute - dt.minute % RISK_BUCKET_MIN, second=0, microsecond=0)


def _slice_start(dt: datetime) -> datetime:
    """Kept for callers of the old 3-hour API; now the 30-minute risk bucket."""
    return risk_bucket(dt)


@lru_cache(maxsize=1)
def _sightings():
    return tuple(load_sightings())


@lru_cache(maxsize=1)
def _presence_grid() -> np.ndarray:
    """Time-independent presence prior per cell (0 on land)."""
    lons, lats = _centers()
    return np.where(_land(), 0.0, presence_field(lons, lats, _sightings(), load_risk_params()))


@dataclass(frozen=True)
class WhaleSurface:
    """Per-cell presence, recency and p_whale for one 30-minute bucket (0 on land)."""

    bucket: datetime
    presence: np.ndarray
    recency: np.ndarray
    p_whale: np.ndarray


@lru_cache(maxsize=1)
def _recency_terms() -> tuple[tuple[datetime, np.ndarray, np.ndarray], ...]:
    """Per sighting: (observed_at, exp(-dist/rho) grid, in-radius mask). Time-independent."""
    lons, lats = _centers()
    p = load_risk_params()
    out = []
    for sg in _sightings():
        d = _dist_grid_km(sg.lon, sg.lat)
        out.append((_as_utc(sg.observed_at), np.exp(-d / p.rho_km), d <= p.radius_km))
    return tuple(out)


def _dist_grid_km(lon: float, lat: float) -> np.ndarray:
    from app.engine.risk import _haversine_km_grid

    lons, lats = _centers()
    return _haversine_km_grid(lons, lats, lon, lat)


def _recency_grid(when: datetime) -> np.ndarray:
    """Same formula as app.engine.risk.recency_field, reusing cached distance terms."""
    tau = load_risk_params().tau_days
    when = _as_utc(when)
    prod = np.ones(_land().shape)
    for observed, decay, inside in _recency_terms():
        age_days = max((when - observed).total_seconds() / 86400.0, 0.0)
        contrib = np.clip(math.exp(-age_days / tau) * decay, 0.0, 1.0)
        prod *= np.where(inside, 1.0 - contrib, 1.0)
    return 1.0 - prod


@lru_cache(maxsize=1024)
def whale_surface(bucket: datetime) -> WhaleSurface:
    """Speed-independent whale fields for a bucket (vectorized, about 1 ms warm)."""
    params = load_risk_params()
    mid = bucket + timedelta(minutes=RISK_BUCKET_MIN / 2)
    land = _land()
    pres = _presence_grid()
    rec = np.where(land, 0.0, _recency_grid(mid))
    pw = np.where(land, 0.0, np.clip(params.alpha * pres + (1.0 - params.alpha) * rec, 0.0, 1.0))
    for arr in (rec, pw):
        arr.setflags(write=False)
    return WhaleSurface(bucket, pres, rec, pw)


def _p_whale_grid(bucket: datetime) -> np.ndarray:
    return whale_surface(risk_bucket(bucket)).p_whale


@dataclass(frozen=True)
class RiskSurface:
    """Whale risk per cell at one speed: risk = p_whale * lethality(speed)."""

    whale: WhaleSurface
    speed_kn: float
    lethality: float
    risk: np.ndarray


@lru_cache(maxsize=512)
def _risk_surface(bucket: datetime, speed_kn: float) -> RiskSurface:
    w = whale_surface(bucket)
    leth = lethality(speed_kn)
    risk = np.clip(w.p_whale * leth, 0.0, 1.0)
    risk.setflags(write=False)
    return RiskSurface(w, speed_kn, leth, risk)


def risk_surface(when: datetime, speed_kn: float) -> RiskSurface:
    """Cached risk surface per (30-minute bucket, speed).

    Speed is cached at 0.1 kn rather than 1 kn so the layer's numbers match the
    plan's lethality at the captain's exact cruise speed; the expensive,
    speed-independent part is shared through :func:`whale_surface`.
    """
    return _risk_surface(risk_bucket(when), round(float(speed_kn), 1))


@dataclass(frozen=True)
class Readings:
    points: tuple[tuple[float, float, float, float], ...]  # lon, lat, wave_m, wind_kn
    source: str
    fetched_at: str | None
    synthetic: bool


@lru_cache(maxsize=1)
def _readings() -> Readings:
    """Buoy/forecast readings from the bundled snapshot (latest per cell)."""
    res = ingest_conditions(prefer_live=False)
    g = default_grid()
    latest: dict[str, Any] = {}
    for c in res.conditions:
        if c.cell_id not in latest or _as_utc(c.time) > _as_utc(latest[c.cell_id].time):
            latest[c.cell_id] = c
    pts = []
    for c in latest.values():
        ix, iy = (int(p) for p in c.cell_id.split("_"))
        lon, lat = g.center(ix, iy)
        pts.append((lon, lat, float(c.wave_m), float(c.wind_kn)))
    fetched = res.fetched_at.isoformat().replace("+00:00", "Z") if res.fetched_at else None
    return Readings(tuple(pts), res.source, fetched, res.synthetic)


@lru_cache(maxsize=1)
def _wx_grids() -> tuple[np.ndarray, np.ndarray]:
    """(wave_m, wind_kn) per cell by inverse-distance weighting of the readings."""
    lons, lats = _centers()
    pts = _readings().points
    if not pts:
        z = np.zeros_like(lons)
        return z, z
    num_w = np.zeros_like(lons)
    num_k = np.zeros_like(lons)
    den = np.zeros_like(lons)
    for lon, lat, wave, wind in pts:
        d2 = ((lons - lon) * math.cos(math.radians(42.2))) ** 2 + (lats - lat) ** 2
        w = 1.0 / np.maximum(d2, 1e-6)
        num_w += w * wave
        num_k += w * wind
        den += w
    return num_w / den, num_k / den


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RZone:
    id: str
    name: str
    kind: str
    active_from: datetime | None
    active_to: datetime | None
    speed_limit_kn: float | None
    prohibited: bool
    geom_key: str

    def active(self, when: datetime) -> bool:
        when = _as_utc(when)
        if self.active_from is not None and when < self.active_from:
            return False
        if self.active_to is not None and when > self.active_to:
            return False
        return True


def _parse_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return _as_utc(v)
    return _as_utc(datetime.fromisoformat(str(v).replace("Z", "+00:00")))


def _to_rzone(z: Any) -> RZone:
    """Normalize a Zone model or a zone dict (simulator) into an RZone."""
    d = z.model_dump(mode="json") if hasattr(z, "model_dump") else dict(z)
    geom = d.get("geometry") or {}
    return RZone(
        id=str(d.get("id", "candidate")),
        name=str(d.get("name", d.get("id", "candidate"))),
        kind=str(d.get("kind", "candidate")),
        active_from=_parse_dt(d.get("active_from")),
        active_to=_parse_dt(d.get("active_to")),
        speed_limit_kn=float(d["speed_limit_kn"]) if d.get("speed_limit_kn") is not None else None,
        prohibited=bool(d.get("prohibited", False)),
        geom_key=json.dumps(geom, sort_keys=True),
    )


@lru_cache(maxsize=256)
def _zone_mask(geom_key: str) -> np.ndarray:
    """Boolean (ny, nx) mask of cells whose centroid lies in the zone polygon."""
    g = default_grid()
    poly = prep(shape(json.loads(geom_key)))
    out = np.zeros((g.ny, g.nx), dtype=bool)
    for iy in range(g.ny):
        for ix in range(g.nx):
            out[iy, ix] = poly.covers(Point(*g.center(ix, iy)))
    return out


def _zone_set(extra_zones: Iterable[Any] | None) -> list[RZone]:
    """Snapshot zones plus extra (candidate) zones, de-duplicated by id."""
    out: dict[str, RZone] = {z.id: _to_rzone(z) for z in default_zones()}
    for z in extra_zones or []:
        rz = _to_rzone(z)
        out[rz.id] = rz
    return list(out.values())


# ---------------------------------------------------------------------------
# Rounding (one helper for every number the API and narrative show)
# ---------------------------------------------------------------------------

#: Decimal places per unit. Every user-visible number goes through :func:`rnd`
#: once, at the source, so plan cards, narrative and brief show the same value.
DECIMALS = {"m": 1, "kn": 1, "h": 2, "l": 1, "nm": 1, "risk": 3, "exposure": 4, "deg": 4, "effort": 3}


def rnd(value: float, unit: str) -> float:
    """Round ``value`` for display in ``unit`` (see DECIMALS)."""
    return round(float(value), DECIMALS[unit])


# ---------------------------------------------------------------------------
# A*
# ---------------------------------------------------------------------------

#: A port may sit in a coastal land cell; it is moved to water at most this many cells away.
MAX_ORIGIN_SNAP_CELLS = 3


def _step_nm(g: GridSpec, ix: int, iy: int, dx: int, dy: int) -> float:
    lat = g.min_lat + (iy + 0.5 + dy / 2) * g.cell_deg
    return 60.0 * g.cell_deg * math.hypot(dx * math.cos(math.radians(lat)), dy)


def _dist_nm(a: LonLat, b: LonLat) -> float:
    return 60.0 * math.hypot((b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2)), b[1] - a[1])


def _nearest_open(g: GridSpec, lonlat: LonLat, blocked: np.ndarray, max_r: int = 40) -> tuple[int, int] | None:
    """Closest unblocked cell to a point, searching square rings out to ``max_r`` cells."""
    ix0, iy0 = g.index_of(*lonlat)
    best, best_d = None, float("inf")
    for r in range(0, max_r + 1):
        for iy in range(max(iy0 - r, 0), min(iy0 + r, g.ny - 1) + 1):
            for ix in range(max(ix0 - r, 0), min(ix0 + r, g.nx - 1) + 1):
                if max(abs(ix - ix0), abs(iy - iy0)) != r or blocked[iy, ix]:
                    continue
                d = _dist_nm(lonlat, g.center(ix, iy))
                if d < best_d:
                    best, best_d = (ix, iy), d
        if best is not None:
            return best
    return None


def _in_grid(g: GridSpec, lonlat: LonLat) -> bool:
    return g.min_lon <= lonlat[0] <= g.max_lon and g.min_lat <= lonlat[1] <= g.max_lat


def _segment_clear(g: GridSpec, a: LonLat, b: LonLat, blocked: np.ndarray) -> bool:
    """True if the straight segment a-b only passes over unblocked cells."""
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (0.25 * g.cell_deg)) + 1)
    for i in range(n + 1):
        t = i / n
        ix, iy = g.index_of(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        if blocked[iy, ix]:
            return False
    return True


def _dense_waypoints(g: GridSpec, path: list[tuple[int, int]], blocked: np.ndarray) -> list[tuple[float, float]]:
    """Cell-centre track simplified only to a 0.5 cell tolerance.

    Falls back to every cell centre if simplification would cut over a blocked cell.
    """
    pts = [g.center(ix, iy) for ix, iy in path]
    if len(pts) > 2:
        simple = list(LineString(pts).simplify(0.5 * g.cell_deg, preserve_topology=False).coords)
        if all(_segment_clear(g, a, b, blocked) for a, b in pairwise(simple)):
            pts = simple
    return [(rnd(lon, "deg"), rnd(lat, "deg")) for lon, lat in pts]


_ROUTE_CACHE: dict[tuple, dict[str, Any]] = {}
_ROUTE_CACHE_MAX = 8192


def route_one(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Memoized :func:`_route_one` (simulator re-routes the same fleet often).

    Returns a shallow copy so callers can't corrupt the cache.
    """
    try:
        key = _cache_key(*args, **kwargs)
    except TypeError:
        return _route_one(*args, **kwargs)
    hit = _ROUTE_CACHE.get(key)
    if hit is None:
        hit = _route_one(*args, **kwargs)
        if len(_ROUTE_CACHE) >= _ROUTE_CACHE_MAX:
            _ROUTE_CACHE.clear()
        _ROUTE_CACHE[key] = hit
    return {k: (list(v) if isinstance(v, list) else v) for k, v in hit.items()}


def _cache_key(origin_lonlat, dest_lonlat, speed_kn, vessel, when, risk_pref, extra_zones=None, **kw) -> tuple:
    zones = tuple(json.dumps(z.model_dump(mode="json") if hasattr(z, "model_dump") else z, sort_keys=True, default=str)
                  for z in (extra_zones or []))
    return (tuple(origin_lonlat), tuple(dest_lonlat), float(speed_kn), vessel, _as_utc(when).isoformat(),
            float(risk_pref), zones, tuple(sorted((k, v if not isinstance(v, frozenset) else tuple(sorted(v))) for k, v in kw.items())))


def _empty(reason: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "reason": reason, "access_lost": None, "waypoints": [], "eta_hours": 0.0,
            "fuel_est_l": 0.0, "zones_crossed": [], "zones_avoided": [], "max_wave_m": 0.0, "max_wind_kn": 0.0,
            "risk_exposure": 0.0, "slow_zone_hours": 0.0, "origin_adjusted_nm": 0.0, "cells": [], **extra}


def _access_lost(g: GridSpec, which: str, point: LonLat, reason: str, zone: RZone | None,
                 open_mask: np.ndarray) -> dict[str, Any]:
    """Explicit 'cannot reach this point' result with the nearest open alternative."""
    alt = _nearest_open(g, point, open_mask)
    nearest = None
    if alt is not None:
        lon, lat = g.center(*alt)
        nearest = {"lon": rnd(lon, "deg"), "lat": rnd(lat, "deg"), "distance_nm": rnd(_dist_nm(point, (lon, lat)), "nm")}
    code = "closed_zone" if zone else ("land" if "land" in reason else ("outside" if "outside" in reason else "no_water"))
    info = {
        "endpoint": which,
        "code": code,
        "reason": reason,
        "zone_id": zone.id if zone else None,
        "zone_name": zone.name if zone else None,
        "zone_active_to": zone.active_to.isoformat().replace("+00:00", "Z") if zone and zone.active_to else None,
        "nearest_open": nearest,
    }
    return _empty(f"{which} {reason}", access_lost=info)


def _zone_at(g: GridSpec, lonlat: LonLat, zones: list[RZone]) -> RZone | None:
    """First active prohibited zone whose polygon covers the point (exact test)."""
    pt = Point(*lonlat)
    for z in zones:
        if z.prohibited and _zone_prep(z.geom_key).covers(pt):
            return z
    return None


@lru_cache(maxsize=256)
def _zone_prep(geom_key: str):
    return prep(shape(json.loads(geom_key)))


def _route_one(
    origin_lonlat: LonLat,
    dest_lonlat: LonLat,
    speed_kn: float,
    vessel: str,
    when: datetime,
    risk_pref: float,
    extra_zones: Sequence[Any] | None = None,
    *,
    ignore_prohibited: bool = False,
    ignore_wave_limit: bool = False,
    lam_scale: float = 1.0,
    avoid_cells: frozenset[str] = frozenset(),
    avoid_penalty: float = 0.0,
) -> dict[str, Any]:
    """Route one leg on the water grid. All outputs are estimates.

    Args:
        origin_lonlat, dest_lonlat: (lon, lat) decimal degrees.
        speed_kn: cruise speed, knots (> 0).
        vessel: key in config/vessels.yaml.
        when: UTC departure time.
        risk_pref: 0 = fastest, 1 = safest.
        extra_zones: candidate zones (Zone models or dicts) added to the snapshot zones.
        ignore_prohibited, ignore_wave_limit: used only to explain "no legal route".
        lam_scale: multiplier on the whale-risk weight.
        avoid_cells, avoid_penalty: extra cost per hour in these cells (route diversity).

    Returns:
        dict with ok, waypoints [(lon, lat)], eta_hours, fuel_est_l, zones_crossed
        (active zone ids), zones_avoided (active prohibited zone ids not entered),
        max_wave_m, max_wind_kn, risk_exposure (sum risk*hours), slow_zone_hours,
        origin_adjusted_nm, cells, reason (when ok is False) and access_lost.

        ``access_lost`` is None unless the destination (or origin) is on land,
        outside the study area, or inside an active closed zone. The router never
        moves a destination: it returns ok=False with ``access_lost = {endpoint,
        reason, zone_id, zone_name, zone_active_to, nearest_open: {lon, lat,
        distance_nm}}``.
    """
    if vessel not in vessels_config():
        raise RoutingError(f"unknown vessel '{vessel}'")
    if not (speed_kn > 0):
        raise RoutingError("speed_kn must be positive")
    risk_pref = min(max(float(risk_pref), 0.0), 1.0)
    vcfg = vessels_config()[vessel]
    comfort, hard = float(vcfg["comfort_wave_m"]), float(vcfg["hard_wave_limit_m"])
    burn_lph, vessel_cruise = float(vcfg["fuel_burn_l_per_h"]), float(vcfg["cruise_kn"])

    g = default_grid()
    when = _as_utc(when)
    land = _land()
    wave, wind = _wx_grids()
    zones = _zone_set(extra_zones)
    active = [z for z in zones if z.active(when)]

    prohibited = np.zeros_like(land)
    speed_cap = np.full(land.shape, float(speed_kn))
    for z in active:
        m = _zone_mask(z.geom_key)
        if z.prohibited:
            prohibited |= m
        if z.speed_limit_kn is not None:
            speed_cap = np.where(m, np.minimum(speed_cap, z.speed_limit_kn), speed_cap)
    closed = land | (prohibited if not ignore_prohibited else np.zeros_like(land))
    blocked = closed | (wave > hard if not ignore_wave_limit else np.zeros_like(land))
    wave_pen = np.clip((wave - comfort) / max(hard - comfort, 1e-6), 0.0, None) ** 2
    closed_zones = [] if ignore_prohibited else [z for z in active if z.prohibited]

    # Destination: never relocate. Report access_lost instead.
    if not _in_grid(g, dest_lonlat):
        return _access_lost(g, "destination", dest_lonlat, "is outside the study area", None, closed)
    dz = _zone_at(g, dest_lonlat, closed_zones)
    if dz is not None:
        return _access_lost(g, "destination", dest_lonlat, f"is inside active closed zone {dz.name}", dz, closed)
    goal = g.index_of(*dest_lonlat)
    if land[goal[1], goal[0]]:
        return _access_lost(g, "destination", dest_lonlat, "is on land", None, closed)
    if closed[goal[1], goal[0]]:
        zc = next((z for z in closed_zones if _zone_mask(z.geom_key)[goal[1], goal[0]]), None)
        return _access_lost(g, "destination", dest_lonlat, f"is inside active closed zone {zc.name if zc else ''}".strip(), zc, closed)
    if blocked[goal[1], goal[0]]:
        return _empty(f"waves at the destination exceed the {hard:g} m limit for this vessel")

    # Origin: a harbour may fall in a coastal land cell; move it to water nearby, and say so.
    if not _in_grid(g, origin_lonlat):
        return _access_lost(g, "origin", origin_lonlat, "is outside the study area", None, closed)
    oz = _zone_at(g, origin_lonlat, closed_zones)
    if oz is not None:
        return _access_lost(g, "origin", origin_lonlat, f"is inside active closed zone {oz.name}", oz, closed)
    start = _nearest_open(g, origin_lonlat, blocked, max_r=MAX_ORIGIN_SNAP_CELLS)
    if start is None:
        return _access_lost(g, "origin", origin_lonlat, "has no open water nearby", None, closed)
    origin_adjusted = rnd(_dist_nm(origin_lonlat, g.center(*start)), "nm")

    lam_risk = LAM_RISK_MAX * risk_pref * lam_scale
    reuse = np.zeros(land.shape)
    for cid in avoid_cells:
        ax_, ay_ = (int(p) for p in cid.split("_"))
        reuse[ay_, ax_] = avoid_penalty
    leth_cache: dict[float, float] = {}

    def leth(v: float) -> float:
        if v not in leth_cache:
            leth_cache[v] = lethality(v)
        return leth_cache[v]

    gx, gy = goal
    goal_lat = g.center(gx, gy)[1]

    def h(ix: int, iy: int) -> float:
        lat = g.center(ix, iy)[1]
        coslat = math.cos(math.radians(max(abs(lat), abs(goal_lat))))
        nm = 60.0 * g.cell_deg * math.hypot((ix - gx) * coslat, iy - gy)
        return 0.999 * nm / speed_kn

    best: dict[tuple[int, int], float] = {start: 0.0}
    t_at: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    heap = [(h(*start), 0.0, start)]
    done: set[tuple[int, int]] = set()
    while heap:
        _, cost, node = heapq.heappop(heap)
        if node in done:
            continue
        if node == goal:
            break
        done.add(node)
        ix, iy = node
        t0 = t_at[node]
        pw_grid = _p_whale_grid(_slice_start(when + timedelta(hours=t0)))
        for dx, dy in _NEIGHBORS:
            nx_, ny_ = ix + dx, iy + dy
            if not (0 <= nx_ < g.nx and 0 <= ny_ < g.ny) or blocked[ny_, nx_]:
                continue
            if dx and dy and (blocked[iy, nx_] or blocked[ny_, ix]):
                continue  # no corner cutting past land or closed cells
            v = float(speed_cap[ny_, nx_])
            dt = _step_nm(g, ix, iy, dx, dy) / v
            step = dt * (1.0 + lam_risk * pw_grid[ny_, nx_] * leth(v) + LAM_WX * wave_pen[ny_, nx_] + reuse[ny_, nx_])
            nc = cost + step
            nb = (nx_, ny_)
            if nc < best.get(nb, float("inf")):
                best[nb], t_at[nb], parent[nb] = nc, t0 + dt, node
                heapq.heappush(heap, (nc + h(nx_, ny_), nc, nb))
    if goal not in best:
        return _empty("no water path avoids land, closed zones and wave limits", origin_adjusted_nm=origin_adjusted)

    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()

    eta = risk_exp = fuel = slow_h = 0.0
    for (ax, ay), (bx, by) in pairwise(path):
        v = float(speed_cap[by, bx])
        dt = _step_nm(g, ax, ay, bx - ax, by - ay) / v
        pw = _p_whale_grid(_slice_start(when + timedelta(hours=eta)))[by, bx]
        risk_exp += float(pw) * leth(v) * dt
        fuel += burn_lph * dt * (v / vessel_cruise) ** 2
        if v < speed_kn:
            slow_h += dt
        eta += dt
    max_wave = max(float(wave[iy, ix]) for ix, iy in path)
    max_wind = max(float(wind[iy, ix]) for ix, iy in path)
    on_path = set(path)
    crossed, avoided = [], []
    for z in active:
        m = _zone_mask(z.geom_key)
        if any(m[iy, ix] for ix, iy in on_path):
            crossed.append(z.id)
        elif z.prohibited:
            avoided.append(z.id)

    return {
        "ok": True,
        "reason": None,
        "access_lost": None,
        "waypoints": _dense_waypoints(g, path, blocked),
        "eta_hours": rnd(eta, "h"),
        "fuel_est_l": rnd(fuel, "l"),
        "zones_crossed": crossed,
        "zones_avoided": avoided,
        "max_wave_m": rnd(max_wave, "m"),
        "max_wind_kn": rnd(max_wind, "kn"),
        "risk_exposure": rnd(risk_exp, "exposure"),
        "slow_zone_hours": rnd(slow_h, "h"),
        "origin_adjusted_nm": origin_adjusted,
        "cells": [g.cell_id(ix, iy) for ix, iy in path],
    }


# ---------------------------------------------------------------------------
# Alternates
# ---------------------------------------------------------------------------


def _field(req: Any, name: str, default: Any = None) -> Any:
    return req.get(name, default) if isinstance(req, dict) else getattr(req, name, default)


def _track(r: dict[str, Any]) -> LineString:
    g = default_grid()
    pts = [g.center(*(int(p) for p in c.split("_"))) for c in r["cells"]]
    return LineString(pts if len(pts) > 1 else pts * 2)


def track_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Share of the tracks lying within one cell of each other (min of both directions)."""
    ta, tb = _track(a), _track(b)
    buf = DEDUPE_BUFFER_CELLS * default_grid().cell_deg
    if ta.length == 0 or tb.length == 0:
        return 1.0
    return min(tb.intersection(ta.buffer(buf)).length / tb.length, ta.intersection(tb.buffer(buf)).length / ta.length)


def _distinct(r: dict[str, Any], others: Sequence[dict[str, Any]]) -> bool:
    return all(track_overlap(r, o) <= DEDUPE_OVERLAP for o in others)


def _near_cells(routes: Sequence[dict[str, Any]], radius: int = 1) -> frozenset[str]:
    """Cells within ``radius`` cells of any of the routes' interior cells."""
    g = default_grid()
    out: set[str] = set()
    for r in routes:
        for c in r["cells"][2:-2]:
            ix, iy = (int(p) for p in c.split("_"))
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if 0 <= ix + dx < g.nx and 0 <= iy + dy < g.ny:
                        out.add(g.cell_id(ix + dx, iy + dy))
    return frozenset(out)


def zone_names() -> dict[str, str]:
    return {z.id: z.name for z in default_zones()}


def plan_routes(trip_request: Any, extra_zones: Sequence[Any] | None = None) -> dict[str, Any]:
    """Fastest / Balanced / Safest alternates (Req 4.1, 5.3, 5.4).

    Each option uses a whale-risk weight (0.1, 0.5, 0.9). An option whose track
    overlaps an earlier one by more than 90 % (1-cell buffer) is a duplicate; we
    then retry with a stronger risk weight, and finally with a cost on the
    earlier tracks' corridor, so captains get 2-3 different tracks whenever the
    geometry allows. ``single_route_reason`` explains when it does not.

    ``max_hours`` is the out-and-back budget, so a plan needs 2 * eta <= max_hours.
    Plans are ranked for the requester's own ``risk_pref``.
    """
    port = _field(trip_request, "port")
    ground = _field(trip_request, "target_ground") or "stellwagen_bank"
    vessel = _field(trip_request, "vessel")
    cruise = float(_field(trip_request, "cruise_kn"))
    max_hours = float(_field(trip_request, "max_hours"))
    pref = float(_field(trip_request, "risk_pref", 0.5))
    window = _field(trip_request, "depart_window")
    depart = _parse_dt(window[0])
    origin = place_lonlat("ports", port)
    dest = ground_lonlat(ground)

    rd = _readings()
    data = {"source": rd.source, "fetched_at": rd.fetched_at, "synthetic": rd.synthetic}
    base = {"origin": origin, "dest": dest, "depart": depart.isoformat().replace("+00:00", "Z"),
            "port": port, "ground": ground, "data": data, "access_lost": None, "single_route_reason": None,
            "single_route": None}

    def route(w: float, **kw: Any) -> dict[str, Any]:
        return route_one(origin, dest, cruise, vessel, depart, w, extra_zones, **kw)

    first = route(RISK_PREF_SWEEP[0])
    if first.get("access_lost"):
        return {**base, "ok": False, "plans": [], "access_lost": first["access_lost"],
                "message": explain_access_lost(first["access_lost"], ground)}

    chosen: list[tuple[str, float, str, dict[str, Any]]] = []  # name, weight, method, route
    attempts: list[dict[str, Any]] = []
    for w, name in zip(RISK_PREF_SWEEP, PLAN_ORDER):
        def candidates(w: float = w, name: str = name):
            if name == "Fastest":
                yield "risk_weight", first
                return
            yield "risk_weight", route(w)
            for s in WIDE_BERTH_SCALES:
                yield "risk_weight", route(w, lam_scale=s)
            near = _near_cells([c[3] for c in chosen])
            for pen in DIVERSITY_PENALTIES:
                yield "corridor", route(w, avoid_cells=near, avoid_penalty=pen)

        for method, r in candidates():
            if not r["ok"]:
                continue
            attempts.append(r)
            if 2 * r["eta_hours"] > max_hours:
                continue
            if _distinct(r, [c[3] for c in chosen]):
                chosen.append((name, w, method, r))
                break

    if not chosen:
        ok_runs = [(0.0, r) for r in attempts]
        return {**base, "ok": False, "plans": [], "message": explain_no_route(
            origin, dest, cruise, vessel, depart, max_hours, ok_runs, extra_zones)}

    single_reason = None
    single_route = None
    if len(chosen) == 1:
        longer = [r for r in attempts if 2 * r["eta_hours"] > max_hours and _distinct(r, [chosen[0][3]])]
        if longer:
            need = rnd(2 * min(r["eta_hours"] for r in longer), "h")
            single_route = {"code": "over_budget", "need_hours": need, "max_hours": max_hours}
            single_reason = (f"All weightings give the same route because every different track needs about "
                             f"{need:g} h round trip, more than the {max_hours:g} h limit.")
        else:
            single_route = {"code": "same_corridor"}
            single_reason = ("All weightings give the same route because the open water between the port and the "
                             "ground leaves no meaningfully different track.")

    # Order by ETA (Fastest first). Names follow the measured numbers, not the
    # weight that produced a track: "Safest" only for the minimum-risk plan.
    chosen.sort(key=lambda c: (c[3]["eta_hours"], c[3]["risk_exposure"]))
    fastest = chosen[0][3]
    names = name_plans([c[3] for c in chosen], fastest)
    chosen = [(names[i], w, m, r) for i, (_, w, m, r) in enumerate(chosen)]
    min_eta = min(c[3]["eta_hours"] for c in chosen) or 1.0
    max_risk = max(c[3]["risk_exposure"] for c in chosen) or 1.0
    scores = [(1 - pref) * c[3]["eta_hours"] / min_eta + pref * c[3]["risk_exposure"] / max_risk for c in chosen]
    recommended = scores.index(min(scores))
    effort = rnd(effort_at(*dest), "effort")
    plans = []
    for rank, (name, w, method, r) in enumerate(chosen, start=1):
        p = {k: v for k, v in r.items() if k not in ("ok", "reason", "cells", "access_lost")}
        p["name"] = name
        p["rank"] = rank
        p["recommended"] = rank - 1 == recommended
        p["risk_weight"] = w
        p["method"] = method
        p["effort_proxy"] = effort
        p["round_trip_hours"] = rnd(2 * r["eta_hours"], "h")
        p["vs_fastest"] = {"extra_hours": rnd(r["eta_hours"] - fastest["eta_hours"], "h"),
                           "risk_change": rnd(r["risk_exposure"] - fastest["risk_exposure"], "exposure")}
        p["weather_window"] = {
            "from": base["depart"],
            "to": (depart + timedelta(hours=2 * r["eta_hours"])).isoformat().replace("+00:00", "Z"),
            "max_wave_m": r["max_wave_m"],
            "max_wind_kn": r["max_wind_kn"],
        }
        plans.append(p)
    return {**base, "ok": True, "plans": plans, "message": None, "single_route_reason": single_reason,
            "single_route": single_route}


def name_plans(routes: Sequence[dict[str, Any]], fastest: dict[str, Any]) -> list[str]:
    """Fastest = least time. Safest = the minimum whale-risk exposure, and only if
    it is below Fastest's. Balanced = less risk than Fastest and less time than
    Safest. Alternative = a different track that is not better on either measure."""
    min_risk = min(r["risk_exposure"] for r in routes)
    safest = min(routes, key=lambda r: (r["risk_exposure"], r["eta_hours"]))
    if safest is fastest or safest["risk_exposure"] >= fastest["risk_exposure"] or safest["risk_exposure"] != min_risk:
        safest = None
    out = []
    for r in routes:
        if r is fastest:
            out.append("Fastest")
        elif r is safest:
            out.append("Safest")
        elif r["risk_exposure"] < fastest["risk_exposure"] and (safest is None or r["eta_hours"] < safest["eta_hours"]):
            out.append("Balanced")
        else:
            out.append("Alternative")
    if out.count("Balanced") > 1:  # keep one Balanced: the quickest of them
        first = out.index("Balanced")
        out = [n if (n != "Balanced" or i == first) else "Alternative" for i, n in enumerate(out)]
    if out.count("Alternative") > 1:
        n = 0
        for i, name in enumerate(out):
            if name == "Alternative":
                n += 1
                out[i] = f"Alternative {n}"
    return out


def explain_access_lost(info: dict[str, Any], ground: str) -> str:
    """Plain message for an access_lost result (Lane D and the agent both use it)."""
    try:
        name = ground_name(ground)
    except KeyError:
        name = ground
    where = f"The target ground {name}" if info["endpoint"] == "destination" else "The departure port"
    msg = f"{where} {info['reason']}"
    if info.get("zone_active_to"):
        msg += f" until {info['zone_active_to'][:10]}"
    msg += "."
    alt = info.get("nearest_open")
    if alt:
        msg += (f" Nearest open water is {alt['distance_nm']:g} nm away at {alt['lat']:g}, {alt['lon']:g}."
                " Relax: target ground or departure time.")
    return msg


def explain_no_route(origin: LonLat, dest: LonLat, cruise: float, vessel: str, depart: datetime,
                     max_hours: float, raw: list, extra_zones: Sequence[Any] | None) -> str:
    """Name the binding constraint and what to relax (Req 5.4)."""
    if raw:
        need = rnd(2 * min(r["eta_hours"] for _, r in raw), "h")
        return f"No legal route within {max_hours:g} h. Relax: max_hours (the shortest legal round trip needs about {need:g} h)."
    if route_one(origin, dest, cruise, vessel, depart, 0.1, extra_zones, ignore_wave_limit=True)["ok"]:
        limit = vessels_config()[vessel]["hard_wave_limit_m"]
        return f"No legal route: waves exceed the {limit:g} m limit for this vessel on every path. Relax: departure time or vessel."
    if route_one(origin, dest, cruise, vessel, depart, 0.1, extra_zones, ignore_prohibited=True)["ok"]:
        return "No legal route: active closed zones block every path. Relax: departure time (after the closure ends) or target ground."
    return "No legal route: the destination is not reachable by water. Relax: target ground."
