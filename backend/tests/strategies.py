"""Shared Hypothesis strategies for Fathom's core domain models.

These generate *random but always valid* instances of the pydantic models in
``backend/app/models`` (Anant's models): :class:`Cell`, :class:`Sighting`,
:class:`Zone`, and :class:`TripRequest`. Use them to drive the property-based
tests called for in design.md section 12 and tech.md (every invariant gets a
Hypothesis test).

Design notes
------------
- Coordinates are drawn from the Fathom study area (roughly 41°N–43.5°N,
  71°W–69°W; design.md section 4) so generated objects are realistic, while the
  underlying models still accept the full WGS84 range.
- All datetimes are timezone-aware **UTC** (tech.md: all times UTC internally).
- Strategies respect every model validator, so ``build_*()`` output never raises
  ``ValidationError`` (the accompanying test file asserts exactly this).

Each strategy is exposed as a module-level ``st.SearchStrategy`` and via a small
``*_strategy()`` accessor for readability at call sites.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import get_args

from hypothesis import strategies as st

from app.models import Cell, Sighting, TripRequest, Zone
from app.models.geo import ZoneKind
from app.models.trip import Language, Vessel

# --- Study-area bounds (design.md section 4) ----------------------------------
STUDY_MIN_LON, STUDY_MAX_LON = -71.0, -69.0
STUDY_MIN_LAT, STUDY_MAX_LAT = 41.0, 43.5

# A bounded, UTC datetime window to keep generated times sane and comparable.
_EPOCH_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
_EPOCH_END = datetime(2027, 1, 1, tzinfo=timezone.utc)


# --- Primitive strategies -----------------------------------------------------

def _lons() -> st.SearchStrategy[float]:
    """Longitudes inside the study area, degrees."""
    return st.floats(
        min_value=STUDY_MIN_LON, max_value=STUDY_MAX_LON,
        allow_nan=False, allow_infinity=False,
    )


def _lats() -> st.SearchStrategy[float]:
    """Latitudes inside the study area, degrees."""
    return st.floats(
        min_value=STUDY_MIN_LAT, max_value=STUDY_MAX_LAT,
        allow_nan=False, allow_infinity=False,
    )


def _utc_datetimes() -> st.SearchStrategy[datetime]:
    """Timezone-aware UTC datetimes within a bounded window."""
    return st.datetimes(
        min_value=_EPOCH_START.replace(tzinfo=None),
        max_value=_EPOCH_END.replace(tzinfo=None),
        timezones=st.just(timezone.utc),
    )


def _grid_ids() -> st.SearchStrategy[str]:
    """Grid ids formatted ``"ix_iy"`` with non-negative integer indices."""
    return st.builds(
        lambda ix, iy: f"{ix}_{iy}",
        st.integers(min_value=0, max_value=999),
        st.integers(min_value=0, max_value=999),
    )


def _polygon_geojson() -> st.SearchStrategy[dict]:
    """A minimal, closed GeoJSON Polygon ring inside the study area.

    Built as an axis-aligned rectangle so the ring is always valid and closed
    (first point repeated last), which is all the models require of ``geometry``.
    """
    return st.builds(
        _rect_polygon,
        _lons(), _lats(),
        st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
    )


def _rect_polygon(lon: float, lat: float, dlon: float, dlat: float) -> dict:
    """Return a closed rectangular GeoJSON Polygon anchored at (lon, lat)."""
    x0, y0 = lon, lat
    x1, y1 = lon + dlon, lat + dlat
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {"type": "Polygon", "coordinates": [ring]}


# --- Model strategies ---------------------------------------------------------

def cells(is_land: bool | None = None) -> st.SearchStrategy[Cell]:
    """Generate valid :class:`Cell` objects.

    Args:
        is_land: Force the land flag, or leave ``None`` to let Hypothesis choose.
            Useful for "land cells are never routed" / "risk is 0 on land" tests.
    """
    land = st.just(is_land) if is_land is not None else st.booleans()
    return st.builds(Cell, id=_grid_ids(), lon=_lons(), lat=_lats(), is_land=land)


def sightings() -> st.SearchStrategy[Sighting]:
    """Generate valid :class:`Sighting` objects (count >= 0, UTC time)."""
    return st.builds(
        Sighting,
        lon=_lons(),
        lat=_lats(),
        observed_at=_utc_datetimes(),
        count=st.integers(min_value=0, max_value=50),
        source=st.sampled_from(["OBIS", "NOAA", "synthetic"]),
    )


@st.composite
def zones(draw: st.DrawFn) -> Zone:
    """Generate valid :class:`Zone` objects.

    Honors the model's two validators:
    - ``active_to`` is never earlier than ``active_from``; and
    - a zone with no ``source_url`` is flagged ``synthetic=True`` (data-and-safety).
    """
    kind = draw(st.sampled_from(list(get_args(ZoneKind))))

    active_from = draw(st.none() | _utc_datetimes())
    if active_from is None:
        active_to = draw(st.none() | _utc_datetimes())
    else:
        # Keep active_to >= active_from by adding a non-negative duration.
        extra_hours = draw(st.integers(min_value=0, max_value=24 * 90))
        active_to = draw(st.none() | st.just(active_from + timedelta(hours=extra_hours)))

    # Either a real source (any synthetic flag) or no source (must be synthetic).
    has_source = draw(st.booleans())
    if has_source:
        source_url = draw(st.just("https://www.fisheries.noaa.gov/example"))
        synthetic = draw(st.booleans())
        source_updated = draw(st.none() | _utc_datetimes())
    else:
        source_url = None
        synthetic = True
        source_updated = None

    return Zone(
        id=draw(st.text(min_size=1, max_size=12).filter(lambda s: s.strip() != "")),
        name=draw(st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != "")),
        kind=kind,
        geometry=draw(_polygon_geojson()),
        active_from=active_from,
        active_to=active_to,
        speed_limit_kn=draw(
            st.none()
            | st.floats(min_value=0.0, max_value=30.0, allow_nan=False, allow_infinity=False)
        ),
        prohibited=draw(st.booleans()),
        source_url=source_url,
        source_updated=source_updated,
        synthetic=synthetic,
    )


@st.composite
def trip_requests(draw: st.DrawFn) -> TripRequest:
    """Generate valid :class:`TripRequest` objects.

    Honors the model's ``depart_window`` validator (end not earlier than start)
    and the field bounds (cruise_kn > 0, max_hours > 0, risk_pref in [0, 1]).
    """
    start = draw(_utc_datetimes())
    window_hours = draw(st.integers(min_value=0, max_value=72))
    end = start + timedelta(hours=window_hours)

    return TripRequest(
        port=draw(st.sampled_from(["Gloucester", "New Bedford", "Provincetown", "Scituate"])),
        vessel=draw(st.sampled_from(list(get_args(Vessel)))),
        cruise_kn=draw(
            st.floats(min_value=0.5, max_value=25.0, allow_nan=False, allow_infinity=False)
        ),
        max_hours=draw(
            st.floats(min_value=0.5, max_value=48.0, allow_nan=False, allow_infinity=False)
        ),
        depart_window=(start, end),
        target_ground=draw(st.none() | st.sampled_from(["Stellwagen", "Jeffreys Ledge"])),
        risk_pref=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        language=draw(st.sampled_from(list(get_args(Language)))),
    )


# --- Convenience accessors (readable aliases) ---------------------------------

def cell_strategy() -> st.SearchStrategy[Cell]:
    """Strategy producing valid :class:`Cell` objects."""
    return cells()


def sighting_strategy() -> st.SearchStrategy[Sighting]:
    """Strategy producing valid :class:`Sighting` objects."""
    return sightings()


def zone_strategy() -> st.SearchStrategy[Zone]:
    """Strategy producing valid :class:`Zone` objects."""
    return zones()


def trip_request_strategy() -> st.SearchStrategy[TripRequest]:
    """Strategy producing valid :class:`TripRequest` objects."""
    return trip_requests()
