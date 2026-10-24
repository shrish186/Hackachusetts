"""Example-based tests for the risk model and grid (Task 1.4, Req 3)."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from app.engine.risk import (
    load_risk_params,
    load_sightings,
    p_whale,
    risk_breakdown,
    risk_grid,
)
from app.ingest.grid import build_grid_spec, land_mask_array

_T = datetime(2026, 3, 14, 18, 0, tzinfo=timezone.utc)


def test_params_load_from_config():
    """Risk parameters load from config/risk.yaml."""
    p = load_risk_params()
    assert 0.0 <= p.alpha <= 1.0
    assert p.v50_kn > 0 and p.k > 0


def test_sightings_snapshot_loads():
    """The bundled sightings snapshot validates (real OBIS data, variable count)."""
    s = load_sightings()
    assert len(s) > 0
    assert all(x.count >= 0 for x in s)


def test_higher_near_cluster_than_far():
    """p_whale is higher near a sighting cluster than far offshore."""
    s = load_sightings()
    near = p_whale(-70.33, 42.22, _T, s)
    far = p_whale(-69.9, 43.3, _T, s)
    assert near > far


def test_req3_4_breakdown_factors_present():
    """Req 3.4: a cell breakdown exposes the contributing factors."""
    s = load_sightings()
    b = risk_breakdown("c", -70.33, 42.22, _T, 15.0, s)
    names = {name for name, _ in b.top_factors()}
    assert names == {"seasonal_presence", "recent_sightings", "speed_lethality"}
    assert 0.0 <= b.risk <= 1.0


def test_risk_grid_land_cells_zero_and_bounded():
    """Grid risk is 0 on land and within [0, 1] everywhere."""
    spec = build_grid_spec()
    mask = land_mask_array(spec)
    s = load_sightings()
    grid = risk_grid(spec, _T, 15.0, s, mask)
    assert grid.shape == (spec.ny, spec.nx)
    assert np.all(grid >= 0.0) and np.all(grid <= 1.0)
    # All land cells must be exactly 0.
    assert np.all(grid[mask] == 0.0)
    # Some water cell near the cluster should carry non-trivial risk.
    assert grid.max() > 0.3
