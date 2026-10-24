"""Policy what-if simulator (Lane D, design.md section 8, Req 6).

Routes a representative **fleet** of trips under current zones (the *baseline*),
then re-routes the same fleet with one or more *candidate* zones added (a
*scenario*), and reports the trade-off: how much whale risk is removed vs. how
much it costs the fleet in steaming hours, fuel, and access to fishing grounds
(the *effort proxy* — an ESTIMATE of activity, never catch or revenue).

Design decisions (hard deadline, noted in docs/kiro-evidence/LOG.md):

* **Router is injected.** The real engine exposes
  ``route_one(origin_lonlat, dest_lonlat, speed_kn, vessel, when, risk_pref,
  extra_zones=None)`` in ``app.engine.routing`` (Shrish). We import it if it is
  present; otherwise we fall back to a deterministic synthetic router with the
  same signature so the simulator, its API, and its tests all work *now* and
  pick up the real router automatically once it lands. Tests inject a fake.
* **Fleet is synthetic.** No ``config/ports.yaml`` exists yet, so the fleet is
  generated deterministically (seeded) from a hardcoded Massachusetts port list
  and a set of fishing grounds. Every fleet record is flagged ``synthetic:true``
  and uses anonymized ids (data-and-safety rule).
* **Baseline is cached** so a scenario run is a single re-route pass; target
  runtime is well under 20 s for ~200 trips.

Everything here is deterministic Python (no LLM).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Router interface + fallback
# ---------------------------------------------------------------------------

LonLat = tuple[float, float]


class RouteResult(Protocol):
    """Minimal shape the simulator needs from a routed trip.

    The real ``route_one`` may return a richer object; we read these attributes
    (or dict keys) defensively via :func:`_route_field`.
    """

    eta_hours: float
    fuel_est_l: float
    risk_exposure: float


# Signature Shrish's router must satisfy (design.md section 6 / task brief).
RouterFn = Callable[..., Any]


def _route_field(result: Any, name: str, default: float = 0.0) -> float:
    """Read ``name`` from a route result that may be an object or a dict."""
    if result is None:
        return default
    if isinstance(result, dict):
        val = result.get(name, default)
    else:
        val = getattr(result, name, default)
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _try_import_real_router() -> RouterFn | None:
    """Return the real ``route_one`` if Shrish's routing module is importable."""
    try:  # pragma: no cover - depends on cross-lane code landing
        from app.engine.routing import route_one  # type: ignore

        return route_one
    except Exception:
        return None


def _stable_unit(*parts: Any) -> float:
    """Deterministic pseudo-random value in [0, 1) from the given parts.

    Uses a hash so the synthetic router/fleet are reproducible across runs and
    machines (no global RNG state).
    """
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _haversine_nm(a: LonLat, b: LonLat) -> float:
    """Great-circle distance between two lon/lat points, in nautical miles."""
    import math

    r_km = 6371.0088
    lon1, lat1 = a
    lon2, lat2 = b
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    km = 2 * r_km * math.asin(math.sqrt(h))
    return km / 1.852


def _point_in_ring(pt: LonLat, ring: Sequence[Sequence[float]]) -> bool:
    """Ray-casting point-in-polygon test for a single GeoJSON ring."""
    x, y = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_zone(pt: LonLat, zone: dict) -> bool:
    """True if point is inside a zone's GeoJSON Polygon (outer ring)."""
    geom = zone.get("geometry", zone)
    if geom.get("type") != "Polygon":
        return False
    coords = geom.get("coordinates") or []
    if not coords:
        return False
    return _point_in_ring(pt, coords[0])


# Per-vessel fuel burn (liters per nautical mile) — clearly an ESTIMATE.
# Replace with config/vessels.yaml when it exists.
_VESSEL_BURN_L_PER_NM: dict[str, float] = {
    "small_boat": 3.0,
    "mid_trawler": 9.0,
    "scalloper": 14.0,
}


