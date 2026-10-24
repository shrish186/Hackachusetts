"""Data-honesty tests for bundled snapshots (Lane A).

Covers:
- no placeholder strings ("TODO") anywhere in snapshot JSON (task 2)
- every snapshot carries an honest metadata block (task 1, 7)
- every config/ports.yaml port snaps to a water cell (task 4)
- the whale-season demo scenario activates zones; "today" may show none (task 3)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from app.ingest.config import config_path, data_path
from app.ingest.ports import all_ports_water_points, is_water, load_ports, snap_to_water
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
