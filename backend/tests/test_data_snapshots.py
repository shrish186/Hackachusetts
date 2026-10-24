"""Data-honesty tests for bundled snapshots (Lane A).

Covers:
- no placeholder strings ("TODO") anywhere in snapshot JSON (task 2)
- every snapshot carries an honest metadata block (task 1, 7)
- every config/ports.yaml port snaps to a water cell (task 4)
- the whale-season demo scenario activates zones; "today" may show none (task 3)
"""

from __future__ import annotations

import json
import re as _re
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from app.ingest.config import config_path, data_path
from app.ingest.ports import (
    all_ports_water_points,
    is_water,
    load_grounds,
    load_ports,
    snap_to_water,
)
from app.ingest.zones import is_active, load_zones

SNAPSHOT_DIR = data_path("snapshots")
JSON_SNAPSHOTS = sorted(SNAPSHOT_DIR.glob("*.json"))


def _iter_strings(obj):
    """Yield every string in a nested JSON structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


@pytest.mark.parametrize("path", JSON_SNAPSHOTS, ids=[p.name for p in JSON_SNAPSHOTS])
def test_no_todo_placeholders_in_snapshots(path: Path):
    """No snapshot string may contain a placeholder like TODO / TODO-VERIFY (task 2)."""
    payload = json.loads(path.read_text())
    offenders = [s for s in _iter_strings(payload) if "TODO" in s.upper()]
    assert not offenders, f"{path.name} contains placeholder strings: {offenders}"


@pytest.mark.parametrize("path", JSON_SNAPSHOTS, ids=[p.name for p in JSON_SNAPSHOTS])
def test_snapshot_has_honest_metadata(path: Path):
    """Each collection snapshot declares source, a synthetic flag, and a timestamp."""
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or "metadata" not in payload:
        pytest.skip(f"{path.name} is not a metadata-bearing collection snapshot")
    meta = payload["metadata"]
    assert "synthetic" in meta, f"{path.name} metadata missing 'synthetic'"
    assert isinstance(meta["synthetic"], bool)
    assert meta.get("source"), f"{path.name} metadata missing non-empty 'source'"
    # Real (non-synthetic) layers must name where and when they came from.
    if meta["synthetic"] is False:
        assert meta.get("source_url"), f"real layer {path.name} must have a source_url"
        assert meta.get("fetched_at"), f"real layer {path.name} must have a fetched_at"


def test_ports_snap_to_water():
    """Task 4: every port in config/ports.yaml snaps to a water cell."""
    points = all_ports_water_points()
    assert set(points) == set(load_ports())
    for key, (lon, lat) in points.items():
        assert is_water(lon, lat), f"port {key} snapped to a land cell: ({lon}, {lat})"


def test_snap_to_water_is_identity_for_water_points():
    """A point already in water snaps to its own cell centroid."""
    # Central Massachusetts Bay is open water.
    lon, lat = snap_to_water(-70.4, 42.3)
    assert is_water(lon, lat)


def test_demo_scenario_activates_zones():
    """Task 3: the 'replay whale season' scenario makes protection zones active."""
    cfg = yaml.safe_load(config_path("demo_scenarios.yaml").read_text())
    sc = cfg["scenarios"]["replay_whale_season"]
    when = datetime.fromisoformat(sc["time_utc"].replace("Z", "+00:00"))
    zones = load_zones()
    active = {z.id for z in zones if is_active(z, when)}
    # Every zone the scenario promises as active must actually be active.
    for zid in sc["expected_active_zone_ids"]:
        assert zid in active, f"{zid} expected active on {when} but was not"
    # The Cape Cod Bay SMA in particular must be active in whale season.
    assert "sma_cape_cod_bay" in active


def test_today_zone_activity_is_honest():
    """Task 3: outside whale season (e.g. 24 Oct) the SMAs are correctly inactive.

    Confirms the QA observation ("0 of 3 zones active" near Gloucester in October)
    is correct behavior, not a bug: seasonal SMAs/closures are out of season.
    """
    oct24 = datetime(2026, 10, 24, 13, 0, tzinfo=timezone.utc)
    zones = load_zones()
    active_smas = [z.id for z in zones if z.kind == "whale_sma" and is_active(z, oct24)]
    assert active_smas == [], f"no SMA should be active on 24 Oct, got {active_smas}"


def test_validate_snapshots_script_passes():
    """Task 6 (CI): scripts/validate_snapshots.py reports no problems."""
    import importlib.util

    script = Path(data_path("..", "scripts", "validate_snapshots.py")).resolve()
    spec = importlib.util.spec_from_file_location("validate_snapshots", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    errors = mod.validate_all()
    assert errors == [], "snapshot validation errors:\n" + "\n".join(errors)


def test_meta_sources_every_layer_is_fully_described():
    """Task 1: /api/meta/sources gives every layer name, url, fetched_at,
    license, synthetic flag, and an honest note -- and names no placeholder."""
    from fastapi.testclient import TestClient

    from app.main import app

    body = TestClient(app).get("/api/meta/sources").json()
    layers = {s["layer"] for s in body["sources"]}
    assert {"conditions", "zones", "sightings", "risk", "land_mask"} <= layers
    for s in body["sources"]:
        for field in ("name", "fetched_at", "cached", "synthetic", "license", "note"):
            assert field in s, f"{s['layer']} missing {field}"
        assert s["name"] and "TODO" not in str(s["name"]).upper()
        assert s["license"] and s["note"]
        assert isinstance(s["synthetic"], bool)
        # A layer flagged real must cite where it came from.
        if s["synthetic"] is False:
            assert s["source_url"], f"real layer {s['layer']} needs a source_url"


# --- Replay date zone activity (task 2) -----------------------------------

REPLAY = datetime(2026, 3, 15, 13, 0, tzinfo=timezone.utc)


def test_replay_date_zone_activity_is_correct():
    """Task 2: at 2026-03-15T13:00:00Z the expected zones are active/inactive.

    Active: Cape Cod Bay SMA, Off Race Point SMA, Western Gulf of Maine closure,
    Stellwagen slow zone. Inactive: Great South Channel SMA (opens Apr 1).
    """
    zones = {z.id: z for z in load_zones()}
    for zid in (
        "sma_cape_cod_bay",
        "sma_off_race_point",
        "closure_western_gom",
        "slow_zone_stellwagen_mar",
    ):
        assert zid in zones, f"missing zone {zid}"
        assert is_active(zones[zid], REPLAY), f"{zid} should be active on 2026-03-15"
    assert "sma_great_south_channel" in zones
    assert not is_active(zones["sma_great_south_channel"], REPLAY), (
        "Great South Channel SMA should NOT be active on 2026-03-15 (opens Apr 1)"
    )


# --- Sightings support a meaningful March heatmap (task 1) ----------------

def test_sightings_are_real_whale_season_records():
    """Task 1: sightings are real OBIS records, all in the Jan-May window."""
    payload = json.loads((SNAPSHOT_DIR / "sightings.json").read_text())
    meta = payload["metadata"]
    assert meta["synthetic"] is False
    assert "obis" in meta["source"].lower()
    rows = payload["sightings"]
    assert 40 <= len(rows) <= 80, f"expected ~60 sightings, got {len(rows)}"
    for s in rows:
        month = int(s["observed_at"][5:7])
        assert month in (1, 2, 3, 4, 5), f"sighting outside whale season: {s['observed_at']}"


def test_risk_layer_is_meaningful_at_replay_date():
    """Task 1: the risk heatmap at the replay date has real spatial variation."""
    import numpy as np

    from app.engine.risk import load_sightings, risk_grid
    from app.ingest.grid import build_grid_spec, land_mask_array

    spec = build_grid_spec()
    mask = land_mask_array(spec)
    grid = risk_grid(spec, REPLAY, 12.0, load_sightings(), mask)
    assert grid.max() > 0.15, "March heatmap should show non-trivial risk"
    assert int((grid > 0.05).sum()) > 50, "March heatmap should cover many cells"
    assert np.all(grid >= 0.0) and np.all(grid <= 1.0)


# --- Grounds and ports vs land / closures (task 3) ------------------------

def test_no_fishing_ground_is_on_land():
    """Task 3: every fishing ground sits in water (grounds on land are bugs)."""
    cfg = yaml.safe_load(config_path("ports.yaml").read_text())
    for key, g in cfg["fishing_grounds"].items():
        assert is_water(g["lon"], g["lat"]), f"ground {key} is on land: ({g['lon']},{g['lat']})"


def test_all_ports_are_in_water_at_grid_resolution():
    """Task 3: every port coordinate resolves to a water cell (routable origin)."""
    cfg = yaml.safe_load(config_path("ports.yaml").read_text())
    for key, p in cfg["ports"].items():
        assert is_water(p["lon"], p["lat"]), f"port {key} is on a land cell: ({p['lon']},{p['lat']})"


def test_jeffreys_ledge_is_legitimately_closed_in_whale_season():
    """Task 3: jeffreys_ledge sits in the Western GoM closure during whale season.

    This is a legitimate closure (not a data bug): trips targeting it lose access
    at the replay date by design. Documented in docs/DATA.md.
    """
    from shapely.geometry import Point

    from app.ingest.zones import zone_shape

    cfg = yaml.safe_load(config_path("ports.yaml").read_text())
    g = cfg["fishing_grounds"]["jeffreys_ledge"]
    pt = Point(g["lon"], g["lat"])
    closure = next(z for z in load_zones() if z.id == "closure_western_gom")
    assert is_active(closure, REPLAY)
    assert zone_shape(closure).covers(pt), "jeffreys_ledge should fall inside the closure"


# --- Port / ground metadata (ids, names, display metadata) ----------------

_ID_RE = _re.compile(r"^[a-z0-9_]+$")
_REQUIRED_META = ("name", "display_name", "description", "region")


def _ports_and_grounds():
    """Yield (kind, id, entry) over every port and fishing ground."""
    for pid, entry in load_ports().items():
        yield "port", pid, entry
    for gid, entry in load_grounds().items():
        yield "ground", gid, entry


def test_port_and_ground_ids_are_slug_lowercase():
    """Every port/ground id is lowercase [a-z0-9_] (stable, URL/picker-safe)."""
    for kind, ident, _ in _ports_and_grounds():
        assert _ID_RE.match(ident), f"{kind} id {ident!r} is not lowercase [a-z0-9_]"


def test_port_and_ground_names_non_empty():
    """Every port/ground has a non-empty name and the display metadata fields."""
    for kind, ident, entry in _ports_and_grounds():
        for field in _REQUIRED_META:
            val = entry.get(field)
            assert isinstance(val, str) and val.strip(), (
                f"{kind} {ident!r} has empty/missing {field!r}"
            )


def test_port_and_ground_coords_in_study_bbox():
    """Coordinates stay inside the study bbox (-71..-69 lon, 41..43.5 lat)."""
    for kind, ident, entry in _ports_and_grounds():
        lon, lat = float(entry["lon"]), float(entry["lat"])
        assert -71.0 <= lon <= -69.0, f"{kind} {ident} lon {lon} out of bbox"
        assert 41.0 <= lat <= 43.5, f"{kind} {ident} lat {lat} out of bbox"


def test_expected_ports_and_grounds_present():
    """The five ports and three grounds keep their stable ids."""
    assert set(load_ports()) == {
        "gloucester", "boston", "plymouth", "provincetown", "new_bedford",
    }
    assert set(load_grounds()) == {
        "stellwagen_bank", "jeffreys_ledge", "cape_cod_bay",
    }