def synthetic_route_one(
    origin_lonlat: LonLat,
    dest_lonlat: LonLat,
    speed_kn: float,
    vessel: str,
    when: datetime,
    risk_pref: float,
    extra_zones: list[dict] | None = None,
) -> dict[str, float]:
    """Deterministic fallback router matching ``route_one``'s signature.

    Produces a plausible straight-line-ish trip whose cost rises when the
    destination (or midpoint) falls inside a prohibited/added zone: entering a
    prohibited zone forces a detour (extra distance + hours), and risk exposure
    scales with speed and distance. This is a STAND-IN for Shrish's A* router so
    the simulator is runnable now; it is not calibrated.
    """
    extra_zones = extra_zones or []
    dist_nm = max(_haversine_nm(origin_lonlat, dest_lonlat), 0.1)

    midpoint = (
        (origin_lonlat[0] + dest_lonlat[0]) / 2.0,
        (origin_lonlat[1] + dest_lonlat[1]) / 2.0,
    )

    # Detour factor: each prohibited zone the direct line "hits" adds distance.
    detour = 1.0
    speed_cap = speed_kn
    for z in extra_zones:
        hit = _point_in_zone(dest_lonlat, z) or _point_in_zone(midpoint, z)
        if not hit:
            continue
        if z.get("prohibited"):
            # Route around it: more distance, weighted by how safe the user wants.
            detour += 0.25 + 0.25 * risk_pref
        limit = z.get("speed_limit_kn")
        if limit:
            speed_cap = min(speed_cap, float(limit))

    eff_speed = max(speed_cap, 0.1)
    eta_hours = (dist_nm * detour) / eff_speed
    burn = _VESSEL_BURN_L_PER_NM.get(vessel, 8.0)
    fuel_est_l = dist_nm * detour * burn

    # Risk exposure: baseline risk along the path * hours, reduced if a slow-zone
    # cap lowered the speed, and reduced if the route detoured around a zone.
    base_risk = 0.15 + 0.5 * _stable_unit(origin_lonlat, dest_lonlat, when.date())
    speed_factor = eff_speed / max(speed_kn, 0.1)  # slower => less lethal
    avoided = 0.6 if detour > 1.0 else 1.0  # detouring avoids the hot cell
    risk_exposure = base_risk * speed_factor * avoided * eta_hours

    return {
        "eta_hours": round(eta_hours, 4),
        "fuel_est_l": round(fuel_est_l, 2),
        "risk_exposure": round(risk_exposure, 5),
        "speed_kn_effective": round(eff_speed, 2),
    }


# ---------------------------------------------------------------------------
# Fleet (synthetic, deterministic, anonymized)
# ---------------------------------------------------------------------------

# Hardcoded Massachusetts ports (no config/ports.yaml yet). lon, lat.
_PORTS: list[tuple[str, LonLat]] = [
    ("Gloucester", (-70.662, 42.610)),
    ("New Bedford", (-70.934, 41.635)),
    ("Provincetown", (-70.183, 42.053)),
    ("Scituate", (-70.726, 42.199)),
    ("Plymouth", (-70.662, 41.958)),
]

# Fishing grounds in the study area. lon, lat.
_GROUNDS: list[tuple[str, LonLat]] = [
    ("Stellwagen Bank", (-70.25, 42.35)),
    ("Jeffreys Ledge", (-70.25, 42.95)),
    ("Cape Cod Bay", (-70.30, 41.90)),
    ("Western Gulf of Maine", (-69.95, 42.85)),
]

_VESSELS = ["small_boat", "mid_trawler", "scalloper"]


@dataclass(frozen=True)
class FleetTrip:
    """One synthetic, anonymized fleet trip (data-and-safety: no real identity)."""

    trip_id: str
    origin: LonLat
    dest: LonLat
    vessel: str
    cruise_kn: float
    risk_pref: float
    synthetic: bool = True


def _try_anant_fleet(size: int) -> list[FleetTrip] | None:
    """Adapt Anant's real fleet (``engine.fleet.build_fleet``) if available.

    Anant's ``Trip`` carries ``origin_lon/lat``, ``target_lon/lat``, ``vessel``
    and ``cruise_kn``. We project it onto our :class:`FleetTrip`. Returns None if
    the fleet module / its config (ports.yaml, vessels.yaml) is not usable, so
    the deterministic in-module fallback can take over.
    """
    try:  # pragma: no cover - depends on cross-lane config being present
        from app.engine.fleet import build_fleet

        raw = build_fleet(n=size)
        if not raw:
            return None
        trips: list[FleetTrip] = []
        for i, t in enumerate(raw):
            trips.append(
                FleetTrip(
                    trip_id=getattr(t, "id", f"synthetic-{i:04d}"),
                    origin=(float(t.origin_lon), float(t.origin_lat)),
                    dest=(float(t.target_lon), float(t.target_lat)),
                    vessel=str(t.vessel),
                    cruise_kn=float(t.cruise_kn),
                    # Anant's Trip has no risk preference; sweep deterministically.
                    risk_pref=round(_stable_unit("anant-risk", i), 2),
                )
            )
        return trips
    except Exception:
        return None


