"""A* router on the 8-connected water grid (Lane B, tasks 2.1-2.4, design.md §6).

Edge cost (hours-equivalent) for moving into cell c at effective speed v:

    time_h + lam_risk * risk(c, t, v) * time_h + lam_wx * wave_penalty(c) * time_h

* ``v = min(cruise_kn, zone.speed_limit_kn)`` inside active speed-limited zones,
  so the slower transit is part of the ETA (Req 5.2).
* Cells in active ``prohibited`` zones are impassable (Req 5.1).
* Land cells are impassable, and diagonal moves may not cut a land corner.
* Waves: no penalty below the vessel's comfort height, a steep quadratic
  penalty up to its hard limit, impassable above it (config/vessels.yaml).
* Time dependence: risk and waves are looked up in the 3-hour slice of the
  estimated arrival time at each cell.

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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Iterable, Sequence

import numpy as np
from shapely.geometry import Point, shape
from shapely.prepared import prep

from app.engine.effort import effort_at
from app.engine.risk import lethality, load_risk_params, load_sightings, p_whale
from app.ingest.conditions import get_conditions as ingest_conditions
from app.ingest.config import config_path, load_yaml
from app.ingest.grid import GridSpec, default_grid, land_mask_array
from app.ingest.zones import default_zones

LonLat = tuple[float, float]
SLICE_HOURS = 3
RISK_PREF_SWEEP = (0.1, 0.5, 0.9)
PLAN_NAMES = {0.1: "Fastest", 0.5: "Balanced", 0.9: "Safest", 1.0: "Wide berth", -1.0: "Alternate track"}
#: Extra hours-equivalent per hour in cells used by an earlier plan (path diversity).
REUSE_PENALTY = 0.6
#: Extra risk-weight multipliers tried when the sweep yields fewer than 2 distinct routes.
WIDE_BERTH_SCALES = (4.0, 12.0)
#: Hours-equivalent weights. lam_risk scales with risk_pref; lam_wx is fixed.
LAM_RISK_MAX = 40.0
LAM_WX = 3.0
#: Routes whose cell sets overlap more than this (Jaccard) are duplicates.
DEDUPE_JACCARD = 0.85
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


def _slice_start(dt: datetime) -> datetime:
    dt = _as_utc(dt)
    return dt.replace(hour=dt.hour - dt.hour % SLICE_HOURS, minute=0, second=0, microsecond=0)


@lru_cache(maxsize=1)
def _sightings():
    return tuple(load_sightings())


@lru_cache(maxsize=64)
def _p_whale_grid(slice_start: datetime) -> np.ndarray:
    """p_whale per cell for one 3-hour slice (0 on land). Speed applied later."""
    g = default_grid()
    land = _land()
    params = load_risk_params()
    s = _sightings()
    out = np.zeros((g.ny, g.nx))
    mid = slice_start + timedelta(hours=SLICE_HOURS / 2)
    for iy in range(g.ny):
        for ix in range(g.nx):
            if not land[iy, ix]:
                lon, lat = g.center(ix, iy)
                out[iy, ix] = p_whale(lon, lat, mid, s, params)
    return out


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
# A*
# ---------------------------------------------------------------------------


def _step_nm(g: GridSpec, ix: int, iy: int, dx: int, dy: int) -> float:
    lat = g.min_lat + (iy + 0.5 + dy / 2) * g.cell_deg
    return 60.0 * g.cell_deg * math.hypot(dx * math.cos(math.radians(lat)), dy)


def _nearest_water(g: GridSpec, lonlat: LonLat, blocked: np.ndarray) -> tuple[int, int] | None:
    """Closest passable cell to a point (ports sit on the coast, often in land cells)."""
    ix0, iy0 = g.index_of(*lonlat)
    best, best_d = None, float("inf")
    for r in range(0, 12):
        for iy in range(max(iy0 - r, 0), min(iy0 + r, g.ny - 1) + 1):
            for ix in range(max(ix0 - r, 0), min(ix0 + r, g.nx - 1) + 1):
                if max(abs(ix - ix0), abs(iy - iy0)) != r or blocked[iy, ix]:
                    continue
                lon, lat = g.center(ix, iy)
                d = (lon - lonlat[0]) ** 2 + (lat - lonlat[1]) ** 2
                if d < best_d:
                    best, best_d = (ix, iy), d
        if best is not None:
            return best
    return None


def _simplify(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Drop cells in the middle of straight runs (same step direction)."""
    if len(cells) <= 2:
        return cells
    out = [cells[0]]
    for a, b, c in zip(cells, cells[1:], cells[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(b)
    out.append(cells[-1])
    return out


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

    Returns:
        dict with ok, waypoints [(lon, lat)], eta_hours, fuel_est_l, zones_crossed
        (active zone ids), zones_avoided (active prohibited zone ids not entered),
        max_wave_m, max_wind_kn, risk_exposure (sum risk*hours), slow_zone_hours,
        cells, and reason (when ok is False).
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
    blocked = land.copy()
    if not ignore_prohibited:
        blocked |= prohibited
    if not ignore_wave_limit:
        blocked |= wave > hard
    wave_pen = np.clip((wave - comfort) / max(hard - comfort, 1e-6), 0.0, None) ** 2

    def fail(reason: str) -> dict[str, Any]:
        return {"ok": False, "reason": reason, "waypoints": [], "eta_hours": 0.0, "fuel_est_l": 0.0,
                "zones_crossed": [], "zones_avoided": [], "max_wave_m": 0.0, "max_wind_kn": 0.0,
                "risk_exposure": 0.0, "slow_zone_hours": 0.0, "cells": []}

    start = _nearest_water(g, origin_lonlat, blocked)
    goal = _nearest_water(g, dest_lonlat, blocked)
    if start is None or goal is None:
        return fail("origin or destination has no reachable water nearby")

    lam_risk = LAM_RISK_MAX * risk_pref * lam_scale
    reuse = np.zeros(land.shape)
    for cid in avoid_cells:
        ax_, ay_ = (int(p) for p in cid.split("_"))
        reuse[ay_, ax_] = REUSE_PENALTY
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
    closed: set[tuple[int, int]] = set()
    while heap:
        _, cost, node = heapq.heappop(heap)
        if node in closed:
            continue
        if node == goal:
            break
        closed.add(node)
        ix, iy = node
        t0 = t_at[node]
        for dx, dy in _NEIGHBORS:
            nx_, ny_ = ix + dx, iy + dy
            if not (0 <= nx_ < g.nx and 0 <= ny_ < g.ny) or blocked[ny_, nx_]:
                continue
            if dx and dy and (blocked[iy, nx_] or blocked[ny_, ix]):
                continue  # no corner cutting past land or closed cells
            v = float(speed_cap[ny_, nx_])
            dt = _step_nm(g, ix, iy, dx, dy) / v
            pw = _p_whale_grid(_slice_start(when + timedelta(hours=t0)))[ny_, nx_]
            step = dt * (1.0 + lam_risk * pw * leth(v) + LAM_WX * wave_pen[ny_, nx_] + reuse[ny_, nx_])
            nc = cost + step
            nb = (nx_, ny_)
            if nc < best.get(nb, float("inf")):
                best[nb], t_at[nb], parent[nb] = nc, t0 + dt, node
                heapq.heappush(heap, (nc + h(nx_, ny_), nc, nb))
    if goal not in best:
        return fail("no water path avoids land, closed zones and wave limits")

    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()

    eta = risk_exp = fuel = slow_h = 0.0
    max_wave = max_wind = 0.0
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        v = float(speed_cap[by, bx])
        dt = _step_nm(g, ax, ay, bx - ax, by - ay) / v
        pw = _p_whale_grid(_slice_start(when + timedelta(hours=eta)))[by, bx]
        risk_exp += float(pw) * leth(v) * dt
        fuel += burn_lph * dt * (v / vessel_cruise) ** 2
        if v < speed_kn:
            slow_h += dt
        eta += dt
    for ix, iy in path:
        max_wave = max(max_wave, float(wave[iy, ix]))
        max_wind = max(max_wind, float(wind[iy, ix]))
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
        "waypoints": [tuple(round(c, 4) for c in g.center(ix, iy)) for ix, iy in _simplify(path)],
        "eta_hours": round(eta, 2),
        "fuel_est_l": round(fuel, 1),
        "zones_crossed": crossed,
        "zones_avoided": avoided,
        "max_wave_m": round(max_wave, 2),
        "max_wind_kn": round(max_wind, 1),
        "risk_exposure": round(float(risk_exp), 4),
        "slow_zone_hours": round(slow_h, 2),
        "cells": [g.cell_id(ix, iy) for ix, iy in path],
    }


# ---------------------------------------------------------------------------
# Alternates
# ---------------------------------------------------------------------------


def _field(req: Any, name: str, default: Any = None) -> Any:
    return req.get(name, default) if isinstance(req, dict) else getattr(req, name, default)


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(len(sa | sb), 1)


def zone_names() -> dict[str, str]:
    return {z.id: z.name for z in default_zones()}


def plan_routes(trip_request: Any, extra_zones: Sequence[Any] | None = None) -> dict[str, Any]:
    """2-3 alternates by sweeping risk_pref 0.1/0.5/0.9, de-duplicated (Req 5.3, 5.4).

    ``max_hours`` is the out-and-back budget, so a plan needs 2 * eta <= max_hours.
    Plans are ranked for the requester's own ``risk_pref``.

    Returns {"ok", "plans": [...], "message", "origin", "dest", "depart",
    "data": {source, fetched_at, synthetic}}.
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
    dest = place_lonlat("fishing_grounds", ground)

    raw = []
    for rp in RISK_PREF_SWEEP:
        r = route_one(origin, dest, cruise, vessel, depart, rp, extra_zones)
        if r["ok"]:
            raw.append((rp, r))

    unique: list[tuple[float, dict[str, Any]]] = []
    for rp, r in raw:
        if all(_jaccard(r["cells"], u["cells"]) < DEDUPE_JACCARD for _, u in unique):
            unique.append((rp, r))
    # The sweep often converges on one path; try a wider whale-risk berth so the
    # captain still gets a real alternative (Req 4.1: 2-3 plans).
    for scale in WIDE_BERTH_SCALES:
        if len(unique) >= 2 or not raw:
            break
        r = route_one(origin, dest, cruise, vessel, depart, 1.0, extra_zones, lam_scale=scale)
        if r["ok"] and all(_jaccard(r["cells"], u["cells"]) < DEDUPE_JACCARD for _, u in unique):
            unique.append((1.0, r))
    # Still one corridor: route again with a cost on cells already used.
    if len(unique) == 1:
        used = frozenset(c for c in unique[0][1]["cells"][1:-1])
        r = route_one(origin, dest, cruise, vessel, depart, 0.5, extra_zones, avoid_cells=used)
        if r["ok"] and _jaccard(r["cells"], unique[0][1]["cells"]) < DEDUPE_JACCARD:
            unique.append((-1.0, r))
    legal = [(rp, r) for rp, r in unique if 2 * r["eta_hours"] <= max_hours]

    rd = _readings()
    data = {"source": rd.source, "fetched_at": rd.fetched_at, "synthetic": rd.synthetic}
    base = {"origin": origin, "dest": dest, "depart": depart.isoformat().replace("+00:00", "Z"),
            "port": port, "ground": ground, "data": data}

    if not legal:
        return {**base, "ok": False, "plans": [], "message": explain_no_route(
            origin, dest, cruise, vessel, depart, max_hours, raw, extra_zones)}

    min_eta = min(r["eta_hours"] for _, r in legal) or 1.0
    max_risk = max(r["risk_exposure"] for _, r in legal) or 1.0
    legal.sort(key=lambda x: (1 - pref) * x[1]["eta_hours"] / min_eta + pref * x[1]["risk_exposure"] / max_risk)
    effort = round(effort_at(*dest), 3)
    plans = []
    for rp, r in legal:
        p = {k: v for k, v in r.items() if k not in ("ok", "reason", "cells")}
        p["name"] = PLAN_NAMES[rp]
        p["risk_pref"] = rp if rp >= 0 else 0.5
        p["effort_proxy"] = effort
        p["round_trip_hours"] = round(2 * r["eta_hours"], 2)
        p["weather_window"] = {
            "from": base["depart"],
            "to": (depart + timedelta(hours=2 * r["eta_hours"])).isoformat().replace("+00:00", "Z"),
            "max_wave_m": r["max_wave_m"],
            "max_wind_kn": r["max_wind_kn"],
        }
        plans.append(p)
    return {**base, "ok": True, "plans": plans, "message": None}


def explain_no_route(origin: LonLat, dest: LonLat, cruise: float, vessel: str, depart: datetime,
                     max_hours: float, raw: list, extra_zones: Sequence[Any] | None) -> str:
    """Name the binding constraint and what to relax (Req 5.4)."""
    if raw:
        need = round(2 * min(r["eta_hours"] for _, r in raw), 1)
        return f"No legal route within {max_hours:g} h. Relax: max_hours (the shortest legal round trip needs about {need:g} h)."
    if route_one(origin, dest, cruise, vessel, depart, 0.1, extra_zones, ignore_wave_limit=True)["ok"]:
        limit = vessels_config()[vessel]["hard_wave_limit_m"]
        return f"No legal route: waves exceed the {limit:g} m limit for this vessel on every path. Relax: departure time or vessel."
    if route_one(origin, dest, cruise, vessel, depart, 0.1, extra_zones, ignore_prohibited=True)["ok"]:
        return "No legal route: active closed zones block every path. Relax: departure time (after the closure ends) or target ground."
    return "No legal route: the destination is not reachable by water. Relax: target ground."
