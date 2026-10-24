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
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.simulator import (
    Simulator,
    build_synthetic_fleet,
    preloaded_scenarios,
    synthetic_route_one,
)

WHEN = datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc)


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