def build_synthetic_fleet(size: int = 200, seed: str = "fathom-fleet-v1") -> list[FleetTrip]:
    """Build the fleet: prefer Anant's real builder, else a seeded fallback.

    Both paths are deterministic, anonymized, and flagged synthetic. The
    fallback is used only when ``engine.fleet`` / its config is unavailable.
    """
    anant = _try_anant_fleet(size)
    if anant:
        return anant
    trips: list[FleetTrip] = []
    for i in range(size):
        u = lambda tag: _stable_unit(seed, i, tag)
        _, origin = _PORTS[int(u("port") * len(_PORTS)) % len(_PORTS)]
        _, dest = _GROUNDS[int(u("ground") * len(_GROUNDS)) % len(_GROUNDS)]
        vessel = _VESSELS[int(u("vessel") * len(_VESSELS)) % len(_VESSELS)]
        cruise = round(8.0 + u("speed") * 10.0, 1)  # 8..18 kn
        risk_pref = round(u("risk"), 2)
        trips.append(
            FleetTrip(
                trip_id=f"synthetic-{i:04d}",
                origin=origin,
                dest=dest,
                vessel=vessel,
                cruise_kn=cruise,
                risk_pref=risk_pref,
            )
        )
    return trips


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """A candidate policy: zero or more added zones, with metadata."""

    id: str
    name: str
    description: str
    extra_zones: list[dict]


