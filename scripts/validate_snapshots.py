#!/usr/bin/env python3
"""Validate Fathom data snapshots: schema, bounds, ranges, timestamps (Lane A).

Run standalone (``python scripts/validate_snapshots.py``) or from the CI test
``backend/tests/test_data_snapshots.py``-adjacent runner. Exits non-zero and
prints every problem if any snapshot is malformed, out of the study bbox, has an
out-of-range value, a bad timestamp, or a leftover placeholder string.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots"

# Study-area bbox (mirrors config/study_area.yaml).
BBOX = (-71.0, 41.0, -69.0, 43.5)


def _iso_ok(value) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _in_bbox(lon, lat) -> bool:
    return BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]


def _all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_strings(v)


def validate_metadata(name: str, meta: dict, errors: list[str]) -> None:
    if "synthetic" not in meta or not isinstance(meta["synthetic"], bool):
        errors.append(f"{name}: metadata.synthetic missing or not a bool")
    if not meta.get("source"):
        errors.append(f"{name}: metadata.source is empty")
    if meta.get("fetched_at") is not None and not _iso_ok(meta["fetched_at"]):
        errors.append(f"{name}: metadata.fetched_at is not ISO-8601: {meta.get('fetched_at')!r}")
    if meta.get("synthetic") is False:
        if not meta.get("source_url"):
            errors.append(f"{name}: real layer must have metadata.source_url")
        if not _iso_ok(meta.get("fetched_at")):
            errors.append(f"{name}: real layer must have a valid metadata.fetched_at")


def validate_conditions(name: str, payload: dict, errors: list[str]) -> None:
    for i, c in enumerate(payload.get("conditions", [])):
        where = f"{name}[conditions#{i}]"
        if not isinstance(c.get("wave_m"), (int, float)) or not (0 <= c["wave_m"] <= 30):
            errors.append(f"{where}: wave_m out of range [0,30]: {c.get('wave_m')}")
        if not isinstance(c.get("wind_kn"), (int, float)) or not (0 <= c["wind_kn"] <= 200):
            errors.append(f"{where}: wind_kn out of range [0,200]: {c.get('wind_kn')}")
        if c.get("sst_c") is not None and not (-5 <= c["sst_c"] <= 40):
            errors.append(f"{where}: sst_c out of range [-5,40]: {c.get('sst_c')}")
        if not _iso_ok(c.get("time")):
            errors.append(f"{where}: bad time {c.get('time')!r}")


def validate_sightings(name: str, payload: dict, errors: list[str]) -> None:
    for i, s in enumerate(payload.get("sightings", [])):
        where = f"{name}[sightings#{i}]"
        lon, lat = s.get("lon"), s.get("lat")
        if lon is None or lat is None or not _in_bbox(lon, lat):
            errors.append(f"{where}: ({lon},{lat}) outside study bbox {BBOX}")
        if not isinstance(s.get("count"), int) or s["count"] < 0:
            errors.append(f"{where}: count must be a non-negative int, got {s.get('count')}")
        if not _iso_ok(s.get("observed_at")):
            errors.append(f"{where}: bad observed_at {s.get('observed_at')!r}")


def validate_zones(name: str, payload: dict, errors: list[str]) -> None:
    for i, z in enumerate(payload.get("zones", [])):
        where = f"{name}[zones#{i}:{z.get('id')}]"
        for field in ("id", "name", "kind", "geometry"):
            if not z.get(field):
                errors.append(f"{where}: missing {field}")
        if not z.get("source_url") and not z.get("synthetic"):
            errors.append(f"{where}: no source_url but synthetic is not True")
        if z.get("speed_limit_kn") is not None and not (0 < z["speed_limit_kn"] <= 40):
            errors.append(f"{where}: speed_limit_kn out of range (0,40]: {z['speed_limit_kn']}")
        for key in ("active_from", "active_to"):
            if z.get(key) is not None and not _iso_ok(z[key]):
                errors.append(f"{where}: {key} not ISO-8601: {z[key]!r}")
        af, at = z.get("active_from"), z.get("active_to")
        if _iso_ok(af) and _iso_ok(at):
            if datetime.fromisoformat(at.replace("Z", "+00:00")) < datetime.fromisoformat(af.replace("Z", "+00:00")):
                errors.append(f"{where}: active_to earlier than active_from")


def validate_file(path: Path, errors: list[str]) -> None:
    name = path.name
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"{name}: invalid JSON: {exc}")
        return

    for s in _all_strings(payload):
        if "TODO" in s.upper():
            errors.append(f"{name}: placeholder string found: {s!r}")

    if not isinstance(payload, dict):
        return  # example files may be bare objects; nothing more to check
    if "metadata" in payload:
        validate_metadata(name, payload["metadata"], errors)
    if "conditions" in payload:
        validate_conditions(name, payload, errors)
    if "sightings" in payload:
        validate_sightings(name, payload, errors)
    if "zones" in payload:
        validate_zones(name, payload, errors)


def validate_all() -> list[str]:
    """Validate every *.json in data/snapshots/. Returns a list of problems."""
    errors: list[str] = []
    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        validate_file(path, errors)
    return errors


def main() -> int:
    errors = validate_all()
    if errors:
        print("SNAPSHOT VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: all snapshots in {SNAPSHOT_DIR} pass schema/bounds/range/timestamp checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
