"""Ports, fishing grounds, and snap-to-water helpers (Lane A).

Port coordinates in config/ports.yaml are real harbor locations, but the
bundled land mask is a SIMPLIFIED (synthetic) coastline, so a real harbor can
fall inside a "land" cell at the grid resolution. ``snap_to_water`` moves such
a point to the centroid of the nearest water cell so the router always has a
valid, in-water origin. The original real coordinate is preserved separately.

API (stable for Lane B/D):
    load_ports() -> dict[str, dict]            # raw config ports
    load_grounds() -> dict[str, dict]          # raw config fishing grounds
    snap_to_water(lon, lat, spec=None, mask=None) -> (lon, lat)
    port_water_point(port_key) -> (lon, lat)   # snapped, guaranteed in water
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.ingest.config import config_path, load_yaml
from app.ingest.grid import GridSpec, default_grid, land_mask_array


@lru_cache(maxsize=1)
def _ports_cfg() -> dict:
    return load_yaml(config_path("ports.yaml"))


def load_ports() -> dict[str, dict]:
    """Raw base port definitions from config/ports.yaml (the `ports` key).

    These are the ONLY ports the simulator fleet seeds from; the loader API is
    unchanged. Planner-only harbors live under `planner_ports` (see
    ``load_planner_ports`` / ``load_all_ports``).
    """
    return dict(_ports_cfg().get("ports", {}))


def load_planner_ports() -> dict[str, dict]:
    """Planner-only ports from config/ports.yaml (the `planner_ports` key).

    These extra real Massachusetts harbors populate the trip-planner dropdown
    only. Each is returned with ``planner_only: True``. They are NOT used by the
    fleet/simulator.
    """
    out: dict[str, dict] = {}
    for pid, entry in _ports_cfg().get("planner_ports", {}).items():
        e = dict(entry)
        e["planner_only"] = True
        out[pid] = e
    return out


def load_all_ports() -> dict[str, dict]:
    """All selectable ports for /api/meta/ports and the frontend picker.

    Base ports (``planner_only: False``) plus planner-only ports
    (``planner_only: True``), base first. The fleet/simulator must keep using
    ``load_ports`` (base only); this function is for the UI picker.
    """
    out: dict[str, dict] = {}
    for pid, entry in load_ports().items():
        e = dict(entry)
        e.setdefault("planner_only", False)
        out[pid] = e
    out.update(load_planner_ports())
    return out


def load_grounds() -> dict[str, dict]:
    """Raw fishing-ground definitions from config/ports.yaml."""
    return dict(_ports_cfg().get("fishing_grounds", {}))


@lru_cache(maxsize=1)
def _mask_and_spec() -> tuple[np.ndarray, GridSpec]:
    spec = default_grid()
    return land_mask_array(spec), spec


def is_water(lon: float, lat: float, spec: GridSpec | None = None, mask: np.ndarray | None = None) -> bool:
    """True if (lon, lat) falls in a water cell of the study grid."""
    if mask is None or spec is None:
        mask, spec = _mask_and_spec()
    ix, iy = spec.index_of(lon, lat)
    return not bool(mask[iy, ix])


def snap_to_water(
    lon: float,
    lat: float,
    spec: GridSpec | None = None,
    mask: np.ndarray | None = None,
    max_radius: int = 12,
) -> tuple[float, float]:
    """Return the centroid of the nearest water cell to (lon, lat).

    If the point is already in water, returns its own cell centroid. Otherwise
    searches outward in rings up to ``max_radius`` cells and returns the closest
    water-cell centroid (great-circle-ish nearest by cell distance). Raises if no
    water cell is found within the radius.
    """
    if mask is None or spec is None:
        mask, spec = _mask_and_spec()
    ix0, iy0 = spec.index_of(lon, lat)
    if not mask[iy0, ix0]:
        return spec.center(ix0, iy0)
    best: tuple[float, tuple[int, int]] | None = None
    for r in range(1, max_radius + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:  # only the current ring
                    continue
                ix, iy = ix0 + dx, iy0 + dy
                if not (0 <= ix < spec.nx and 0 <= iy < spec.ny):
                    continue
                if mask[iy, ix]:
                    continue
                d2 = dx * dx + dy * dy
                if best is None or d2 < best[0]:
                    best = (d2, (ix, iy))
        if best is not None:
            ix, iy = best[1]
            return spec.center(ix, iy)
    raise ValueError(f"no water cell within {max_radius} cells of ({lon}, {lat})")


def port_water_point(port_key: str) -> tuple[float, float]:
    """(lon, lat) of a port, snapped to the nearest water cell centroid."""
    ports = load_ports()
    if port_key not in ports:
        raise KeyError(f"unknown port: {port_key}")
    p = ports[port_key]
    return snap_to_water(float(p["lon"]), float(p["lat"]))


def all_ports_water_points() -> dict[str, tuple[float, float]]:
    """Every configured port, snapped to water (origin for the router/fleet)."""
    return {k: port_water_point(k) for k in load_ports()}
