"""Lane B: GET /api/meta/ports and friendly port/ground validation."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app, client=("10.9.1.1", 1))
TRIP = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12,
        "depart_window": ["2026-03-15T13:00:00Z"] * 2, "target_ground": "stellwagen_bank",
        "risk_pref": 0.8, "language": "en"}


def _grounds(time: str) -> dict:
    r = c.get("/api/meta/ports", params={"time": time})
    assert r.status_code == 200, r.text
    body = r.json()
    return body, {g["id"]: g for g in body["ports"][0]["grounds"]}


def test_five_ports_with_shape() -> None:
    body, _ = _grounds("2026-03-15T13:00:00Z")
    assert body["time"] == "2026-03-15T13:00:00Z"
    ids = {p["id"] for p in body["ports"]}
    base = {"gloucester", "boston", "plymouth", "provincetown", "new_bedford"}
    assert base <= ids
    assert {p["id"] for p in body["ports"] if not p["planner_only"]} == base
    for p in body["ports"]:
        assert p["state"] == "MA" and {"name", "lon", "lat", "grounds"} <= p.keys()
        for g in p["grounds"]:
            assert {"id", "name", "lon", "lat", "closed", "closed_reason", "zone_id"} <= g.keys()


def test_jeffreys_closed_in_replay_open_in_october() -> None:
    _, march = _grounds("2026-03-15T13:00:00Z")
    j = march["jeffreys_ledge"]
    assert j["closed"] is True and j["zone_id"] == "closure_western_gom"
    assert "Western Gulf of Maine" in j["closed_reason"] and "2026-04-30" in j["closed_reason"]
    assert march["stellwagen_bank"]["closed"] is False and march["stellwagen_bank"]["closed_reason"] is None
    _, october = _grounds("2026-10-24T12:00:00Z")
    assert october["jeffreys_ledge"]["closed"] is False and october["jeffreys_ledge"]["zone_id"] is None


def test_closed_matches_router_access_lost() -> None:
    from app.engine.routing import plan_routes

    _, march = _grounds("2026-03-15T13:00:00Z")
    for gid, g in march.items():
        out = plan_routes({**TRIP, "target_ground": gid, "max_hours": 30})
        assert bool(out.get("access_lost")) == g["closed"], gid


def test_bad_time_is_422() -> None:
    for bad in ("not-a-date", "2020-01-01T00:00:00Z", "2031-01-01T00:00:00Z"):
        r = c.get("/api/meta/ports", params={"time": bad})
        assert r.status_code == 422, bad
        assert r.json()["fields"] == ["time"] and "Traceback" not in r.text


def test_default_time_and_cache_header() -> None:
    r = c.get("/api/meta/ports")
    assert r.status_code == 200 and r.json()["time"].endswith("Z")
    assert r.headers["cache-control"] == "public, max-age=30"
    r2 = c.get("/api/meta/ports")
    assert r2.json() == r.json()


def test_unknown_port_and_ground_are_friendly_422() -> None:
    r = c.post("/api/trip/plan", json={**TRIP, "port": "Atlantis"})
    assert r.status_code == 422
    body = r.json()
    assert body["fields"] == ["port"]
    from app.engine.routing import ports_config

    assert "valid ports: " + ", ".join(sorted(ports_config()["ports"])) in body["message"]
    assert "Atlantis" not in r.text and "Traceback" not in r.text
    r = c.post("/api/trip/plan", json={**TRIP, "target_ground": "georges_bank"})
    assert r.status_code == 422 and r.json()["fields"] == ["target_ground"]
    assert "valid grounds: cape_cod_bay, jeffreys_ledge, stellwagen_bank" in r.json()["messages"]["target_ground"]
