#!/usr/bin/env python3
"""Precompute the 3 preset what-if scenarios into data/snapshots/sim_results.json.

The live A* router is accurate but slow: running all preset scenarios over the
200-trip fleet on the production box took >20 s and returned a 504 (the critical
bug). Presets never change between requests, so we compute them once at build
time and commit the result. ``POST /api/sim/run`` then serves the preset from
this snapshot in well under 300 ms (JSON read + lookup), keeping the live code
path only for user-drawn custom polygons.

Run from the repo root:

    python scripts/precompute_sim.py

This imports the backend app and the simulator exactly as the API does, so the
committed JSON has the identical response shape (baseline, options with
``deltas_pct`` and ``on_frontier``, trilingual summaries, fleet/labels). It adds
``provenance`` and ``computed_at`` so the API can advertise the result as
precomputed, and surfaces the Pareto points the frontend reads.

Deterministic: the fleet is seeded and the router is deterministic, so re-running
this script on the same code + config reproduces the same numbers.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Run offline from bundled snapshots, like the deployed app.
import os

os.environ.setdefault("FATHOM_DEMO_MODE", "true")
os.environ.setdefault("FATHOM_ROOT", str(_REPO_ROOT))

from app.api.sim import _current_zones
from app.engine.simulator import Simulator, preloaded_scenarios

OUT_PATH = _REPO_ROOT / "data" / "snapshots" / "sim_results.json"

#: Bump when the response shape changes so a stale snapshot can be detected.
SCHEMA_VERSION = 1


def build() -> dict:
    """Run every preset against the baseline and return the committed payload."""
    sim = Simulator(current_zones=_current_zones())
    result = sim.run_all(preloaded_scenarios())

    computed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    result["computed_at"] = computed_at
    result["schema_version"] = SCHEMA_VERSION
    result["provenance"] = {
        "precomputed": True,
        "computed_at": computed_at,
        "script": "scripts/precompute_sim.py",
        "router": result.get("router"),
        "fleet": result.get("fleet"),
        "synthetic": True,
        "note": (
            "Preset scenarios precomputed at build time from bundled synthetic "
            "data; served without the live A* router so Manager mode is instant."
        ),
    }
    return result


def main() -> int:
    payload = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_opts = len(payload.get("options", []))
    print(f"wrote {OUT_PATH.relative_to(_REPO_ROOT)}: {n_opts} preset options, computed_at={payload['computed_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
