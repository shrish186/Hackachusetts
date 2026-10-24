"""Tests for the what-if simulator (Lane D, Req 6, design.md section 8).

Covers the invariants from the task brief:
  * no option on the Pareto frontier is dominated by another option;
  * deltas are internally consistent (sign/magnitude match the totals);
  * the trilingual summaries carry IDENTICAL numbers across en/pt/es.

A deterministic **fake router** is injected so the tests do not depend on
Shrish's real ``route_one`` landing. The fake honors the same signature and
makes prohibited zones costly, which is all the simulator needs.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime

from app.engine.simulator import (
    Simulator,
    build_synthetic_fleet,
    preloaded_scenarios,
    synthetic_route_one,
)
from hypothesis import given, settings
from hypothesis import strategies as st

WHEN = datetime(2026, 3, 15, 11, 0, tzinfo=UTC)


def fake_router(origin, dest, speed_kn, vessel, when, risk_pref, extra_zones=None):
    """Deterministic router: extra prohibited/limited zones raise cost/lower risk."""
    extra_zones = extra_zones or []
    base_hours = 4.0 + abs(dest[0] - origin[0]) + abs(dest[1] - origin[1])
    detour = 1.0
    speed = speed_kn
    for z in extra_zones:
        if z.get("prohibited"):
            detour += 0.3
        if z.get("speed_limit_kn"):
            speed = min(speed, float(z["speed_limit_kn"]))
    hours = base_hours * detour / max(speed / 10.0, 0.1)
    return {
        "eta_hours": hours,
        "fuel_est_l": hours * 50.0,
        "risk_exposure": (0.4 if not extra_zones else 0.25) * hours,
    }


def _sim() -> Simulator:
    """A simulator with a small deterministic fleet and the fake router."""
    fleet = build_synthetic_fleet(size=40, seed="test-fleet")
    return Simulator(router=fake_router, fleet=fleet, current_zones=[])


# --- Example tests ------------------------------------------------------------

def test_req6_scenarios_endpoint_lists_three() -> None:
    """There are exactly three preloaded scenarios with stable ids."""
    scen = preloaded_scenarios()
    assert len(scen) == 3
    assert {s.id for s in scen} == {
        "extend_closure_east",
        "dynamic_zone_sightings",
        "seasonal_speed_limit",
    }


def test_req6_run_all_shape_and_frontier_present() -> None:
    """run_all returns baseline, 3 options, and at least one frontier option."""
    result = _sim().run_all()
    assert set(result["baseline"]) >= {"risk_exposure", "steaming_hours", "fuel_l", "effort_access"}
    assert len(result["options"]) == 3
    assert any(o["on_frontier"] for o in result["options"])
    # Effort is labelled an estimate, not revenue (Req 6.4).
    assert "estimate" in result["labels"]["effort_access"].lower()
    assert result["fleet"]["synthetic"] is True


def test_req6_baseline_is_cached() -> None:
    """The baseline is computed once and reused."""
    sim = _sim()
    b1 = sim.baseline(WHEN)
    b2 = sim.baseline(WHEN)
    assert b1 is b2  # same cached object


def test_req6_runs_fast_for_200_trips() -> None:
    """A full 200-trip run finishes well under the 20 s budget."""
    sim = Simulator(router=fake_router, fleet=build_synthetic_fleet(200), current_zones=[])
    t0 = time.perf_counter()
    sim.run_all()
    assert time.perf_counter() - t0 < 20.0


# --- Property / invariant tests ----------------------------------------------

def test_req6_frontier_has_no_dominated_option() -> None:
    """No option flagged on_frontier is dominated by any other option.

    Objectives minimized: x = delta_risk_pct, y = -delta_effort_access_pct.
    """
    options = _sim().run_all()["options"]
    pts = [
        (o["deltas_pct"]["risk"], -o["deltas_pct"]["effort_access"], o["on_frontier"])
        for o in options
    ]
    for xi, yi, on_frontier in pts:
        if not on_frontier:
            continue
        for xj, yj, _ in pts:
            if (xj, yj) == (xi, yi):
                continue
            dominates = (xj <= xi and yj <= yi) and (xj < xi or yj < yi)
            assert not dominates, "a frontier option was dominated"


def test_req6_every_dominated_option_is_off_frontier() -> None:
    """Conversely, any option dominated by another must not be on the frontier."""
    options = _sim().run_all()["options"]
    pts = [(o["deltas_pct"]["risk"], -o["deltas_pct"]["effort_access"]) for o in options]
    for i, (xi, yi) in enumerate(pts):
        dominated = any(
            (xj <= xi and yj <= yi) and (xj < xi or yj < yi)
            for j, (xj, yj) in enumerate(pts)
            if j != i
        )
        if dominated:
            assert options[i]["on_frontier"] is False


def test_req6_deltas_consistent_with_totals() -> None:
    """Each percent delta's sign matches scenario-vs-baseline totals."""
    sim = _sim()
    result = sim.run_all()
    base = result["baseline"]
    for o in result["options"]:
        tot = o["totals"]
        d = o["deltas_pct"]
        for key_tot, key_delta in [
            ("risk_exposure", "risk"),
            ("steaming_hours", "hours"),
            ("fuel_l", "fuel"),
            ("effort_access", "effort_access"),
        ]:
            if base[key_tot] == 0:
                continue
            sign_delta = (tot[key_tot] - base[key_tot])
            if sign_delta > 0:
                assert d[key_delta] >= 0
            elif sign_delta < 0:
                assert d[key_delta] <= 0


