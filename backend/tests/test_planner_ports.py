"""Lane B: planner_only ports, plans from every port id, two-phase warm-up."""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from app.api import warmup
from app.engine import fleet, routing
from app.main import app

REPLAY = "2026-03-15T13:00:00Z"
TRIP = {"vessel": "small_boat", "cruise_kn": 9, "max_hours": 12, "depart_window": [REPLAY, REPLAY],
        "target_ground": "stellwagen_bank", "risk_pref": 0.5, "language": "en"}
FAKE = {"name": "Aaa Test Harbor", "lon": -70.55, "lat": 41.95, "planner_only": True}


def _client() -> TestClient:
    return TestClient(app, client=("10.9.2.1", 1))


def _sse(text: str) -> dict:
    out = {}
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out[lines["event"]] = json.loads(lines["data"])
    return out


def _assert_plans_or_clear_reason(r) -> None:
    assert r.status_code == 200, r.text
    ev = _sse(r.text)
    assert "error" not in ev and "done" in ev
    p = ev["plans"]
    if p["plans"]:
        assert 1 <= len(p["plans"]) <= 3
    else:
        assert p["access_lost"] or "No legal route" in (p["message"] or ""), p


@pytest.mark.parametrize("port", sorted(routing.ports_config()["ports"]))
def test_every_port_id_plans(port: str) -> None:
    _assert_plans_or_clear_reason(_client().post("/api/trip/plan", json={**TRIP, "port": port}))


@pytest.fixture
def with_fake_port(monkeypatch):
    cfg = routing.ports_config()
    patched = {**cfg, "ports": {**cfg["ports"], "aaa_test_harbor": FAKE}}
    monkeypatch.setattr(routing, "ports_config", lambda: patched)
    import app.api.trip as trip_mod
    import app.ingest.ports as ingest_ports

    monkeypatch.setattr(trip_mod, "ports_config", lambda: patched)
    monkeypatch.setattr(ingest_ports, "_ports_cfg", lambda: patched)
    monkeypatch.setattr(fleet, "_ports", lambda: patched["ports"])
    from app.api import ports as ports_api

    ports_api._cache.clear()
    yield
    ports_api._cache.clear()


def test_planner_only_port_not_in_fleet(with_fake_port) -> None:
    assert "aaa_test_harbor" not in fleet.fleet_ports()
    trips = fleet.build_fleet(200)
    assert all(t.port != "aaa_test_harbor" for t in trips)


def test_fleet_unchanged_by_planner_only_port(monkeypatch) -> None:
    before = [t.to_dict() for t in fleet.build_fleet(200)]
    cfg = routing.ports_config()
    monkeypatch.setattr(fleet, "_ports", lambda: {**cfg["ports"], "aaa_test_harbor": FAKE})
    assert [t.to_dict() for t in fleet.build_fleet(200)] == before


def test_planner_only_port_listed_sorted_and_plannable(with_fake_port) -> None:
    c = _client()
    body = c.get("/api/meta/ports", params={"time": REPLAY}).json()
    names = [p["name"] for p in body["ports"]]
    assert names == sorted(names, key=str.lower)
    fake = next(p for p in body["ports"] if p["id"] == "aaa_test_harbor")
    assert fake["planner_only"] is True and len(fake["grounds"]) == len(routing.ports_config()["fishing_grounds"])
    assert all(p["planner_only"] is False for p in body["ports"] if p["id"] != "aaa_test_harbor")
    _assert_plans_or_clear_reason(c.post("/api/trip/plan", json={**TRIP, "port": "aaa_test_harbor"}))


def test_ready_after_basic_phase_while_full_runs(monkeypatch) -> None:
    monkeypatch.setattr(warmup, "_state", {"started": True, "ready": False, "error": None, "seconds": None,
                                           "plans": 0, "full_ready": False, "full_seconds": None})
    monkeypatch.setattr(warmup, "run_full", lambda pause=0.0: time.sleep(1.0) or 0)
    c = _client()
    assert c.get("/api/ready").status_code == 503
    import threading

    th = threading.Thread(target=warmup.run_warmup)
    t0 = time.monotonic()
    th.start()
    while c.get("/api/ready").status_code != 200:
        assert time.monotonic() - t0 < 10
        time.sleep(0.02)
    body = c.get("/api/ready").json()
    assert body["full_warmup"] == "running"
    th.join()
    assert c.get("/api/ready").json()["full_warmup"] == "done"


def test_ready_is_cheap() -> None:
    c = _client()
    t0 = time.perf_counter()
    for _ in range(20):
        c.get("/api/ready")
    assert (time.perf_counter() - t0) / 20 < 0.05


def test_per_port_warmup_respects_budget(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(warmup, "_plan", lambda trip, dep: calls.append(trip["port"]) or time.sleep(0.05))
    cfg = routing.ports_config()
    many = {**cfg, "ports": {**cfg["ports"], **{f"p{i:02d}": FAKE for i in range(40)}}}
    monkeypatch.setattr(routing, "ports_config", lambda: many)
    n = warmup.warm_all_ports([warmup.REPLAY_DEPART], budget_s=0.2)
    assert n == len(calls) and 3 <= n <= 6
