"""TEMPORARY whale-risk stub for the /api/layers/risk endpoint.

TODO(Lane A): replace this with the real model in ``backend/app/engine/risk.py``.
The real model (design.md section 5) computes, per cell/time/speed:

    presence(c, month)  -> kernel-smoothed sighting density, 0..1
    recency(c, t)       -> decay over recent nearby sightings
    p_whale(c, t)       -> clip(alpha*presence + (1-alpha)*recency, 0, 1)
    lethality(v)        -> logistic in speed (v50 ~= 11.8 kn, k ~= 2.0)
    risk                -> p_whale * lethality

Parameters must live in ``config/risk.yaml`` (never hardcoded) and the
invariants in .kiro/steering/testing-pbt.md apply (risk in [0,1], monotonic in
speed, 0 on land, sightings never lower risk).

This stub is deliberately simple and deterministic so the endpoint is wired and
demoable now. It is monotonic in speed, bounded [0, 1], and 0 for land cells,
but it is NOT calibrated and MUST NOT appear on a slide. The risk layer response
is flagged ``synthetic: true`` while this stub is in use.
"""
from __future__ import annotations

import math


def lethality(speed_kn: float) -> float:
    """Placeholder vessel-speed lethality, logistic and monotonic in speed.

    Args:
        speed_kn: Planned vessel speed, knots.

    Returns:
        A value in (0, 1). Uncalibrated placeholder (v50=11.8, k=2.0 shape only).
    """
    v50, k = 11.8, 2.0
    return 1.0 / (1.0 + math.exp(-(speed_kn - v50) / k))


def stub_risk(presence: float, speed_kn: float, is_land: bool) -> float:
    """Placeholder per-cell risk = presence * lethality(speed), 0 on land.

    Args:
        presence: Crude whale-presence prior for the cell, 0..1.
        speed_kn: Planned vessel speed, knots.
        is_land: True if the cell is land (risk is always 0 there).

    Returns:
        Risk score clipped to [0, 1]. Placeholder only — see module docstring.
    """
    if is_land:
        return 0.0
    presence = min(max(presence, 0.0), 1.0)
    return min(max(presence * lethality(speed_kn), 0.0), 1.0)