def _numbers(text: str) -> list[str]:
    """Extract all numeric tokens (with optional % and decimals) from a string."""
    return re.findall(r"\d+\.\d+%?|\d+%?", text)


def test_req7_translations_carry_identical_numbers() -> None:
    """en/pt/es summaries contain the exact same numeric tokens (Req 7.2)."""
    result = _sim().run_all()
    for o in result["options"]:
        s = o["summary"]
        en, pt, es = _numbers(s["en"]), _numbers(s["pt"]), _numbers(s["es"])
        assert en == pt == es, f"numbers differ across languages for {o['scenario_id']}"
        assert en, "summary should contain at least one number"


@given(
    speed=st.floats(min_value=1.0, max_value=25.0, allow_nan=False, allow_infinity=False),
    risk_pref=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50, deadline=None)
def test_synthetic_router_outputs_nonnegative(speed: float, risk_pref: float) -> None:
    """The fallback router never returns negative eta/fuel/risk."""
    res = synthetic_route_one((-70.66, 42.61), (-70.25, 42.35), speed, "mid_trawler", WHEN, risk_pref)
    assert res["eta_hours"] >= 0
    assert res["fuel_est_l"] >= 0
    assert res["risk_exposure"] >= 0


# --- Access lost (task 4) -----------------------------------------------------

def _poly(min_lon, min_lat, max_lon, max_lat):
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat],
            [min_lon, max_lat], [min_lon, min_lat],
        ]],
    }


def test_req6_ground_closure_reports_access_lost_not_relocation() -> None:
    """A prohibited zone over a fishing ground is reported as access_lost.

    Stellwagen Bank sits near (-70.25, 42.35); a prohibited zone covering it
    must mark trips to that ground as access_lost rather than relocating them.
    """
    from app.engine.simulator import Scenario

    fleet = build_synthetic_fleet(size=60, seed="access-lost")
    # Ensure at least one trip targets a ground inside the closure.
    targets_in = [t for t in fleet if -70.35 <= t.dest[0] <= -70.1 and 42.25 <= t.dest[1] <= 42.5]
    sim = Simulator(router=fake_router, fleet=fleet, current_zones=[])
    closure = Scenario(
        id="close_stellwagen",
        name="Close Stellwagen",
        description="prohibited over Stellwagen",
        extra_zones=[{
            "id": "close_stellwagen", "name": "Close Stellwagen", "kind": "fishing_closure",
            "geometry": _poly(-70.35, 42.25, -70.1, 42.5), "prohibited": True,
            "speed_limit_kn": None, "synthetic": True,
        }],
    )
    opt = sim.run_scenario(closure, WHEN)
    if targets_in:
        assert opt.totals.access_lost >= 1
        assert opt.as_dict()["cost_breakdown"]["access_lost_trips"] == opt.totals.access_lost


