"""Property + example tests for effort proxy and synthetic fleet (task 9)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.effort import effort_access, effort_at
from app.engine.fleet import _VESSEL_TYPES, build_fleet

# Study-area ranges (design.md section 4).
_LON = st.floats(min_value=-71.0, max_value=-69.0, allow_nan=False, allow_infinity=False)
_LAT = st.floats(min_value=41.0, max_value=43.5, allow_nan=False, allow_infinity=False)


@settings(max_examples=300, deadline=None)
@given(lon=_LON, lat=_LAT)
def test_effort_at_in_unit_interval(lon, lat):
    """effort_at is always within [0, 1]."""
    assert 0.0 <= effort_at(lon, lat) <= 1.0


@settings(max_examples=100, deadline=None)
@given(
    route=st.lists(st.tuples(_LON, _LAT), min_size=0, max_size=10),
)
def test_effort_access_in_unit_interval(route):
    """effort_access is always within [0, 1] (0 for an empty route)."""
    val = effort_access(route)
    assert 0.0 <= val <= 1.0
    if not route:
        assert val == 0.0


def test_effort_higher_on_a_ground_than_far_corner():
    """Effort peaks near a known ground and is lower in an empty corner."""
    # Stellwagen Bank center vs. a far SE corner of the bbox.
    on_ground = effort_at(-70.25, 42.35)
    far = effort_at(-69.05, 41.05)
    assert on_ground > far


def test_fleet_deterministic():
    """build_fleet is deterministic for a fixed (n, seed)."""
    a = [t.to_dict() for t in build_fleet(n=80, seed=42)]
    b = [t.to_dict() for t in build_fleet(n=80, seed=42)]
    assert a == b
    # A different seed should (almost surely) differ.
    c = [t.to_dict() for t in build_fleet(n=80, seed=7)]
    assert c != a


def test_fleet_size_and_valid_fields():
    """Fleet has n anonymous trips with valid ports, grounds, and vessels."""
    trips = build_fleet(n=80, seed=42)
    assert len(trips) == 80
    ids = [t.id for t in trips]
    assert ids == [f"V-{i + 1:03d}" for i in range(80)]  # anonymous, ordered
    assert len(set(ids)) == 80
    for t in trips:
        assert t.vessel in _VESSEL_TYPES
        assert t.cruise_kn > 0
        # Coordinates inside the study area.
        assert -71.0 <= t.origin_lon <= -69.0 and 41.0 <= t.origin_lat <= 43.5
        assert -71.0 <= t.target_lon <= -69.0 and 41.0 <= t.target_lat <= 43.5
        # Never a real vessel name -- anonymous id only.
        assert t.id.startswith("V-")


def test_fleet_zero_is_empty():
    """n=0 yields an empty fleet."""
    assert build_fleet(n=0) == []
