"""Study-area grid generator and land mask application (Lane A).

Builds the regular lon/lat grid of ``Cell`` objects for the study area and
flags which cells are land. The grid is the common substrate the risk model
and the router both index into.

Design.md section 4: cells are identified as "ix_iy" where ix/iy are integer
grid indices increasing east and north from the bbox origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app.ingest.config import study_area_config
from app.ingest.landmask import get_land_mask
from app.models.geo import Cell


@dataclass(frozen=True)
class GridSpec:
    """Immutable description of the grid geometry.

    Units: degrees. ``nx``/``ny`` are the number of cell centroids east and
    north. Centroids sit half a cell in from the bbox origin.
    """

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    cell_deg: float
    nx: int
    ny: int

    def cell_id(self, ix: int, iy: int) -> str:
        """Return the "ix_iy" id for integer grid indices."""
        return f"{ix}_{iy}"

    def center(self, ix: int, iy: int) -> tuple[float, float]:
        """Return the (lon, lat) centroid of cell (ix, iy) in degrees."""
        lon = self.min_lon + (ix + 0.5) * self.cell_deg
        lat = self.min_lat + (iy + 0.5) * self.cell_deg
        return lon, lat

    def index_of(self, lon: float, lat: float) -> tuple[int, int]:
        """Return the (ix, iy) grid indices containing (lon, lat).

        Indices are clamped to the valid range so points on the max edge map to
        the last cell rather than overflowing.
        """
        ix = int((lon - self.min_lon) / self.cell_deg)
        iy = int((lat - self.min_lat) / self.cell_deg)
        ix = min(max(ix, 0), self.nx - 1)
        iy = min(max(iy, 0), self.ny - 1)
        return ix, iy


def build_grid_spec(
    bbox: tuple[float, float, float, float] | None = None,
    cell_deg: float | None = None,
) -> GridSpec:
    """Build a :class:`GridSpec` from the config (or explicit overrides).

    ``bbox`` is (min_lon, min_lat, max_lon, max_lat) in degrees.
    """
    cfg = study_area_config()
    if bbox is None:
        b = cfg["bbox"]
        bbox = (b["min_lon"], b["min_lat"], b["max_lon"], b["max_lat"])
    if cell_deg is None:
        cell_deg = float(cfg["cell_deg"])

    min_lon, min_lat, max_lon, max_lat = bbox
    if max_lon <= min_lon or max_lat <= min_lat:
        raise ValueError("bbox max must be greater than min")
    if cell_deg <= 0:
        raise ValueError("cell_deg must be positive")

    nx = int(round((max_lon - min_lon) / cell_deg))
    ny = int(round((max_lat - min_lat) / cell_deg))
    return GridSpec(min_lon, min_lat, max_lon, max_lat, cell_deg, nx, ny)


def land_mask_array(spec: GridSpec) -> np.ndarray:
    """Return a boolean array of shape (ny, nx); True where the cell is land.

    Indexed as ``mask[iy, ix]`` to match the natural "row = latitude" layout
    used by the risk grid.
    """
    mask = get_land_mask()
    arr = np.zeros((spec.ny, spec.nx), dtype=bool)
    for iy in range(spec.ny):
        for ix in range(spec.nx):
            lon, lat = spec.center(ix, iy)
            arr[iy, ix] = mask.is_land(lon, lat)
    return arr


def generate_cells(spec: GridSpec | None = None) -> list[Cell]:
    """Generate all :class:`Cell` objects for the grid, with land flags set."""
    if spec is None:
        spec = build_grid_spec()
    mask = land_mask_array(spec)
    cells: list[Cell] = []
    for iy in range(spec.ny):
        for ix in range(spec.nx):
            lon, lat = spec.center(ix, iy)
            cells.append(
                Cell(id=spec.cell_id(ix, iy), lon=lon, lat=lat, is_land=bool(mask[iy, ix]))
            )
    return cells


@lru_cache(maxsize=1)
def default_grid() -> GridSpec:
    """The grid spec built from config (cached for reuse by the engine)."""
    return build_grid_spec()
