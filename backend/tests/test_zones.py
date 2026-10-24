"""Unit tests for zone ingest and normalization (Task 1.2, Req 2)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.ingest.zones import (
    active_zones,
    is_active,
    load_zones,
    restriction_summary,
    zones_containing,
)


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def test_all_zones_load_and_validate():
    """Every bundled zone loads into a valid Zone object."""
    zones = load_zones()
    assert len(zones) >= 5
    ids = {z.id for z in zones}
    assert "sma_cape_cod_bay" in ids
    assert "closure_western_gom" in ids


def test_req2_every_zone_has_source_or_is_synthetic():
    """Req 2.4: zones carry a source, or are flagged synthetic."""
    for z in load_zones():
        assert z.source_url is not None or z.synthetic is True


def test_active_filtering_by_time():
    """A zone is active only inside its [active_from, active_to] window."""
    zones = load_zones()
    # Mid-March: SMA (Jan-May) and the March slow zone are active.
    mar = _utc(2026, 3, 15)
    active_ids = {z.id for z in active_zones(zones, mar)}
    assert "sma_cape_cod_bay" in active_ids
    assert "slow_zone_stellwagen_mar" in active_ids
    # July: the March slow zone is inactive.
    jul = _utc(2026, 7, 1)
    assert "slow_zone_stellwagen_mar" not in {z.id for z in active_zones(zones, jul)}


def test_unbounded_zone_always_active():
    """A zone with no active window (wind lease) is always active."""
    lease = next(z for z in load_zones() if z.id == "wind_lease_vineyard")
    assert is_active(lease, _utc(2024, 1, 1))
    assert is_active(lease, _utc(2030, 12, 31))


def test_point_in_zone():
    """A point inside the Cape Cod Bay SMA polygon is detected."""
    zones = load_zones()
    hits = {z.id for z in zones_containing(zones, -70.3, 41.9)}
    assert "sma_cape_cod_bay" in hits
    # A point far north-east should not be in the SMA.
    assert "sma_cape_cod_bay" not in {z.id for z in zones_containing(zones, -69.4, 43.2)}


def test_restriction_summary_prohibited_vs_speed():
    """Summaries reflect prohibition vs speed limit without legal claims."""
    zones = {z.id: z for z in load_zones()}
    assert "No entry" in restriction_summary(zones["closure_western_gom"])
    assert "Speed limit" in restriction_summary(zones["sma_cape_cod_bay"])
    # Advisory assistant must never assert legal compliance.
    for z in zones.values():
        assert "legal" not in restriction_summary(z).lower()
