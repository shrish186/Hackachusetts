"""Lane B tests for the layer endpoints (task 1.5 / 3).

Provenance is asserted against each snapshot's own metadata, so the tests stay
honest when Lane A swaps synthetic seeds for real downloads.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.ingest.config import data_path
from app.main import app

client = TestClient(app, client=("10.0.0.1", 50001))

_PROVENANCE_KEYS = {"source", "fetched_at", "cached", "synthetic", "demo_mode"}


def _meta(name: str) -> dict:
    return json.loads(data_path("snapshots", name).read_text()).get("metadata", {})


def test_req1_conditions_layer_has_provenance() -> None:
    resp = client.get("/api/layers/conditions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["layer"] == "conditions"
    assert _PROVENANCE_KEYS <= body["provenance"].keys()
    assert body["provenance"]["synthetic"] is bool(_meta("conditions.json").get("synthetic", False))
    assert body["provenance"]["cached"] is True  # demo mode serves the snapshot
    assert body["count"] == len(body["items"]) > 0
    for item in body["items"]:
        assert {"cell_id", "wave_m", "wind_kn", "source", "fetched_at", "cached", "synthetic"} <= item.keys()


def test_req1_conditions_bbox_filter_uses_grid() -> None:
    all_items = client.get("/api/layers/conditions").json()["items"]
    first = all_items[0]
    tight = f"{first['lon'] - 0.01},{first['lat'] - 0.01},{first['lon'] + 0.01},{first['lat'] + 0.01}"
    got = client.get("/api/layers/conditions", params={"bbox": tight}).json()["items"]
    assert [i["cell_id"] for i in got] == [first["cell_id"]]
    assert client.get("/api/layers/conditions", params={"bbox": "0,0,1,1"}).json()["count"] == 0


def test_req2_zones_layer_marks_active_state_and_provenance() -> None:
    resp = client.get("/api/layers/zones", params={"time": "2026-03-14T18:00:00Z"})
    assert resp.status_code == 200
    body = resp.json()
    assert _PROVENANCE_KEYS <= body["provenance"].keys()
    assert body["count"] == len(body["items"]) > 0
    by_id = {z["id"]: z for z in body["items"]}
    assert by_id["sma_cape_cod_bay"]["active"] is True
    late = client.get("/api/layers/zones", params={"time": "2026-08-01T00:00:00Z"}).json()
    # Inactive zones are returned (dimmed), not hidden (Req 2.3).
    assert {z["id"]: z["active"] for z in late["items"]}["sma_cape_cod_bay"] is False
    if any(z["synthetic"] for z in body["items"]):
        assert body["provenance"]["synthetic"] is True


def test_req3_risk_layer_is_synthetic_and_monotonic_in_speed() -> None:
    params = {"time": "2026-03-15T09:00:00Z"}
    slow = client.get("/api/layers/risk", params={**params, "speed": 8}).json()
    fast = client.get("/api/layers/risk", params={**params, "speed": 16}).json()
    assert slow["provenance"]["synthetic"] is True
    assert slow["count"] > 0
    fast_by_id = {c["cell_id"]: c["risk"] for c in fast["items"]}
    for cell in slow["items"]:
        assert 0.0 <= cell["risk"] <= 1.0
        assert {"presence", "recency", "lethality"} <= cell["factors"].keys()
        assert fast_by_id[cell["cell_id"]] >= cell["risk"]


def test_layers_reject_bad_input() -> None:
    assert client.get("/api/layers/risk", params={"speed": 0}).status_code == 422
    assert client.get("/api/layers/risk", params={"speed": 99}).status_code == 422
    bad = client.get("/api/layers/conditions", params={"bbox": "1,2,3"})
    assert bad.status_code == 422 and "Traceback" not in bad.text
    assert client.get("/api/layers/zones", params={"bbox": "-69,41,-71,43"}).status_code == 422


def test_meta_sources_shape() -> None:
    body = client.get("/api/meta/sources").json()
    assert body["demo_mode"] is True
    assert body["data_timestamp"]
    for s in body["sources"]:
        assert {"layer", "source_url", "fetched_at", "cached", "synthetic"} <= s.keys()
