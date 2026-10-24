"""Unit tests for the grid generator and land mask (Task 1.1, Req 5.1)."""

from __future__ import annotations

from app.ingest.grid import build_grid_spec, generate_cells, land_mask_array
from app.ingest.landmask import get_land_mask


def test_grid_covers_study_area_bbox():
    """The grid spans the configured bbox with 0.05-degree cells."""
    spec = build_grid_spec()
    # Study area: 71W-69W, 41N-43.5N at 0.05 deg => 40 x 50 cells.
    assert spec.nx == 40
    assert spec.ny == 50
    assert spec.cell_deg == 0.05


def test_cell_ids_unique_and_centroids_in_bbox():
    """Every cell has a unique id and a centroid inside the bbox."""
    spec = build_grid_spec()
    cells = generate_cells(spec)
    assert len(cells) == spec.nx * spec.ny
    assert len({c.id for c in cells}) == len(cells)
    for c in cells:
        assert spec.min_lon <= c.lon <= spec.max_lon
        assert spec.min_lat <= c.lat <= spec.max_lat


def test_known_land_points_are_land():
    """Points on the mainland / Cape Cod resolve to land."""
    mask = get_land_mask()
    # Well inside the western mainland.
    assert mask.is_land(-70.95, 42.8)
    # On the Cape Cod peninsula.
    assert mask.is_land(-70.3, 41.78)


def test_known_water_points_are_not_land():
    """Open-water points in the bays resolve to water."""
    mask = get_land_mask()
    # Middle of Massachusetts Bay.
    assert not mask.is_land(-70.3, 42.35)
    # Middle of Cape Cod Bay.
    assert not mask.is_land(-70.3, 41.95)
    # Offshore east of the Cape.
    assert not mask.is_land(-69.5, 42.0)


def test_land_mask_array_shape_and_has_both_classes():
    """The mask array matches the grid and contains both land and water."""
    spec = build_grid_spec()
    arr = land_mask_array(spec)
    assert arr.shape == (spec.ny, spec.nx)
    assert arr.any(), "expected some land cells"
    assert (~arr).any(), "expected some water cells"


def test_generate_cells_land_flags_match_mask():
    """Cell.is_land agrees with the land mask array."""
    spec = build_grid_spec()
    arr = land_mask_array(spec)
    for c in generate_cells(spec):
        ix, iy = (int(p) for p in c.id.split("_"))
        assert c.is_land == bool(arr[iy, ix])
