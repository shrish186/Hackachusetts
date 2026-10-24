"""Property-based tests for the whale risk model (Task 1.4.1, Req 3).

Invariants required by the testing-pbt steering file (one test each, name
starts with the requirement number):
  * req3 risk(cell, t, speed) is always within [0, 1]
  * req3 risk is monotonic non-decreasing in speed
  * req3 risk is 0 for land cells
  * req3 adding a sighting never lowers risk in any cell

When a property fails, keep the minimized counterexample as a regression
example and note it in docs/kiro-evidence/LOG.md. Never edit a test to make it
pass -- fix the code or ask.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.risk import load_risk_params, risk_at
from app.models.geo import Sighting

# Study-area ranges (design.md section 4).
_LON = st.floats(min_value=-71.0, max_value=-69.0, allow_nan=False, allow_infinity=False)
_LAT = st.floats(min_value=41.0, max_value=43.5, allow_nan=False, allow_infinity=False)
_SPEED = st.floats(min_value=0.0, max_value=40.0, allow_nan=False, allow_infinity=False)

_T0 = datetime(2026, 3, 14, 18, 0, tzinfo=timezone.utc)


def _sighting(lon: float, lat: float, age_days: float, count: int) -> Sighting:
    return Sighting(
        lon=lon,
        lat=lat,
        observed_at=_T0 - timedelta(days=age_days),
        count=count,
        source="hypothesis",
    )


# A strategy for a list of 0..6 sightings inside the study area.
_sightings = st.lists(
    st.builds(
        _sighting,
        lon=_LON,
        lat=_LAT,
        age_days=st.floats(min_value=0.0, max_value=60.0, allow_nan=False),
        count=st.integers(min_value=0, max_value=10),
    ),
    min_size=0,
    max_size=6,
)


@settings(max_examples=250, deadline=None)
@given(lon=_LON, lat=_LAT, speed=_SPEED, sightings=_sightings)
def test_req3_risk_bounded_0_1(lon, lat, speed, sightings):
    """risk is always within [0, 1]."""
    r = risk_at(lon, lat, _T0, speed, sightings, is_land=False)
    assert 0.0 <= r <= 1.0


@settings(max_examples=250, deadline=None)
@given(
    lon=_LON,
    lat=_LAT,
    v_lo=_SPEED,
    delta=st.floats(min_value=0.0, max_value=20.0, allow_nan=False),
    sightings=_sightings,
)
def test_req3_risk_monotonic_in_speed(lon, lat, v_lo, delta, sightings):
    """risk is monotonic non-decreasing in speed (all else fixed)."""
    r_lo = risk_at(lon, lat, _T0, v_lo, sightings, is_land=False)
    r_hi = risk_at(lon, lat, _T0, v_lo + delta, sightings, is_land=False)
    # Allow a tiny epsilon for floating point noise.
    assert r_hi >= r_lo - 1e-12


@settings(max_examples=200, deadline=None)
@given(lon=_LON, lat=_LAT, speed=_SPEED, sightings=_sightings)
def test_req3_risk_zero_on_land(lon, lat, speed, sightings):
    """risk is exactly 0 for land cells, regardless of other inputs."""
    assert risk_at(lon, lat, _T0, speed, sightings, is_land=True) == 0.0


@settings(max_examples=250, deadline=None)
@given(
    lon=_LON,
    lat=_LAT,
    speed=_SPEED,
    sightings=_sightings,
    new_lon=_LON,
    new_lat=_LAT,
    new_age=st.floats(min_value=0.0, max_value=60.0, allow_nan=False),
    new_count=st.integers(min_value=0, max_value=10),
)
def test_req3_adding_sighting_never_lowers_risk(
    lon, lat, speed, sightings, new_lon, new_lat, new_age, new_count
):
    """Adding a sighting never lowers risk in any cell."""
    before = risk_at(lon, lat, _T0, speed, sightings, is_land=False)
    augmented = list(sightings) + [_sighting(new_lon, new_lat, new_age, new_count)]
    after = risk_at(lon, lat, _T0, speed, augmented, is_land=False)
    assert after >= before - 1e-12


def test_req3_lethality_50pct_at_v50():
    """Sanity example: lethality is ~0.5 at the configured v50 (regression)."""
    from app.engine.risk import lethality

    p = load_risk_params()
    assert abs(lethality(p.v50_kn, p) - 0.5) < 1e-9