def test_req6_pareto_points_present_and_match_options() -> None:
    """run_all exposes pareto points, one per option, with on_frontier flags."""
    result = _sim().run_all()
    assert len(result["pareto"]) == len(result["options"])
    by_id = {p["scenario_id"]: p for p in result["pareto"]}
    for o in result["options"]:
        p = by_id[o["scenario_id"]]
        assert p["on_frontier"] == o["on_frontier"]
        # risk_reduced is the negation of the risk delta.
        assert p["risk_reduced"] == round(-o["deltas_pct"]["risk"], 2)


# --- Property: a prohibited zone never raises risk, never lowers cost ---------

@st.composite
def _prohibited_zone(draw):
    """A valid prohibited rectangle somewhere in/around the study area."""
    min_lon = draw(st.floats(min_value=-71.0, max_value=-69.5))
    min_lat = draw(st.floats(min_value=41.0, max_value=43.0))
    w = draw(st.floats(min_value=0.1, max_value=1.0))
    h = draw(st.floats(min_value=0.1, max_value=1.0))
    return {
        "id": "pbt_zone", "name": "PBT zone", "kind": "fishing_closure",
        "geometry": _poly(min_lon, min_lat, min_lon + w, min_lat + h),
        "prohibited": True, "speed_limit_kn": None, "synthetic": True,
    }


@given(zone=_prohibited_zone())
@settings(max_examples=40, deadline=None)
def test_req6_prohibited_zone_never_increases_risk_and_always_costs_the_fleet(zone) -> None:
    """Adding a prohibited zone never increases total whale risk, and always
    costs the fleet (more steaming time, OR lost access to a closed ground).

    A no-entry zone can only force detours or close grounds, so the fleet can
    never be exposed to MORE whale risk than with the zone absent. For the
    livelihood side, the honest cost is twofold: trips that can still reach
    their ground steam further (hours up), and trips whose ground the closure
    removes are counted as ``access_lost`` (ground unreachable, not relocated —
    task 4). The invariant is therefore: risk never rises, and the fleet is
    never strictly better off — either steaming hours do not fall, or some
    access was lost.

    (An earlier version asserted steaming_hours alone never falls; Hypothesis
    found the counterexample where a closure removes grounds entirely, dropping
    those trips' hours. That is lost access, a real cost, not a free lunch — so
    the invariant now accounts for access_lost. Logged in LOG-vidhaan.md.)
    """
    from app.engine.simulator import Scenario

    fleet = build_synthetic_fleet(size=40, seed="pbt")
    sim = Simulator(router=fake_router, fleet=fleet, current_zones=[])
    base = sim.baseline(WHEN)
    scen = Scenario(id="pbt", name="PBT", description="pbt", extra_zones=[zone])
    opt = sim.run_scenario(scen, WHEN)
    tol = 1e-9
    # Risk never increases.
    assert opt.totals.risk_exposure <= base.risk_exposure + tol, "prohibited zone increased risk"
    # The fleet is never strictly better off: either it steams at least as much,
    # or access was lost (grounds closed).
    steams_at_least_as_much = opt.totals.steaming_hours >= base.steaming_hours - tol
    lost_access = opt.totals.access_lost > 0
    assert steams_at_least_as_much or lost_access, "prohibited zone was a free lunch (no cost)"
    # When access is lost, effort access must drop (grounds removed).
    if lost_access:
        assert opt.totals.effort_access <= base.effort_access + tol
