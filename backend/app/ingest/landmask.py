"""Land mask for the study area (Lane A).

Loads simplified land polygons from a bundled GeoJSON and answers "is this
point on land?". Backed by shapely so it works offline in demo mode.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.prepared import prep
from shapely.prepared import PreparedGeometry

from app.ingest.config import data_path, study_area_config


def _load_land_geojson(path: Path) -> list[dict]:
    """Return the list of GeoJSON geometries from a FeatureCollection file."""
    with path.open("r", encoding="utf-8") as fh:
        gj = json.load(fh)
    if gj.get("type") == "FeatureCollection":
        return [f["geometry"] for f in gj.get("features", []) if f.get("geometry")]
    if gj.get("type") == "Feature":
        return [gj["geometry"]]
    # Bare geometry.
    return [gj]


class LandMask:
    """Point-in-land test over the bundled land polygons.

    Uses a prepared union of all land polygons for fast repeated queries.
    """

    def __init__(self, geometries: list[dict]) -> None:
        polys = [shape(g) for g in geometries]
        self._union = polys[0] if len(polys) == 1 else _union_all(polys)
        self._prepared: PreparedGeometry = prep(self._union)

    def is_land(self, lon: float, lat: float) -> bool:
        """True if (lon, lat) in decimal degrees falls on land.

        A point exactly on the coastline is treated as land (boundary counts).
        """
        pt = Point(lon, lat)
        return self._prepared.covers(pt)


def _union_all(polys: list) -> object:
    """Union a list of shapely polygons (compatible across shapely versions)."""
    try:
        from shapely import union_all  # shapely >= 2.0

        return union_all(polys)
    except Exception:  # pragma: no cover - fallback for older shapely
        from shapely.ops import unary_union

        return unary_union(polys)


@lru_cache(maxsize=1)
def get_land_mask() -> LandMask:
    """Load the land mask defined in ``config/study_area.yaml`` (cached)."""
    cfg = study_area_config()
    rel = cfg.get("land_geojson", "data/snapshots/land_mask.geojson")
    # The config path is relative to the repo root; strip a leading "data/".
    parts = Path(rel).parts
    if parts and parts[0] == "data":
        path = data_path(*parts[1:])
    else:
        path = data_path(*parts)
    return LandMask(_load_land_geojson(path))
