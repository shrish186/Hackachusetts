"""Regression tests for the live-QA findings (Lane B, final round)."""
from __future__ import annotations

import importlib
import json
import re
import time

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point

from app.api import security, warmup
from app.engine import routing
from app.engine.routing import plan_routes, route_one
from app.ingest.grid import default_grid

VERCEL = "https://fathom-six-vert.vercel.app"
TRIP = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12,
        "depart_window": ["2026-03-15T07:00:00Z", "2026-03-15T07:00:00Z"],
        "target_ground": "stellwagen_bank", "risk_pref": 0.8, "language": "en"}
_ip = iter(range(1, 10_000))


def fresh_app(monkeypatch, **env: str):
    """Re-import app.main so module-level settings pick up the env vars."""
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app.main as main

    return importlib.reload(main).app


def client(app=None) -> TestClient:
    if app is None:
        from app.main import app
    return TestClient(app, client=(f"10.7.0.{next(_ip) % 250}", 1))


def sse(text: str) -> dict:
    out = {}
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out[lines["event"]] = json.loads(lines["data"])
    return out


@pytest.fixture(autouse=True)
def _restore_app(monkeypatch):
    yield
    monkeypatch.undo()
    import app.main as main

    importlib.reload(main)


# 1. CORS -----------------------------------------------------------------------


def test_cors_origin_parsing(monkeypatch) -> None:
    monkeypatch.setenv("FATHOM_ALLOWED_ORIGINS", f' {VERCEL}/ , "http://localhost:5173",,{VERCEL}')
    assert security.allowed_origins() == [VERCEL, "http://localhost:5173"]