def _rect_polygon(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict:
    """A closed GeoJSON Polygon rectangle."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat],
            [min_lon, max_lat], [min_lon, min_lat],
        ]],
    }


def preloaded_scenarios() -> list[Scenario]:
    """The three preloaded what-if scenarios (design.md section 8, task brief)."""
    return [
        Scenario(
            id="extend_closure_east",
            name="Extend whale closure east",
            description="Extend the Western Gulf of Maine closure ~20 nm east (full no-entry).",
            extra_zones=[{
                "id": "cand_extend_closure_east",
                "name": "Closure extension (east)",
                "kind": "fishing_closure",
                "geometry": _rect_polygon(-69.7, 42.6, -69.3, 43.1),
                "prohibited": True,
                "speed_limit_kn": None,
                "synthetic": True,
            }],
        ),
        Scenario(
            id="dynamic_zone_sightings",
            name="Dynamic zone around recent sightings",
            description="A smaller dynamic no-entry zone placed over the latest sighting cluster.",
            extra_zones=[{
                "id": "cand_dynamic_sightings",
                "name": "Dynamic sighting zone",
                "kind": "slow_zone",
                "geometry": _rect_polygon(-70.35, 42.25, -70.1, 42.5),
                "prohibited": True,
                "speed_limit_kn": None,
                "synthetic": True,
            }],
        ),
        Scenario(
            id="seasonal_speed_limit",
            name="Seasonal 10-knot speed limit (instead of closure)",
            description="A broad 10 kn speed cap over the approaches rather than a closure.",
            extra_zones=[{
                "id": "cand_seasonal_speed_limit",
                "name": "Seasonal 10 kn speed area",
                "kind": "whale_sma",
                "geometry": _rect_polygon(-70.5, 42.0, -69.8, 43.0),
                "prohibited": False,
                "speed_limit_kn": 10.0,
                "synthetic": True,
            }],
        ),
    ]


# ---------------------------------------------------------------------------
# Totals, deltas, Pareto, summaries
# ---------------------------------------------------------------------------


@dataclass
class FleetTotals:
    """Aggregate fleet outcome for one routing pass."""

    risk_exposure: float = 0.0
    steaming_hours: float = 0.0
    fuel_l: float = 0.0
    effort_access: float = 0.0  # ESTIMATE of fishing activity, not revenue
    trips: int = 0
    access_lost: int = 0  # trips whose target ground a candidate closure removed

    def as_dict(self) -> dict[str, float | int]:
        return {
            "risk_exposure": round(self.risk_exposure, 4),
            "steaming_hours": round(self.steaming_hours, 2),
            "fuel_l": round(self.fuel_l, 1),
            "effort_access": round(self.effort_access, 4),
            "trips": self.trips,
            "access_lost": self.access_lost,
        }


def _ground_blocked(trip: FleetTrip, extra_zones: list[dict] | None) -> bool:
    """True if a prohibited candidate zone covers this trip's target ground.

    "Access lost" (Req 6, task 4): when a candidate closure sits on top of a
    fishing ground, the honest outcome is that the ground is unreachable, not
    that the fleet relocates to another ground. We detect it by testing the
    trip's destination (the ground) against each prohibited candidate zone.
    """
    for z in extra_zones or []:
        if z.get("prohibited") and _point_in_zone(trip.dest, z):
            return True
    return False


def _route_fleet(
    fleet: Sequence[FleetTrip],
    router: RouterFn,
    when: datetime,
    extra_zones: list[dict] | None,
) -> FleetTotals:
    """Route every fleet trip once and aggregate the totals.

    Trips whose target ground is closed by a prohibited candidate zone are
    counted as ``access_lost`` (the ground is unreachable) instead of being
    relocated — their effort access contribution is zero and they are not
    re-routed elsewhere.
    """
    totals = FleetTotals()
    for trip in fleet:
        if _ground_blocked(trip, extra_zones):
            # Ground closed: report lost access; no relocation, no phantom route.
            totals.access_lost += 1
            totals.trips += 1
            continue
        res = router(
            trip.origin,
            trip.dest,
            trip.cruise_kn,
            trip.vessel,
            when,
            trip.risk_pref,
            extra_zones=extra_zones or None,
        )
        eta = _route_field(res, "eta_hours")
        fuel = _route_field(res, "fuel_est_l")
        risk = _route_field(res, "risk_exposure")
        # Effort access proxy: a reachable trip contributes inverse-time access;
        # a prohibitively long detour (zone blocks the ground) reduces access.
        access = 1.0 / (1.0 + eta) if eta > 0 else 0.0
        totals.risk_exposure += risk
        totals.steaming_hours += eta
        totals.fuel_l += fuel
        totals.effort_access += access
        totals.trips += 1
    return totals


def _pct_delta(baseline: float, scenario: float) -> float:
    """Percent change scenario-vs-baseline; 0 when baseline is 0."""
    if baseline == 0:
        return 0.0
    return round((scenario - baseline) / baseline * 100.0, 1)


@dataclass
class OptionResult:
    """One scenario's outcome relative to the baseline."""

    scenario_id: str
    name: str
    description: str
    totals: FleetTotals
    delta_risk_pct: float
    delta_hours_pct: float
    delta_fuel_pct: float
    delta_effort_access_pct: float
    on_frontier: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "totals": self.totals.as_dict(),
            "deltas_pct": {
                "risk": self.delta_risk_pct,
                "hours": self.delta_hours_pct,
                "fuel": self.delta_fuel_pct,
                "effort_access": self.delta_effort_access_pct,
            },
            "cost_breakdown": {
                # Trips whose target ground a candidate closure removed entirely
                # (reported as lost access, not relocated — task 4).
                "access_lost_trips": self.totals.access_lost,
                "steaming_hours": self.totals.steaming_hours,
                "fuel_l": self.totals.fuel_l,
            },
            "on_frontier": self.on_frontier,
        }


def _mark_pareto_frontier(options: list[OptionResult]) -> None:
    """Flag non-dominated options on the (risk reduced, livelihood cost) axes.

    We want to MINIMIZE both objectives:
      * ``x`` = delta_risk_pct (more negative = more risk removed = better),
      * ``y`` = -delta_effort_access_pct (loss of access; smaller loss better).
    Option A dominates B iff A is <= B on both and strictly < on at least one.
    An option is on the frontier if no other option dominates it.
    """
    pts = [(o.delta_risk_pct, -o.delta_effort_access_pct) for o in options]
    for i, oi in enumerate(options):
        xi, yi = pts[i]
        dominated = False
        for j, _ in enumerate(options):
            if i == j:
                continue
            xj, yj = pts[j]
            if (xj <= xi and yj <= yi) and (xj < xi or yj < yi):
                dominated = True
                break
        oi.on_frontier = not dominated


