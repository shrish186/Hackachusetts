"""API tests for the what-if simulator endpoints (Lane D, Req 6, task 3).

Covers the production incident and its fix:
  * preset scenarios are served from the precompute snapshot in < 0.5 s;
  * a small custom polygon runs live in < 8 s;
  * concurrent custom requests do not deadlock (one runs, extras get 429);
  * malformed polygons (self-intersecting/zero-area, outside the study area,
    10,000 vertices, NaN coordinates) return 422, never 500/504;
  * no public API response contains the string "TODO".
"""

from __future__ import annotations

import threading
import time

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

_SMALL_POLY = {
    "type": "Polygon",
    "coordinates": [[
        [-70.4, 42.2], [-70.1, 42.2], [-70.1, 42.5], [-70.4, 42.5], [-70.4, 42.2],
    ]],
}


# --- Preset latency -----------------------------------------------------------

def test_req6_preset_is_fast_and_precomputed() -> None:
    """A preset scenario returns in under 0.5 s from the precompute snapshot."""
    t0 = time.perf_counter()
    r = client.post("/api/sim/run", json={"scenario_id": "extend_closure_east"})
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200
    assert elapsed < 0.5, f"preset took {elapsed:.3f}s (budget 0.5s)"
    body = r.json()
    assert body["served_from"] == "precomputed"
    assert "computed_at" in body
    # All preloaded scenarios are returned so the frontier is meaningful.
    n_presets = client.get("/api/sim/scenarios").json()["count"]
    assert len(body["options"]) == n_presets
    assert len(body["pareto"]) == n_presets


def test_req6_all_presets_served() -> None:
    """Every advertised scenario id runs and returns the preset set."""
    ids = [s["id"] for s in client.get("/api/sim/scenarios").json()["scenarios"]]
    for sid in ids:
        r = client.post("/api/sim/run", json={"scenario_id": sid})
        assert r.status_code == 200, sid
        assert r.json()["requested"] == sid


def test_req6_unknown_scenario_is_422() -> None:
    assert client.post("/api/sim/run", json={"scenario_id": "nope"}).status_code == 422


# --- Custom polygon budget ----------------------------------------------------

def test_req6_small_custom_polygon_under_budget() -> None:
    """A small valid custom polygon runs live within the 8 s budget."""
    t0 = time.perf_counter()
    r = client.post("/api/sim/run", json={"polygon": _SMALL_POLY, "prohibited": True})
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200
    assert elapsed < 8.0, f"custom polygon took {elapsed:.3f}s (budget 8s)"
    assert r.json()["served_from"] == "live"


# --- Bad polygons -> 422 (never 500/504) --------------------------------------

def test_req6_zero_area_polygon_422() -> None:
    poly = {"type": "Polygon", "coordinates": [[[-70, 42], [-70, 42], [-70, 42], [-70, 42]]]}
    assert client.post("/api/sim/run", json={"polygon": poly}).status_code == 422


def test_req6_self_intersecting_polygon_422_not_500() -> None:
    bowtie = {"type": "Polygon", "coordinates": [[
        [-70.4, 42.2], [-70.1, 42.5], [-70.1, 42.2], [-70.4, 42.5], [-70.4, 42.2],
    ]]}
    assert client.post("/api/sim/run", json={"polygon": bowtie}).status_code == 422


def test_req6_outside_study_area_422() -> None:
    poly = {"type": "Polygon", "coordinates": [[
        [10, 10], [10.1, 10], [10.1, 10.1], [10, 10.1], [10, 10],
    ]]}
    assert client.post("/api/sim/run", json={"polygon": poly}).status_code == 422


def test_req6_too_many_vertices_422() -> None:
    ring = [[-70.4 + 0.00001 * i, 42.2] for i in range(10001)]
    ring.append(ring[0])
    poly = {"type": "Polygon", "coordinates": [ring]}
    assert client.post("/api/sim/run", json={"polygon": poly}).status_code == 422


def test_req6_nan_coordinates_422() -> None:
    raw = (
        '{"polygon":{"type":"Polygon","coordinates":'
        '[[[NaN,42],[-70,42],[-70,42.5],[-70.4,42.5],[NaN,42]]]}}'
    )
    r = client.post("/api/sim/run", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_req6_requires_exactly_one_input() -> None:
    # both -> 422, neither -> 422
    assert client.post("/api/sim/run", json={"scenario_id": "x", "polygon": _SMALL_POLY}).status_code == 422
    assert client.post("/api/sim/run", json={}).status_code == 422


# --- Concurrency: no deadlock; extras get 429 ---------------------------------

def test_req6_concurrent_custom_requests_do_not_deadlock() -> None:
    """Fire several custom requests at once: all return promptly (200 or 429).

    The single-flight semaphore means at most one runs the live sim; the rest
    fail fast with 429 "busy". The key assertion is that none hang and the
    process does not deadlock.
    """
    results: list[int] = []
    lock = threading.Lock()

    def hit() -> None:
        r = client.post("/api/sim/run", json={"polygon": _SMALL_POLY, "prohibited": True})
        with lock:
            results.append(r.status_code)

    threads = [threading.Thread(target=hit) for _ in range(5)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.perf_counter() - t0

    assert all(not t.is_alive() for t in threads), "a request hung (possible deadlock)"
    assert len(results) == 5
    assert all(code in (200, 429) for code in results), results
    assert 200 in results, "at least one request should succeed"
    assert elapsed < 30, "concurrent requests took too long"


# --- No TODO leaks in public responses ----------------------------------------

def test_no_public_response_contains_todo() -> None:
    """No public API response body may contain the string 'TODO' (task 6)."""
    endpoints = [
        ("GET", "/api/health", None),
        ("GET", "/api/meta/sources", None),
        ("GET", "/api/sim/scenarios", None),
        ("GET", "/api/layers/zones", None),
        ("GET", "/api/layers/conditions", None),
        ("GET", "/api/layers/risk", None),
    ]
    for method, path, _ in endpoints:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "TODO" not in r.text, f"{path} response contains TODO"
    # And the sim run response.
    r = client.post("/api/sim/run", json={"scenario_id": "seasonal_speed_limit"})
    assert "TODO" not in r.text


# --- Baseline access_lost + plain-language explanation (task 4) ---------------

def test_req6_baseline_reports_access_lost_with_explanation() -> None:
    """The baseline reports lost access (grounds in today's closed zones) and a
    plain-language explanation whose numbers match, identical across languages.

    Confirms Shrish's routing finding (docs/API_CONTRACT.md): the router counts
    trips to grounds inside active closed zones as lost access rather than
    relocating them, so the baseline shows access_lost > 0 with no scenario.
    """
    import re

    r = client.post("/api/sim/run", json={"scenario_id": "extend_closure_east"})
    assert r.status_code == 200
    body = r.json()

    base = body["baseline"]
    assert base["trips"] == 200
    assert base["access_lost"] > 0, "baseline should report grounds already closed"

    exp = body["baseline_explanation"]
    assert set(exp) == {"en", "pt", "es"}
    # The real numbers appear in the text.
    assert str(base["access_lost"]) in exp["en"]
    assert str(base["trips"]) in exp["en"]
    # Numbers are identical across all three languages (Req 7.2).
    def nums(s: str) -> list[str]:
        return re.findall(r"\d+", s)

    assert nums(exp["en"]) == nums(exp["pt"]) == nums(exp["es"])