@pytest.mark.parametrize("path", ["/api/trip/plan", "/api/sim/run"])
def test_cors_preflight_allowed_origin(monkeypatch, path: str) -> None:
    app = fresh_app(monkeypatch, FATHOM_ALLOWED_ORIGINS=f"{VERCEL}/")
    r = client(app).options(path, headers={"Origin": VERCEL, "Access-Control-Request-Method": "POST",
                                           "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == VERCEL
    assert "POST" in r.headers["access-control-allow-methods"]
    assert "content-type" in r.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in r.headers


def test_cors_bare_options_no_405(monkeypatch) -> None:
    app = fresh_app(monkeypatch, FATHOM_ALLOWED_ORIGINS=VERCEL)
    r = client(app).options("/api/trip/plan", headers={"Origin": VERCEL})
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == VERCEL


def test_cors_disallowed_origin_gets_no_acao(monkeypatch) -> None:
    app = fresh_app(monkeypatch, FATHOM_ALLOWED_ORIGINS=VERCEL)
    c = client(app)
    pre = c.options("/api/trip/plan", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in pre.headers
    bare = c.options("/api/trip/plan", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bare.headers
    get = c.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in get.headers
    ok = c.get("/api/health", headers={"Origin": VERCEL})
    assert ok.headers["access-control-allow-origin"] == VERCEL


# 2. Validation -------------------------------------------------------------------


@pytest.mark.parametrize("window", [
    ["2026-03-16T07:00:00Z", "2026-03-15T07:00:00Z"],   # reversed (was a 500)
    ["2026-03-15T07:00:00Z", "2026-04-15T07:00:00Z"],   # longer than 14 days
    ["2025-01-01T07:00:00Z", "2025-01-01T07:00:00Z"],   # more than 7 days in the past
])
def test_bad_depart_window_is_422_with_field(window) -> None:
    r = client().post("/api/trip/plan", json={**TRIP, "depart_window": window})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "Invalid input." and body["fields"] == ["depart_window"]
    assert body["messages"]["depart_window"]  # friendly reason, no stack trace


def test_equal_depart_window_is_allowed() -> None:
    # The frontend sends [departIso, departIso].
    assert client().post("/api/trip/plan", json=TRIP).status_code == 200


def test_earliest_departure_outside_demo(monkeypatch) -> None:
    from datetime import datetime, timezone

    from app.api import trip

    monkeypatch.setenv("FATHOM_DEMO_MODE", "false")
    now = datetime(2026, 10, 24, tzinfo=timezone.utc)
    assert trip.earliest_departure(now) == datetime(2026, 10, 17, tzinfo=timezone.utc)


def test_malformed_json_reports_body_field() -> None:
    r = client().post("/api/trip/plan", content=b'{"port": "glou', headers={"content-type": "application/json"})
    assert r.status_code == 422
    assert r.json()["fields"] == ["body"]


# 3. Alternates -------------------------------------------------------------------


def _demo_plans() -> dict:
    return plan_routes(TRIP)


def test_demo_trip_returns_2_to_3_distinct_ranked_plans() -> None:
    out = _demo_plans()
    plans = out["plans"]
    assert 2 <= len(plans) <= 3
    assert plans[0]["rank"] == 1 and [p["rank"] for p in plans] == list(range(1, len(plans) + 1))
    names = [p["name"] for p in plans]
    assert "Fastest" in names and len(set(names)) == len(names)
    fastest = next(p for p in plans if p["name"] == "Fastest")
    assert fastest["eta_hours"] == min(p["eta_hours"] for p in plans)
    for p in plans:
        if p["name"] == "Safest":
            assert p["risk_exposure"] == min(q["risk_exposure"] for q in plans) < fastest["risk_exposure"]
        if p["name"] == "Balanced":
            assert p["risk_exposure"] < fastest["risk_exposure"]
    # Any two plans overlap at most 90 % within a 1-cell buffer (the de-dup rule).
    buf = routing.DEDUPE_BUFFER_CELLS * default_grid().cell_deg
    lines = [LineString(p["waypoints"]) for p in plans]
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a, b = lines[i], lines[j]
            share = min(b.intersection(a.buffer(buf)).length / b.length, a.intersection(b.buffer(buf)).length / a.length)
            assert share <= 0.9 + 0.02, (plans[i]["name"], plans[j]["name"], share)


def test_waypoints_are_dense_half_cell_tolerance() -> None:
    o = routing.place_lonlat("ports", "gloucester")
    d = routing.place_lonlat("fishing_grounds", "stellwagen_bank")
    r = route_one(o, d, 9, "small_boat", routing._parse_dt(TRIP["depart_window"][0]), 0.1)
    g = default_grid()
    line = LineString(r["waypoints"])
    for c in r["cells"]:
        ix, iy = (int(p) for p in c.split("_"))
        assert line.distance(Point(g.center(ix, iy))) <= 0.5 * g.cell_deg + 1e-6
    land = routing._land()
    for a, b in zip(r["waypoints"], r["waypoints"][1:]):
        assert routing._segment_clear(g, a, b, land)


def test_single_route_is_explained_in_narrative() -> None:
    from app.agent.agent import run_agent

    trip = {**TRIP, "port": "provincetown", "target_ground": "cape_cod_bay"}
    out = plan_routes(trip)
    if len(out["plans"]) != 1:
        pytest.skip("geometry now yields alternates for this trip")
    assert out["single_route_reason"].startswith("All weightings give the same route because")
    plans = next(e["data"] for e in run_agent(trip) if e["event"] == "plans")
    assert any("All weightings give the same route because" in s["text"] for s in plans["narrative"])


# 4. Access lost --------------------------------------------------------------------


def test_closed_ground_is_access_lost_not_relocated() -> None:
    out = plan_routes({**TRIP, "target_ground": "jeffreys_ledge"})
    assert out["ok"] is False and out["plans"] == []
    info = out["access_lost"]
    assert info["endpoint"] == "destination" and info["code"] == "closed_zone"
    assert info["zone_id"] == "closure_western_gom" and info["zone_active_to"].startswith("2026-04-30")
    alt = info["nearest_open"]
    assert alt["distance_nm"] > 0
    zone = next(z for z in routing._zone_set(None) if z.id == "closure_western_gom")
    assert not routing._zone_prep(zone.geom_key).covers(Point(alt["lon"], alt["lat"]))
    assert "Nearest open water" in out["message"]


def test_land_endpoint_is_access_lost() -> None:
    inland = (-70.95, 42.2)  # Quincy/Braintree: on land in the mask
    r = route_one((-70.66, 42.61), inland, 9, "small_boat", routing._parse_dt(TRIP["depart_window"][0]), 0.5)
    assert r["ok"] is False and r["waypoints"] == []
    assert r["access_lost"]["code"] == "land" and r["access_lost"]["nearest_open"]


def test_candidate_zone_over_ground_is_access_lost() -> None:
    d = routing.place_lonlat("fishing_grounds", "stellwagen_bank")
    box = {"id": "cand", "name": "Candidate closure", "prohibited": True,
           "geometry": {"type": "Polygon", "coordinates": [[[d[0] - .1, d[1] - .1], [d[0] + .1, d[1] - .1],
                                                           [d[0] + .1, d[1] + .1], [d[0] - .1, d[1] + .1], [d[0] - .1, d[1] - .1]]]}}
    r = route_one((-70.66, 42.61), d, 9, "small_boat", routing._parse_dt(TRIP["depart_window"][0]), 0.5, extra_zones=[box])
    assert r["ok"] is False and r["access_lost"]["zone_id"] == "cand"


def test_access_lost_in_sse_and_narrative() -> None:
    ev = sse(client().post("/api/trip/plan", json={**TRIP, "target_ground": "jeffreys_ledge", "language": "pt"}).text)
    assert ev["plans"]["access_lost"]["code"] == "closed_zone"
    assert any("Western Gulf of Maine Seasonal Closure" in s["text"] for s in ev["plans"]["narrative"])


# 5. Production hardening ------------------------------------------------------------


def test_docs_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("FATHOM_ENABLE_DOCS", raising=False)
    c = client(fresh_app(monkeypatch))
    for p in ("/docs", "/redoc", "/openapi.json"):
        assert c.get(p).status_code == 404


def test_docs_enabled_by_env(monkeypatch) -> None:
    c = client(fresh_app(monkeypatch, FATHOM_ENABLE_DOCS="true"))
    assert c.get("/openapi.json").status_code == 200


def test_api_security_headers(monkeypatch) -> None:
    monkeypatch.setenv("FATHOM_TRUST_PROXY", "true")
    c = client()
    g = c.get("/api/meta/sources")
    assert g.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "strict-transport-security" not in g.headers
    hs = c.get("/api/health", headers={"X-Forwarded-Proto": "https"})
    assert hs.headers["strict-transport-security"].startswith("max-age=")
    p = c.post("/api/trip/plan", json=TRIP)
    assert p.headers["cache-control"] == "no-store"
    b = c.post("/api/trip/brief", json={"plan": sse(p.text)["plans"]["plans"][0]})
    assert b.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in b.headers["content-security-policy"]
    monkeypatch.setenv("FATHOM_TRUST_PROXY", "false")
    assert "strict-transport-security" not in c.get("/api/health", headers={"X-Forwarded-Proto": "https"}).headers


# 6. Consistent numbers ----------------------------------------------------------------


def test_narrative_wind_and_wave_match_plan_cards() -> None:
    ev = sse(client().post("/api/trip/plan", json=TRIP).text)["plans"]
    text = " ".join(s["text"] for s in ev["narrative"])
    for p in ev["plans"]:
        assert p["max_wind_kn"] == p["weather_window"]["max_wind_kn"]
        assert p["max_wave_m"] == p["weather_window"]["max_wave_m"]
        m = re.search(rf"On the {re.escape(p['name'])} track waves reach about ([\d.]+) m and wind about ([\d.]+) kn", text)
        assert m, p["name"]
        assert float(m.group(1)) == p["max_wave_m"] and float(m.group(2)) == p["max_wind_kn"]
        assert routing.rnd(p["max_wind_kn"], "kn") == p["max_wind_kn"]


def test_rnd_helper() -> None:
    assert routing.rnd(5.74, "kn") == 5.7
    assert routing.rnd(5.76, "kn") == 5.8
    assert routing.rnd(1.234, "m") == 1.2
    assert routing.rnd(2.3449, "h") == 2.34
    assert routing.rnd(0.123456, "exposure") == 0.1235


# 7. Warm-up ------------------------------------------------------------------------------


def test_health_immediate_and_ready_after_warmup(monkeypatch) -> None:
    monkeypatch.setattr(warmup, "_state", {"started": True, "ready": False, "error": None, "seconds": None})
    c = client()
    t = time.time()
    assert c.get("/api/health").status_code == 200
    assert time.time() - t < 0.5
    assert c.get("/api/ready").status_code == 503
    warmup.run_warmup()
    r = c.get("/api/ready")
    assert r.status_code == 200 and r.json()["status"] == "ready"
    assert r.json()["warmup_seconds"] < 60
