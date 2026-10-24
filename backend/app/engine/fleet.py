"""Deterministic synthetic fleet builder (Lane A, task 6).

Builds a representative fleet of anonymous fishing trips for the what-if
simulator. No real AIS was ingested, so this is SYNTHETIC and seeded from the
real port and fishing-ground locations in config/ports.yaml.

Fully deterministic for a given (n, seed): same output every run. Vessel
identities are anonymous (V-001, V-002, ...) -- never a real vessel name
(data-and-safety steering).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from functools import lru_cache

from app.ingest.config import config_path, load_yaml

# This fleet is synthetic until real vessel tracks are ingested.
SYNTHETIC = True

_VESSEL_TYPES = ("small_boat", "mid_trawler", "scalloper")


@dataclass(frozen=True)
class Trip:
    """One anonymous fleet trip."""

    id: str                 # anonymous id, e.g. "V-001"
    port: str               # origin port key (config/ports.yaml)
    origin_lon: float
    origin_lat: float
    target_ground: str      # fishing-ground key (config/ports.yaml)
    target_lon: float
    target_lat: float
    vessel: str             # one of _VESSEL_TYPES
    cruise_kn: float        # from config/vessels.yaml

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def _ports() -> dict[str, dict]:
    return load_yaml(config_path("ports.yaml")).get("ports", {})


@lru_cache(maxsize=1)
def _grounds() -> dict[str, dict]:
    return load_yaml(config_path("ports.yaml")).get("fishing_grounds", {})


@lru_cache(maxsize=1)
def _vessels() -> dict[str, dict]:
    return load_yaml(config_path("vessels.yaml")).get("vessels", {})


def build_fleet(n: int = 80, seed: int = 42) -> list[Trip]:
    """Return ``n`` deterministic, anonymous synthetic trips.

    Each trip: an origin port, a target fishing ground, a vessel class and its
    cruise speed. Deterministic given (n, seed). synthetic: true.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    rng = random.Random(seed)
    ports = _ports()
    grounds = _grounds()
    vessels = _vessels()
    if not ports or not grounds or not vessels:
        raise RuntimeError("ports.yaml / vessels.yaml must define ports, grounds, vessels")

    port_keys = sorted(ports)        # sorted for determinism
    ground_keys = sorted(grounds)
    vtypes = [v for v in _VESSEL_TYPES if v in vessels]

    trips: list[Trip] = []
    for i in range(n):
        pk = rng.choice(port_keys)
        gk = rng.choice(ground_keys)
        vt = rng.choice(vtypes)
        p = ports[pk]
        g = grounds[gk]
        trips.append(
            Trip(
                id=f"V-{i + 1:03d}",
                port=pk,
                origin_lon=float(p["lon"]),
                origin_lat=float(p["lat"]),
                target_ground=gk,
                target_lon=float(g["lon"]),
                target_lat=float(g["lat"]),
                vessel=vt,
                cruise_kn=float(vessels[vt]["cruise_kn"]),
            )
        )
    return trips
