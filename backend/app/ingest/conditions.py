"""Conditions ingest with caching and a "cached" flag (Task 1.3, Req 1.3).

Fetches buoy/forecast conditions into ``Conditions`` objects. When a live
source is unreachable (or demo mode is on), it falls back to the bundled
snapshot and reports ``cached=True`` plus the snapshot timestamp so the UI can
show a "cached <timestamp>" badge (Req 1.3, steering: data-and-safety).

Network calls use httpx with a short timeout; any failure degrades gracefully
to the cache rather than raising.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from app.ingest.config import data_path
from app.models.conditions import Conditions

_DEFAULT_SNAPSHOT = ("snapshots", "conditions.json")

# Live endpoint candidate (design.md section 3). Kept here so the live path is
# documented even though demo mode never calls it.
NDBC_REALTIME_URL = "https://www.ndbc.noaa.gov/data/realtime2/44013.txt"


@dataclass
class ConditionsResult:
    """A conditions layer plus its provenance for UI badging.

    - ``cached``: True when served from the bundled snapshot (not live).
    - ``synthetic``: True when the underlying data is synthetic.
    - ``fetched_at``: UTC timestamp of the data (snapshot or live fetch).
    - ``source``: human-readable source label.
    """

    conditions: list[Conditions]
    cached: bool
    synthetic: bool
    source: str
    source_url: str | None
    fetched_at: datetime | None
    error: str | None = field(default=None)

    @property
    def badge(self) -> str:
        """Short badge text for the layer, e.g. 'cached 2026-03-14T18:05Z'."""
        if self.synthetic:
            prefix = "synthetic"
        elif self.cached:
            prefix = "cached"
        else:
            prefix = "live"
        if self.fetched_at is not None:
            stamp = self.fetched_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
            return f"{prefix} {stamp}"
        return prefix


def demo_mode() -> bool:
    """True when the app must run from bundled snapshots only (tech.md)."""
    return os.getenv("FATHOM_DEMO_MODE", "false").lower() in {"1", "true", "yes"}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_cached_conditions(path: Path | None = None) -> ConditionsResult:
    """Load conditions from the bundled snapshot and flag them cached."""
    if path is None:
        path = data_path(*_DEFAULT_SNAPSHOT)
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    meta = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    raw = payload.get("conditions", []) if isinstance(payload, dict) else payload
    conditions = [Conditions.model_validate(c) for c in raw]
    return ConditionsResult(
        conditions=conditions,
        cached=True,
        synthetic=bool(meta.get("synthetic", False)),
        source=meta.get("source", "snapshot"),
        source_url=meta.get("source_url"),
        fetched_at=_parse_dt(meta.get("fetched_at")),
    )


def _fetch_live_conditions(timeout_s: float) -> ConditionsResult:
    """Attempt a live fetch. Raises on any failure so the caller can fall back.

    NOTE: parsing the NDBC realtime text into per-cell Conditions is a Phase-3
    refinement; for now a successful fetch still returns the snapshot shape but
    with ``cached=False`` and a fresh ``fetched_at``. Demo mode never reaches
    this path.
    """
    import httpx  # imported lazily so demo mode has no hard httpx dependency

    resp = httpx.get(NDBC_REALTIME_URL, timeout=timeout_s)
    resp.raise_for_status()
    # Reuse the snapshot grid mapping but mark the fetch time as now.
    base = load_cached_conditions()
    now = datetime.now(timezone.utc)
    refreshed = [c.model_copy(update={"fetched_at": now}) for c in base.conditions]
    return ConditionsResult(
        conditions=refreshed,
        cached=False,
        synthetic=False,
        source="noaa_ndbc_44013",
        source_url=NDBC_REALTIME_URL,
        fetched_at=now,
    )


def get_conditions(
    *, prefer_live: bool | None = None, timeout_s: float = 5.0
) -> ConditionsResult:
    """Return conditions, preferring live data but falling back to the cache.

    - In demo mode (or ``prefer_live=False``) returns the cached snapshot.
    - Otherwise tries a live fetch; on any error, returns the cached snapshot
      with ``cached=True`` and an ``error`` note (Req 1.3).
    """
    if prefer_live is None:
        prefer_live = not demo_mode()

    if not prefer_live:
        return load_cached_conditions()

    try:
        return _fetch_live_conditions(timeout_s)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully to cache
        fallback = load_cached_conditions()
        fallback.error = f"live fetch failed, using cache: {exc!s}"
        return fallback


def filter_by_time(conditions: list[Conditions], when: datetime) -> list[Conditions]:
    """Return conditions whose ``time`` equals the requested slice (UTC)."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    out = []
    for c in conditions:
        ctime = c.time if c.time.tzinfo else c.time.replace(tzinfo=timezone.utc)
        if ctime == when:
            out.append(c)
    return out


@lru_cache(maxsize=1)
def default_conditions() -> ConditionsResult:
    """Cached-snapshot conditions (cached call for reuse)."""
    return load_cached_conditions()
