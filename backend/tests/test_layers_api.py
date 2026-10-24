"""Lane B tests for the layer endpoints (task 1.5).

One test per endpoint. These assert the contract that matters for the demo:
each layer response is well-formed and carries the required provenance
(``source``, ``fetched_at``, cached/synthetic flags). See design.md section 9
and the data-and-safety steering rule.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Provenance keys every layer response must include.
_PROVENANCE_KEYS = {"source", "fetched_at", "cached", "synthetic", "demo_mode"}


def test_req1_conditions_layer_has_provenance() -> None:
    """GET /api/layers/conditions returns features plus full provenance."""
    resp = client.get("/api/layers/conditions")
    assert resp.status_code == 200
    body = resp.json()

    assert body["layer"] == "conditions"
    assert _PROVENANCE_KEYS <= body["provenance"].keys()
    assert body["provenance"]["source"]  # non-empty source label
    assert body["count"] == len(body["features"])
    # Provenance must be honest: whichever it is, cached XOR synthetic. The
    # conditions snapshot can be a real NOAA download (cached) or a hand-authored
    # demo set (synthetic); the loader reflects the file's own metadata.
    prov = body["provenance"]
    assert isinstance(prov["synthetic"], bool) and isinstance(prov["cached"], bool)
    assert prov["cached"] != prov["synthetic"]


def test_req2_zones_layer_marks_active_state_and_provenance() -> None:
    """GET /api/layers/zones returns zones with an active flag and provenance."""
    resp = client.get("/api/layers/zones", params={"time": "2026-03-14T18:00:00Z"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["layer"] == "zones"
    assert _PROVENANCE_KEYS <= body["provenance"].keys()
    assert body["count"] == len(body["features"])
    for feature in body["features"]:
        # Inactive zones are returned (dimmed), not hidden (Req 2.3).
        assert "active" in feature
        assert isinstance(feature["active"], bool)


def test_req3_risk_layer_is_synthetic_and_monotonic_in_speed() -> None:
    """GET /api/layers/risk returns a synthetic-flagged grid that rises with speed."""
    slow = client.get("/api/layers/risk", params={"speed": 8})
    fast = client.get("/api/layers/risk", params={"speed": 16})
    assert slow.status_code == 200 and fast.status_code == 200

    slow_body, fast_body = slow.json(), fast.json()
    assert slow_body["layer"] == "risk"
    assert _PROVENANCE_KEYS <= slow_body["provenance"].keys()
    # The risk stub is never calibrated data (see _risk_stub.py).
    assert slow_body["provenance"]["synthetic"] is True

    # Every risk score stays within [0, 1] and is non-decreasing in speed.
    for cell in slow_body["cells"] + fast_body["cells"]:
        assert 0.0 <= cell["risk"] <= 1.0
    for slow_cell, fast_cell in zip(slow_body["cells"], fast_body["cells"]):
        assert fast_cell["risk"] >= slow_cell["risk"]
