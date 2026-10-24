"""Unit tests for conditions ingest + cache flag (Task 1.3, Req 1.3)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.ingest.conditions import (
    ConditionsResult,
    filter_by_time,
    get_conditions,
    load_cached_conditions,
)
from app.ingest.grid import build_grid_spec, land_mask_array


def test_cached_conditions_load_and_flag():
    """Snapshot loads, is flagged cached, and exposes a timestamped badge."""
    res = load_cached_conditions()
    assert isinstance(res, ConditionsResult)
    assert res.conditions, "expected some conditions"
    assert res.cached is True
    assert res.fetched_at is not None
    # The current conditions snapshot is hand-authored (synthetic: true), so the
    # badge reflects synthetic honestly; it carries a timestamp either way.
    assert res.badge.startswith(("cached ", "synthetic "))


def test_req1_3_demo_mode_uses_cache(monkeypatch):
    """Req 1.3: in demo mode conditions come from the cache (no live call)."""
    monkeypatch.setenv("FATHOM_DEMO_MODE", "true")
    res = get_conditions()
    assert res.cached is True
    assert res.error is None


def test_req1_3_live_failure_falls_back_to_cache(monkeypatch):
    """When a live fetch fails, we fall back to cache and note the error."""
    monkeypatch.setenv("FATHOM_DEMO_MODE", "false")

    import app.ingest.conditions as mod

    def boom(timeout_s):
        raise RuntimeError("network down")

    monkeypatch.setattr(mod, "_fetch_live_conditions", boom)
    res = get_conditions(prefer_live=True)
    assert res.cached is True
    assert res.error is not None and "network down" in res.error


def test_conditions_cells_are_water_cells():
    """Every conditions cell_id maps to a valid, non-land grid cell."""
    spec = build_grid_spec()
    arr = land_mask_array(spec)
    for c in load_cached_conditions().conditions:
        ix, iy = (int(p) for p in c.cell_id.split("_"))
        assert 0 <= ix < spec.nx and 0 <= iy < spec.ny
        assert not arr[iy, ix], f"conditions cell {c.cell_id} is on land"


def test_filter_by_time():
    """Filtering returns only the conditions at the requested slice.

    Derive the slice from the data rather than hardcoding a date, so the test
    holds whether the snapshot is a live download or a hand-authored demo set.
    """
    res = load_cached_conditions()
    assert res.conditions, "expected some conditions in the snapshot"
    first = res.conditions[0]
    slice_t = first.time if first.time.tzinfo else first.time.replace(tzinfo=timezone.utc)
    got = filter_by_time(res.conditions, slice_t)
    assert got, "expected at least one record at the first record's time"
    assert all(
        (c.time if c.time.tzinfo else c.time.replace(tzinfo=timezone.utc)) == slice_t
        for c in got
    )