def _pareto_points(options: list[OptionResult]) -> list[dict[str, Any]]:
    """Explicit trade-off points for the frontend chart (API_CONTRACT.md).

    Matches ``frontend/src/manager/TradeoffChart.tsx``:
      * ``risk_reduced`` = -delta_risk_pct  (higher = more whale risk removed),
      * ``fleet_cost``   = (delta_hours_pct + -delta_effort_access_pct) / 2
        (higher = costlier for the fleet).
    ``on_frontier`` marks the efficient (non-dominated) options.
    """
    pts = []
    for o in options:
        pts.append({
            "scenario_id": o.scenario_id,
            "name": o.name,
            "risk_reduced": round(-o.delta_risk_pct, 2),
            "fleet_cost": round((o.delta_hours_pct + -o.delta_effort_access_pct) / 2.0, 2),
            "on_frontier": o.on_frontier,
        })
    return pts


def baseline_access_explanation(access_lost: int, total_trips: int) -> dict[str, str]:
    """Plain-language note on baseline access loss, in en/pt/es (identical numbers).

    Even before any new scenario, some fleet trips target grounds that sit
    inside today's *already-active* closed zones (notably the Western Gulf of
    Maine Seasonal Closure and the Vineyard Wind construction exclusion). The
    router does not relocate those trips — it reports them as lost access
    (confirmed with Shrish's routing finding in docs/API_CONTRACT.md). This
    explains why the baseline shows ``access_lost`` > 0 with no scenario applied.

    Exposed as a module function so the API layer can attach the same text to a
    precomputed preset result without re-running the simulator.
    """
    n = access_lost
    total = total_trips
    return {
        "en": (
            f"Before any new rule, {n} of {total} fleet trips already target "
            f"fishing grounds inside today's active closed zones (mainly the "
            f"Western Gulf of Maine closure and the Vineyard Wind construction "
            f"exclusion), so they are counted as lost access, not re-routed."
        ),
        "pt": (
            f"Antes de qualquer nova regra, {n} de {total} viagens da frota já "
            f"têm como destino pesqueiros dentro das zonas fechadas ativas de "
            f"hoje (principalmente o fecho do oeste do Golfo do Maine e a "
            f"exclusão de construção do Vineyard Wind), por isso são contadas "
            f"como acesso perdido, e não realocadas."
        ),
        "es": (
            f"Antes de cualquier nueva norma, {n} de {total} viajes de la flota "
            f"ya se dirigen a caladeros dentro de las zonas cerradas activas de "
            f"hoy (sobre todo el cierre del oeste del Golfo de Maine y la "
            f"exclusión de construcción de Vineyard Wind), por lo que se cuentan "
            f"como acceso perdido, no reubicados."
        ),
    }


def _summaries(option: OptionResult) -> dict[str, str]:
    """Plain-language summaries in en/pt/es with IDENTICAL numbers (Req 7.2).

    Numbers are formatted once and interpolated into every language so the
    figures never diverge across translations (data-and-safety rule).
    """
    risk = f"{abs(option.delta_risk_pct):.1f}%"
    hours = f"{abs(option.delta_hours_pct):.1f}%"
    access = f"{abs(option.delta_effort_access_pct):.1f}%"
    risk_dir = {"en": "less" if option.delta_risk_pct <= 0 else "more",
                "pt": "menos" if option.delta_risk_pct <= 0 else "mais",
                "es": "menos" if option.delta_risk_pct <= 0 else "más"}
    acc_dir = {"en": "less" if option.delta_effort_access_pct <= 0 else "more",
               "pt": "menos" if option.delta_effort_access_pct <= 0 else "mais",
               "es": "menos" if option.delta_effort_access_pct <= 0 else "más"}
    return {
        "en": (
            f"\"{option.name}\": the fleet is exposed to {risk} {risk_dir['en']} "
            f"whale risk, spends {hours} more steaming time, and has {access} "
            f"{acc_dir['en']} access to fishing grounds (effort is an estimate, "
            f"not revenue)."
        ),
        "pt": (
            f"\"{option.name}\": a frota fica exposta a {risk} {risk_dir['pt']} "
            f"risco de baleias, gasta {hours} mais tempo de navegação e tem "
            f"{access} {acc_dir['pt']} acesso aos pesqueiros (o esforço é uma "
            f"estimativa, não receita)."
        ),
        "es": (
            f"\"{option.name}\": la flota queda expuesta a {risk} {risk_dir['es']} "
            f"riesgo de ballenas, dedica {hours} más de tiempo de navegación y "
            f"tiene {access} {acc_dir['es']} acceso a los caladeros (el esfuerzo "
            f"es una estimación, no ingresos)."
        ),
    }


