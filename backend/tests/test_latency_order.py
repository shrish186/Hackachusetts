"""Lane B: plan latency after warm-up, plan order/names, coordinate grounds, baseline access_lost."""
from __future__ import annotations

import time
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.api import warmup
from app.engine import routing
from app.engine.routing import name_plans, plan_routes, route_one

REPLAY = "2026-03-15T13:00:00Z"
BASE = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12,
        "depart_window": [REPLAY, REPLAY], "target_ground": "stellwagen_bank", "risk_pref": 0.8, "language": "en"}

#: Local budget. The product target is 3 s on Render's free CPU; locally plans
#: take well under 1 s, so 1.5 s leaves headroom for a slower CI runner.
BUDGET_S = 1.5


@pytest.fixture(scope="module")
def warm_client():
    warmup.run_warmup()
    assert warmup.status()["ready"], warmup.status()
    from app.main import app

    return TestClient(app, client=("10.8.0.1", 1))


@pytest.mark.parametrize("trip", [
    {},                                                                    # demo trip, replay date
    {"port": "new_bedford", "vessel": "scalloper", "cruise_kn": 7.3, "target_ground": "cape_cod_bay",
     "risk_pref": 0.33, "max_hours": 20, "depart_window": ["2026-11-09T05:17:00Z"] * 2},   # non-demo date, odd params
    {"port": "boston", "vessel": "mid_trawler", "cruise_kn": 11.2, "depart_window": ["2026-11-10T19:40:00Z"] * 2},
    {"port": "plymouth", "target_ground": "-70.325,42.925"},              # "plan to nearest open water"
])
def test_plan_under_time_budget_after_ready(warm_client, trip) -> None:
    t0 = time.perf_counter()
    r = warm_client.post("/api/trip/plan", json={**BASE, **trip})
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200
    assert "event: done" in r.text
    assert elapsed < BUDGET_S, f"plan took {elapsed:.2f} s"


def test_health_instant_while_warming(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setattr(warmup, "_state", {"started": True, "ready": False, "error": None, "seconds": None, "plans": 0})
    c = TestClient(app, client=("10.8.0.2", 1))
    t0 = time.perf_counter()
    assert c.get("/api/health").status_code == 200
    assert time.perf_counter() - t0 < 0.2
    assert c.get("/api/ready").status_code == 503


def test_whale_surface_matches_scalar_model() -> None:
    from datetime import timedelta

    from app.engine.risk import p_whale

    when = routing._parse_dt(REPLAY)
    b = routing.risk_bucket(when)
    surf = routing.whale_surface(b)
    mid = b + timedelta(minutes=routing.RISK_BUCKET_MIN / 2)
    lons, lats = routing._centers()
    land = routing._land()
    for iy in range(0, land.shape[0], 7):
        for ix in range(0, land.shape[1], 7):
            if not land[iy, ix]:
                assert surf.p_whale[iy, ix] == pytest.approx(p_whale(lons[iy, ix], lats[iy, ix], mid, routing._sightings()), abs=1e-9)


def test_risk_surface_bucketing() -> None:
    a = routing.risk_surface(routing._parse_dt("2026-03-15T13:01:00Z"), 9.0)
    b = routing.risk_surface(routing._parse_dt("2026-03-15T13:29:00Z"), 9.04)
    c = routing.risk_surface(routing._parse_dt("2026-03-15T13:31:00Z"), 9.0)
    assert a is b and a is not c


# --- order and names -----------------------------------------------------------


@pytest.mark.parametrize("port,ground", [("gloucester", "stellwagen_bank"), ("gloucester", "cape_cod_bay"),
                                         ("boston", "cape_cod_bay"), ("plymouth", "stellwagen_bank"),
                                         ("new_bedford", "cape_cod_bay"), ("provincetown", "stellwagen_bank")])
def test_plans_sorted_by_eta_and_names_honest(port: str, ground: str) -> None:
    plans = plan_routes({**BASE, "port": port, "target_ground": ground, "max_hours": 24})["plans"]
    etas = [p["eta_hours"] for p in plans]
    assert etas == sorted(etas)
    assert plans[0]["name"] == "Fastest"
    assert [p["rank"] for p in plans] == list(range(1, len(plans) + 1))
    assert sum(p["recommended"] for p in plans) == 1
    min_risk = min(p["risk_exposure"] for p in plans)
    for p in plans:
        assert "Alternate track" not in p["name"]
        if p["name"] == "Safest":
            assert p["risk_exposure"] == min_risk
    names = [p["name"] for p in plans]
    order = {"Fastest": 0, "Balanced": 1, "Safest": 2}
    ranked = [order[n] for n in names if n in order]
    assert ranked == sorted(ranked)


def test_name_plans_rules() -> None:
    f = {"eta_hours": 1.0, "risk_exposure": 0.5}
    slow_safe = {"eta_hours": 2.0, "risk_exposure": 0.2}
    mid = {"eta_hours": 1.5, "risk_exposure": 0.3}
    worse = {"eta_hours": 1.6, "risk_exposure": 0.6}
    assert name_plans([f, mid, slow_safe], f) == ["Fastest", "Balanced", "Safest"]
    assert name_plans([f, worse], f) == ["Fastest", "Alternative"]
    assert name_plans([f, worse, {"eta_hours": 1.7, "risk_exposure": 0.7}], f) == ["Fastest", "Alternative 1", "Alternative 2"]
    # Never "Safest" without the minimum risk: Fastest has the minimum here.
    assert "Safest" not in name_plans([{"eta_hours": 1.0, "risk_exposure": 0.1}, mid], {"eta_hours": 1.0, "risk_exposure": 0.1})


def test_coordinate_ground_validation() -> None:
    from app.main import app

    c = TestClient(app, client=("10.8.0.3", 1))
    assert c.post("/api/trip/plan", json={**BASE, "target_ground": "-70.325,42.925"}).status_code == 200
    for bad in ("0,0", "-70.3;42.9", "<b>", "-70.3,42.9,1"):
        r = c.post("/api/trip/plan", json={**BASE, "target_ground": bad})
        assert r.status_code == 422 and r.json()["fields"] == ["target_ground"], bad


# --- baseline access_lost ----------------------------------------------------------


def test_baseline_access_lost_is_only_closed_jeffreys_ledge() -> None:
    """All baseline lost-access trips target Jeffreys Ledge inside the active
    Western Gulf of Maine closure; none are caused by land cells."""
    from app.api.sim import _current_zones
    from app.engine import simulator as S

    when = S._default_when()
    reasons: Counter = Counter()
    jeffreys = routing.place_lonlat("fishing_grounds", "jeffreys_ledge")
    for t in S.build_synthetic_fleet(200):
        r = route_one(t.origin, t.dest, t.cruise_kn, t.vessel, when, t.risk_pref, extra_zones=_current_zones() or None)
        if r.get("access_lost"):
            al = r["access_lost"]
            reasons[(al["endpoint"], al["code"], al["zone_id"], tuple(t.dest) == jeffreys)] += 1
    assert set(reasons) == {("destination", "closed_zone", "closure_western_gom", True)}
    zone = next(z for z in routing._zone_set(None) if z.id == "closure_western_gom")
    assert zone.active(when)
