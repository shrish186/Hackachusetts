"""Lane B task 5: router properties and examples (Req 5, design.md §6)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine import routing
from app.engine.routing import plan_routes, route_one
from app.ingest.grid import default_grid, land_mask_array
from app.ingest.zones import default_zones, is_active, zones_containing

GRID = default_grid()
LAND = land_mask_array(GRID)
WHEN = datetime(2026, 3, 15, 9, tzinfo=timezone.utc)

_LON = st.floats(min_value=-70.95, max_value=-69.05, allow_nan=False)
_LAT = st.floats(min_value=41.05, max_value=43.45, allow_nan=False)
_TIME = st.integers(min_value=0, max_value=24 * 200).map(lambda h: datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=h))


def _cells(r: dict) -> list[tuple[int, int]]:
    return [tuple(int(p) for p in c.split("_")) for c in r["cells"]]


def _trip(**kw) -> dict:
    base = {"port": "provincetown", "vessel": "mid_trawler", "cruise_kn": 9.5, "max_hours": 24,
            "depart_window": [WHEN.isoformat(), WHEN.isoformat()], "target_ground": "stellwagen_bank",
            "risk_pref": 0.5, "language": "en"}
    return {**base, **kw}


@settings(max_examples=60, deadline=None)
@given(o=st.tuples(_LON, _LAT), d=st.tuples(_LON, _LAT), when=_TIME,
       pref=st.floats(0, 1), vessel=st.sampled_from(["small_boat", "mid_trawler", "scalloper"]))
def test_req5_route_never_crosses_land(o, d, when, pref, vessel) -> None:
    r = route_one(o, d, 9.0, vessel, when, pref)
    for ix, iy in _cells(r):
        assert not LAND[iy, ix]
    # Consecutive cells are 8-neighbors and diagonals never cut a land corner.
    for (ax, ay), (bx, by) in zip(_cells(r), _cells(r)[1:]):
        assert max(abs(bx - ax), abs(by - ay)) == 1
        if ax != bx and ay != by:
            assert not LAND[ay, bx] and not LAND[by, ax]


@settings(max_examples=60, deadline=None)
@given(o=st.tuples(_LON, _LAT), d=st.tuples(_LON, _LAT), when=_TIME, pref=st.floats(0, 1))
def test_req5_route_never_enters_active_prohibited_zone(o, d, when, pref) -> None:
    r = route_one(o, d, 9.0, "mid_trawler", when, pref)
    for ix, iy in _cells(r):
        lon, lat = GRID.center(ix, iy)
        for z in zones_containing(list(default_zones()), lon, lat):
            assert not (z.prohibited and is_active(z, when)), z.id


def test_req5_extra_prohibited_zone_is_avoided() -> None:
    base = route_one((-70.18, 42.05), (-70.25, 42.35), 9.5, "mid_trawler", WHEN, 0.1)
    lons = [GRID.center(*c)[0] for c in _cells(base)]
    lats = [GRID.center(*c)[1] for c in _cells(base)]
    mid_lon, mid_lat = lons[len(lons) // 2], lats[len(lats) // 2]
    box = {"id": "cand", "name": "Candidate", "kind": "fishing_closure", "prohibited": True,
           "geometry": {"type": "Polygon", "coordinates": [[[mid_lon - 0.06, mid_lat - 0.06], [mid_lon + 0.06, mid_lat - 0.06],
                                                           [mid_lon + 0.06, mid_lat + 0.06], [mid_lon - 0.06, mid_lat + 0.06],
                                                           [mid_lon - 0.06, mid_lat - 0.06]]]}}
    r = route_one((-70.18, 42.05), (-70.25, 42.35), 9.5, "mid_trawler", WHEN, 0.1, extra_zones=[box])
    assert r["ok"] and "cand" not in r["zones_crossed"]
    assert r["eta_hours"] >= base["eta_hours"]


def test_req5_2_slow_zone_caps_speed_and_adds_time() -> None:
    o, d = (-70.18, 42.05), (-70.25, 42.35)
    capped = route_one(o, d, 14.0, "mid_trawler", WHEN, 0.1)
    off_season = route_one(o, d, 14.0, "mid_trawler", datetime(2026, 8, 1, 9, tzinfo=timezone.utc), 0.1)
    assert "sma_cape_cod_bay" in capped["zones_crossed"]
    assert capped["slow_zone_hours"] > 0
    assert capped["eta_hours"] > off_season["eta_hours"]


def test_req5_4_no_legal_route_names_constraint() -> None:
    out = plan_routes(_trip(max_hours=0.5, target_ground="jeffreys_ledge"))
    assert out["ok"] is False and out["plans"] == []
    assert "Relax: max_hours" in out["message"]


def test_req5_wave_hard_limit_blocks(monkeypatch) -> None:
    import numpy as np

    rough = np.full(LAND.shape, 9.0)
    monkeypatch.setattr(routing, "_wx_grids", lambda: (rough, rough))
    monkeypatch.setattr(routing, "_ROUTE_CACHE", {})
    out = plan_routes(_trip(vessel="small_boat"))
    assert out["ok"] is False and "waves exceed" in out["message"]


def test_req5_3_alternates_are_distinct_and_fast() -> None:
    t0 = time.time()
    out = plan_routes(_trip(port="gloucester", target_ground="cape_cod_bay"))
    assert time.time() - t0 < 3.0
    assert 2 <= len(out["plans"]) <= 3
    tracks = {tuple(map(tuple, p["waypoints"])) for p in out["plans"]}
    assert len(tracks) == len(out["plans"])
    for p in out["plans"]:
        assert 2 * p["eta_hours"] <= 24 and p["fuel_est_l"] > 0 and 0 <= p["effort_proxy"] <= 1