# ---------------------------------------------------------------------------
# Public simulator
# ---------------------------------------------------------------------------


class Simulator:
    """Runs baselines and scenarios over a synthetic fleet, caching the baseline."""

    def __init__(
        self,
        *,
        router: RouterFn | None = None,
        fleet: Sequence[FleetTrip] | None = None,
        current_zones: list[dict] | None = None,
        fleet_size: int = 200,
    ) -> None:
        """Create a simulator.

        Args:
            router: A ``route_one``-compatible callable. Defaults to the real
                router if importable, else the deterministic synthetic fallback.
            fleet: Fleet trips. Defaults to a deterministic synthetic fleet.
            current_zones: Zones active in the baseline (added to every route).
            fleet_size: Size of the generated synthetic fleet when none is given.
        """
        self.router: RouterFn = router or _try_import_real_router() or synthetic_route_one
        self.using_real_router = router is None and _try_import_real_router() is not None
        if fleet is not None:
            self.fleet = list(fleet)
            self.fleet_source = "injected"
        else:
            anant = _try_anant_fleet(fleet_size)
            if anant:
                self.fleet = anant
                self.fleet_source = "synthetic (engine.fleet.build_fleet, seeded from config/ports.yaml)"
            else:
                self.fleet = build_synthetic_fleet(fleet_size)
                self.fleet_source = "synthetic (seeded from in-module Massachusetts port list)"
        self.current_zones = current_zones or []
        self._baseline_cache: FleetTotals | None = None

    def baseline(self, when: datetime | None = None) -> FleetTotals:
        """Route the fleet under current zones (cached after first call)."""
        if self._baseline_cache is None:
            self._baseline_cache = _route_fleet(
                self.fleet, self.router, when or _default_when(), self.current_zones or None
            )
        return self._baseline_cache

    def run_scenario(self, scenario: Scenario, when: datetime | None = None) -> OptionResult:
        """Route the fleet with the scenario's extra zones and compute deltas."""
        base = self.baseline(when)
        combined = (self.current_zones or []) + scenario.extra_zones
        scen_totals = _route_fleet(self.fleet, self.router, when or _default_when(), combined)
        return OptionResult(
            scenario_id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            totals=scen_totals,
            delta_risk_pct=_pct_delta(base.risk_exposure, scen_totals.risk_exposure),
            delta_hours_pct=_pct_delta(base.steaming_hours, scen_totals.steaming_hours),
            delta_fuel_pct=_pct_delta(base.fuel_l, scen_totals.fuel_l),
            delta_effort_access_pct=_pct_delta(base.effort_access, scen_totals.effort_access),
        )

    def run_all(self, scenarios: Sequence[Scenario] | None = None, when: datetime | None = None) -> dict[str, Any]:
        """Run every scenario, mark the Pareto frontier, and build summaries.

        Returns a JSON-serializable result with the baseline, per-option deltas,
        frontier flags, trilingual summaries (identical numbers), and honesty
        labels. Designed to complete in well under 20 s for ~200 trips.
        """
        scenarios = list(scenarios if scenarios is not None else preloaded_scenarios())
        base = self.baseline(when)
        options = [self.run_scenario(s, when) for s in scenarios]
        _mark_pareto_frontier(options)
        return {
            "baseline": base.as_dict(),
            "baseline_explanation": baseline_access_explanation(base.access_lost, base.trips),
            "options": [
                {**o.as_dict(), "summary": _summaries(o)} for o in options
            ],
            "pareto": _pareto_points(options),
            "fleet": {
                "size": len(self.fleet),
                "synthetic": True,
                "source": self.fleet_source,
            },
            "router": "real" if self.using_real_router else "synthetic-fallback",
            "labels": {
                "effort_access": "ESTIMATE of fishing activity, not catch or revenue",
                "advisory": "Advisory only; does not replace official notices or captain judgment.",
            },
        }


def _default_when() -> datetime:
    """Default evaluation time: mid-March (whale season) demo date, UTC."""
    return datetime(2026, 3, 15, 11, 0, tzinfo=UTC)
