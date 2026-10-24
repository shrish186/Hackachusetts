"""Sanity tests for the shared Hypothesis strategies.

These assert the single invariant every strategy must satisfy: the objects it
builds are *always valid* instances of the corresponding pydantic model. If a
strategy ever generated an invalid object, pydantic would raise during
construction inside the strategy and Hypothesis would surface it here.

We re-run model validation explicitly (``model_validate(model_dump())``) so the
check does not rely solely on construction-time validation.
"""

from __future__ import annotations

from hypothesis import given

from app.models import Cell, Sighting, TripRequest, Zone
from tests import strategies as strat


@given(strat.cells())
def test_cell_strategy_produces_valid_cells(cell: Cell) -> None:
    """Every generated Cell round-trips through validation and stays in range."""
    assert isinstance(cell, Cell)
    Cell.model_validate(cell.model_dump())
    assert -180.0 <= cell.lon <= 180.0
    assert -90.0 <= cell.lat <= 90.0
    assert "_" in cell.id


@given(strat.sightings())
def test_sighting_strategy_produces_valid_sightings(sighting: Sighting) -> None:
    """Every generated Sighting is valid and has a non-negative count."""
    assert isinstance(sighting, Sighting)
    Sighting.model_validate(sighting.model_dump())
    assert sighting.count >= 0


@given(strat.zones())
def test_zone_strategy_produces_valid_zones(zone: Zone) -> None:
    """Every generated Zone is valid and honors both model validators."""
    assert isinstance(zone, Zone)
    Zone.model_validate(zone.model_dump())
    # active_to is never earlier than active_from when both are present.
    if zone.active_from is not None and zone.active_to is not None:
        assert zone.active_to >= zone.active_from
    # A zone with no source_url must be flagged synthetic (data-and-safety).
    if not zone.source_url:
        assert zone.synthetic is True


@given(strat.trip_requests())
def test_trip_request_strategy_produces_valid_requests(req: TripRequest) -> None:
    """Every generated TripRequest is valid with an ordered departure window."""
    assert isinstance(req, TripRequest)
    TripRequest.model_validate(req.model_dump())
    start, end = req.depart_window
    assert end >= start
    assert req.cruise_kn > 0.0
    assert req.max_hours > 0.0
    assert 0.0 <= req.risk_pref <= 1.0


@given(strat.cells(is_land=True))
def test_cells_can_be_forced_to_land(cell: Cell) -> None:
    """The is_land override lets land-cell invariants be tested directly."""
    assert cell.is_land is True


@given(strat.cells(is_land=False))
def test_cells_can_be_forced_to_water(cell: Cell) -> None:
    """The is_land override can also pin cells to water."""
    assert cell.is_land is False
