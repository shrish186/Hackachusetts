"""Lane B task 6: agent tool functions return provenance and valid JSON schemas."""
from __future__ import annotations

import json

import pytest

from app.agent.tools import call_tool, tool_schemas

TRIP = {"port": "gloucester", "vessel": "mid_trawler", "cruise_kn": 9.5, "max_hours": 14,
        "depart_window": ["2026-03-15T09:00:00Z", "2026-03-15T09:00:00Z"],
        "target_ground": "stellwagen_bank", "risk_pref": 0.5, "language": "en"}
BB = [-70.7, 41.9, -70.1, 42.7]


def test_tool_schemas_are_json_objects() -> None:
    specs = tool_schemas()
    assert {s["name"] for s in specs} == {"get_conditions", "get_zones", "get_whale_risk",
                                          "plan_routes", "get_effort_proxy", "estimate_fuel"}
    for s in specs:
        assert s["input_schema"]["type"] == "object"
        json.dumps(s)


@pytest.mark.parametrize("name,args", [
    ("get_conditions", {"bbox": BB}),
    ("get_zones", {"bbox": BB, "time": "2026-03-15T09:00:00Z"}),
    ("get_whale_risk", {"bbox": BB, "time": "2026-03-15T09:00:00Z", "speed_kn": 9.5}),
    ("get_effort_proxy", {"bbox": BB, "month": 3}),
    ("plan_routes", {"trip_request": TRIP}),
    ("estimate_fuel", {"route": {"waypoints": [[-70.66, 42.6], [-70.25, 42.35]]}, "vessel": "small_boat"}),
])
def test_every_tool_returns_provenance(name: str, args: dict) -> None:
    out = call_tool(name, args)
    assert {"source", "fetched_at", "synthetic"} <= out.keys()
    json.dumps(out)


def test_tools_demo_mode_never_goes_live() -> None:
    out = call_tool("get_conditions", {})
    assert out["demo_mode"] is True and out["cached"] is True


def test_tool_input_validation() -> None:
    with pytest.raises(ValueError):
        call_tool("get_whale_risk", {"speed_kn": 0})
    with pytest.raises(ValueError):
        call_tool("get_conditions", {"bbox": [0, 0, 1]})
    with pytest.raises(ValueError):
        call_tool("plan_routes", {"trip_request": {**TRIP, "risk_pref": 2}})
