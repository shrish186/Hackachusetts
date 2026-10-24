"""Snapshot loading + provenance helpers for the layer endpoints.

Lane B owns the API layer. This module reads bundled demo data from
``data/snapshots/`` and attaches the provenance every response must carry:
``source``, ``fetched_at`` (UTC), and a ``cached`` / ``synthetic`` flag
(tech.md + data-and-safety.md steering rules).

Snapshot resolution, in order:
  1. A named collection file, e.g. ``data/snapshots/conditions.json`` — a JSON
     list of records. This is what the Lane A ingest jobs will write.
  2. The single-record example under ``data/snapshots/examples/<name>.example.json``
     (wrapped in a 1-element list). These ship today so the API is demoable
     before real ingest exists; they are flagged ``synthetic`` / not ``cached``.

``FATHOM_DEMO_MODE`` forces snapshot-only reads (no live network). Since this
skeleton has no live sources wired up yet, we always read snapshots; the flag is
still surfaced so the UI can badge "Demo data".
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# backend/app/api/_snapshots.py -> repo root is four parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = _REPO_ROOT / "data" / "snapshots"
EXAMPLE_DIR = SNAPSHOT_DIR / "examples"


def demo_mode() -> bool:
    """Return True when the app should run from bundled snapshots only."""
    return os.getenv("FATHOM_DEMO_MODE", "false").lower() in {"1", "true", "yes"}


def _file_mtime_utc(path: Path) -> datetime:
    """Return a file's modification time as a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


class SnapshotResult:
    """A loaded snapshot plus the provenance the API must echo to callers.

    Attributes:
        records: The list of raw record dicts loaded from disk.
        source: Human-readable source label (dataset name or 'synthetic').
        fetched_at: UTC time the snapshot was produced/cached (file mtime).
        cached: True when served from a real cached collection snapshot.
        synthetic: True when served from the bundled example seed (not real).
    """

    def __init__(
        self,
        records: list[dict[str, Any]],
        *,
        source: str,
        fetched_at: datetime | None,
        cached: bool,
        synthetic: bool,
    ) -> None:
        self.records = records
        self.source = source
        self.fetched_at = fetched_at
        self.cached = cached
        self.synthetic = synthetic

    def provenance(self) -> dict[str, Any]:
        """The provenance block attached to every layer response."""
        return {
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "cached": self.cached,
            "synthetic": self.synthetic,
            "demo_mode": demo_mode(),
        }


def _example_candidates(name: str) -> list[str]:
    """Example filename stems to try for a collection name.

    Lane A's collection snapshots are plural (``zones.json``) but the bundled
    example seeds are singular (``zone.example.json``). Try the exact name first,
    then a naive de-pluralized form, so both resolve.
    """
    candidates = [name]
    if name.endswith("s"):
        candidates.append(name[:-1])
    return candidates


def load_snapshot(name: str) -> SnapshotResult:
    """Load a named snapshot collection, falling back to the bundled example.

    Args:
        name: Logical collection name, e.g. "conditions", "zones", "sightings".

    Returns:
        A :class:`SnapshotResult` with the records and their provenance. If no
        file is found at all, returns an empty result flagged synthetic so the
        caller still emits a well-formed, clearly-unsourced response.
    """
    collection = SNAPSHOT_DIR / f"{name}.json"
    if collection.exists():
        data = json.loads(collection.read_text())
        # Lane A snapshots are either a bare JSON list, or a dict of the form
        # {"metadata": {...}, "<name>": [...]} where metadata carries honest
        # provenance (source/source_url/fetched_at/synthetic). Respect that
        # metadata instead of assuming every collection file is real data.
        if isinstance(data, dict):
            meta = data.get("metadata", {})
            records = None
            for key, value in data.items():
                if key != "metadata" and isinstance(value, list):
                    records = value
                    break
            if records is None:
                records = [data]
            synthetic = bool(meta.get("synthetic", False))
            parsed_fetched = None
            if meta.get("fetched_at"):
                try:
                    parsed_fetched = datetime.fromisoformat(
                        str(meta["fetched_at"]).replace("Z", "+00:00")
                    )
                except ValueError:
                    parsed_fetched = None
            return SnapshotResult(
                records,
                source=meta.get("source") or f"fathom snapshot: {name}.json",
                fetched_at=parsed_fetched or _file_mtime_utc(collection),
                # A hand-authored (synthetic) snapshot is not real cached data.
                cached=not synthetic,
                synthetic=synthetic,
            )
        records = data if isinstance(data, list) else [data]
        return SnapshotResult(
            records,
            source=f"fathom snapshot: {name}.json",
            fetched_at=_file_mtime_utc(collection),
            cached=True,
            synthetic=False,
        )

    for stem in _example_candidates(name):
        example = EXAMPLE_DIR / f"{stem}.example.json"
        if example.exists():
            data = json.loads(example.read_text())
            records = data if isinstance(data, list) else [data]
            return SnapshotResult(
                records,
                source=f"synthetic example seed: {stem}.example.json",
                fetched_at=_file_mtime_utc(example),
                cached=False,
                synthetic=True,
            )

    return SnapshotResult(
        [],
        source="synthetic (no snapshot available)",
        fetched_at=None,
        cached=False,
        synthetic=True,
    )


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float] | None) -> bool:
    """Return True if (lon, lat) is inside bbox (min_lon, min_lat, max_lon, max_lat).

    A ``None`` bbox matches everything (no spatial filter requested).
    """
    if bbox is None:
        return True
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    """Parse a 'min_lon,min_lat,max_lon,max_lat' query string into a tuple.

    Returns None when no bbox is supplied. Raises ValueError on malformed input
    (the endpoint converts this into an HTTP 422).
    """
    if bbox is None:
        return None
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be 'min_lon,min_lat,max_lon,max_lat'")
    min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    if min_lon > max_lon or min_lat > max_lat:
        raise ValueError("bbox min must not exceed max")
    return (min_lon, min_lat, max_lon, max_lat)
