"""Lane B task 8: POST /api/trip/plan (SSE) and POST /api/trip/brief (HTML)."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, client=("10.0.2.1", 1))

TRIP = {"port": "provincetown", "vessel": "mid_trawler", "cruise_kn": 9.5, "max_hours": 14,
        "depart_window": ["2026-03-15T09:00:00Z", "2026-03-15T09:00:00Z"],
        "target_ground": "stellwagen_bank", "risk_pref": 0.6, "language": "en"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_req4_plan_streams_tool_events_then_plans() -> None:
    r = client.post("/api/trip/plan", json=TRIP)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    names = [e for e, _ in events]
    assert names[-2:] == ["plans", "done"]
    assert names.count("tool_call") == names.count("tool_result") <= 8
    for ev, data in events:
        if ev in ("tool_call", "tool_result"):
            assert {"id", "tool", "label", "status"} <= data.keys()
    plans = dict(events)["plans"]
    assert 2 <= len(plans["plans"]) <= 3
    for p in plans["plans"]:
        assert {"waypoints", "eta_hours", "fuel_est_l", "zones_crossed", "max_wave_m",
                "risk_exposure", "effort_proxy", "citations", "weather_window"} <= p.keys()
    assert "Advisory only" in plans["disclaimer"]


def test_req4_plan_rejects_bad_input() -> None:
    for bad in ({**TRIP, "risk_pref": 1.5}, {**TRIP, "cruise_kn": 0}, {**TRIP, "port": "atlantis"},
                {**TRIP, "max_hours": 999}, {**TRIP, "extra": 1}, {**TRIP, "port": "<script>"}):
        r = client.post("/api/trip/plan", json=bad)
        assert r.status_code == 422, bad
        assert r.json()["error"] == "Invalid input."


def test_req8_brief_is_printable_html_with_required_sections() -> None:
    events = dict(parse_sse(client.post("/api/trip/plan", json={**TRIP, "language": "pt"}).text))
    plan = events["plans"]["plans"][0]
    r = client.post("/api/trip/brief", json={"plan": plan, "language": "pt", "trip": {**TRIP, "language": "pt"}})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    page = r.text
    for needle in ("Pontos de rota", "Alertas de zonas", "Janela de tempo", "Horários dos dados",
                   "Apenas orientativo", "Cape Cod Bay Seasonal Management Area", f"{plan['eta_hours']:g} h"):
        assert needle in page, needle
    assert "compliant" not in page.lower()


def test_req8_brief_escapes_user_text() -> None:
    plan = {"name": "<script>alert(1)</script>", "waypoints": [[-70.2, 42.0]], "eta_hours": 1, "fuel_est_l": 1,
            "zones_crossed": ["<img src=x>"], "max_wave_m": 1, "risk_exposure": 0.1}
    page = client.post("/api/trip/brief", json={"plan": plan}).text
    assert "<script>alert" not in page and "<img src=x>" not in page
