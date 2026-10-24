"""Source-URL hygiene (final audit item B).

Fails when any citation/source URL in the API's /api/meta/sources response or in
the bundled snapshot metadata is empty, null, or malformed (missing scheme or
host). This does NOT make a network call — it is a fast, offline structural
check so a dead-shaped link can never ship. (Reachability was verified by hand
with ``curl -sIL`` during the audit; see docs/kiro-evidence/FINAL_AUDIT.md.)
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from app.api.meta import get_sources

_REPO = Path(__file__).resolve().parents[2]
_SNAPSHOTS = _REPO / "data" / "snapshots"


def _is_wellformed(url: str) -> bool:
    """True if ``url`` is a SINGLE, usable http(s) link.

    It must have an http/https scheme and a host, and must NOT contain any
    whitespace or a semicolon — two URLs joined by ' ; ' render as one broken
    <a href> in the Sources panel, so that shape is rejected outright.
    """
    if not isinstance(url, str) or not url:
        return False
    if any(c.isspace() for c in url) or ";" in url:
        return False
    p = urlparse(url)
    return p.scheme in ("http", "https") and bool(p.netloc)


def test_meta_sources_urls_are_wellformed() -> None:
    """Every layer in /api/meta/sources has a non-empty, well-formed source_url.

    ``land_mask`` may legitimately have no URL (a hand-drawn coastline), so a
    null there is allowed; any present URL must still be well-formed.
    """
    sources = get_sources()["sources"]
    assert sources, "meta/sources returned no layers"
    for s in sources:
        url = s.get("source_url")
        if s["layer"] == "land_mask" and not url:
            continue  # hand-drawn; no authoritative URL
        assert url, f"layer {s['layer']} is missing a source_url"
        assert _is_wellformed(url), f"layer {s['layer']} has a malformed source_url: {url!r}"


def _iter_source_urls(obj: object):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "source_url" and v is not None:
                yield v
            else:
                yield from _iter_source_urls(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_source_urls(v)


@pytest.mark.parametrize(
    "name", ["zones.json", "conditions.json", "sightings.json"]
)
def test_snapshot_source_urls_are_wellformed(name: str) -> None:
    """Every non-null source_url in the bundled snapshots is well-formed."""
    path = _SNAPSHOTS / name
    payload = json.loads(path.read_text())
    urls = list(_iter_source_urls(payload))
    for url in urls:
        assert _is_wellformed(url), f"{name} has a malformed source_url: {url!r}"
