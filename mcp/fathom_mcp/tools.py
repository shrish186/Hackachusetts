"""The eight Fathom tools (design.md section 7), as validated placeholders.

Each public function here:

1. Validates its arguments with a pydantic model from :mod:`fathom_mcp.models`
   (raising ``pydantic.ValidationError`` on bad input).
2. Returns a clearly-labelled placeholder response (see
   :mod:`fathom_mcp.placeholders`) shaped like the real tool's eventual output.

These functions are deliberately framework-agnostic (plain Python, no MCP types)
so they can be unit-tested directly and wired into any server. The MCP wiring
lives in :mod:`fathom_mcp.server`.

Tool  -> design.md section 7 table:
    get_conditions   bbox, time range            -> wave/wind/SST per cell + source
    get_zones        bbox, time                  -> zones active/inactive + sources
    get_whale_risk   bbox, time, speed_kn        -> risk grid + top factors
    plan_routes      TripRequest                 -> 2-3 RoutePlan objects
    get_effort_proxy bbox, month                 -> normalized historical effort grid
    estimate_fuel    route, vessel               -> liters (labelled estimate)
    simulate_zone    polygon, fleet sample id    -> Δrisk, Δtime, Δeffort, per-vessel
    export_brief     RoutePlan, language         -> one-page HTML/PDF path
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from .models import (
    EstimateFuelArgs,
    ExportBriefArgs,
    GetConditionsArgs,
    GetEffortProxyArgs,
    GetWhaleRiskArgs,
    GetZonesArgs,
    PlanRoutesArgs,
    SimulateZoneArgs,
)
from .placeholders import placeholder_response

try:
    from . import backend_bridge as _bridge
except Exception:  # pragma: no cover - bridge should always import
    _bridge = None  # type: ignore


def _backend_ready() -> bool:
    """True when the real backend engine is importable (wire real data)."""
    return _bridge is not None and _bridge.available()


def _real_response(tool: str, source: str, **payload: Any) -> dict[str, Any]:
    """Envelope for REAL engine output: ``placeholder: false`` + a real source."""
    from datetime import datetime

    return {
        "placeholder": False,
        "tool": tool,
        "source": source,
        "generated_at": datetime.now(UTC).isoformat(),
        **payload,
    }


def get_conditions(bbox: dict, time_range: dict) -> dict[str, Any]:
    """Return wave/wind/SST per cell for a bbox over a time range (PLACEHOLDER).

    Args:
        bbox: ``{min_lon, min_lat, max_lon, max_lat}`` in decimal degrees.
        time_range: ``{start, end}`` ISO-8601 UTC timestamps.

    Returns:
        Placeholder conditions payload (always ``placeholder: true``).
    """
    args = GetConditionsArgs(bbox=bbox, time_range=time_range)
    if _backend_ready():
        data = _bridge.conditions_readings(
            args.bbox.model_dump(), args.time_range.model_dump(mode="json")["start"]
        )
        return _real_response(
            tool="get_conditions",
            source=str(data.get("source", "app.ingest.conditions")),
            bbox=args.bbox.model_dump(),
            time_range=args.time_range.model_dump(mode="json"),
            count=data.get("count", 0),
            max_wave_m=data.get("max_wave_m"),
            max_wind_kn=data.get("max_wind_kn"),
            cells=data.get("readings", []),
            synthetic=bool(data.get("synthetic")),
        )
    return placeholder_response(
        tool="get_conditions",
        note=(
            "Will return wave height (m), wind (kn), and SST (°C) per grid cell "
            "with per-record source and fetched_at. This is placeholder data."
        ),
        bbox=args.bbox.model_dump(),
        time_range=args.time_range.model_dump(mode="json"),
        cells=[],
    )


def get_zones(bbox: dict, time: Any) -> dict[str, Any]:
    """Return protection zones and their active/inactive state (PLACEHOLDER).

    Args:
        bbox: ``{min_lon, min_lat, max_lon, max_lat}`` in decimal degrees.
        time: ISO-8601 UTC timestamp to evaluate zone activity at.
    """
    args = GetZonesArgs(bbox=bbox, time=time)
    if _backend_ready():
        zones = _bridge.zones_at(args.time.isoformat())
        return _real_response(
            tool="get_zones",
            source="app.ingest.zones (bundled zones snapshot)",
            bbox=args.bbox.model_dump(),
            time=args.time.isoformat(),
            zones=zones,
        )
    return placeholder_response(
        tool="get_zones",
        note=(
            "Will return whale SMAs, slow zones, fishing closures, and wind "
            "lease/construction areas as GeoJSON with name, kind, effective "
            "dates, restriction summary, and source_url. This is placeholder data."
        ),
        bbox=args.bbox.model_dump(),
        time=args.time.isoformat(),
        zones=[],
    )


def get_whale_risk(bbox: dict, time: Any, speed_kn: float) -> dict[str, Any]:
    """Return a whale-risk grid (0..1) for a speed at a time (PLACEHOLDER).

    Args:
        bbox: ``{min_lon, min_lat, max_lon, max_lat}`` in decimal degrees.
        time: ISO-8601 UTC timestamp.
        speed_kn: Planned vessel speed in knots (> 0).
    """
    args = GetWhaleRiskArgs(bbox=bbox, time=time, speed_kn=speed_kn)
    if _backend_ready():
        cells = _bridge.whale_risk_points(args.time.isoformat(), args.speed_kn)
        return _real_response(
            tool="get_whale_risk",
            source="app.engine.risk (deterministic model, config/risk.yaml)",
            bbox=args.bbox.model_dump(),
            time=args.time.isoformat(),
            speed_kn=args.speed_kn,
            risk_cells=cells,
        )
    return placeholder_response(
        tool="get_whale_risk",
        note=(
            "Will return risk(c,t,v) in [0,1] per cell = p_whale * lethality(v), "
            "plus the top contributing factors (presence, recency) per cell. "
            "Deterministic engine, never the LLM. This is placeholder data."
        ),
        bbox=args.bbox.model_dump(),
        time=args.time.isoformat(),
        speed_kn=args.speed_kn,
        risk_cells=[],
    )


def plan_routes(trip_request: dict) -> dict[str, Any]:
    """Return 2-3 ranked route plans for a trip request (PLACEHOLDER).

    Args:
        trip_request: A ``TripRequest``-shaped dict (port, vessel, cruise_kn,
            max_hours, risk_pref, ...).
    """
    args = PlanRoutesArgs(trip_request=trip_request)
    if _backend_ready():
        data = _bridge.plan_routes_real(args.trip_request)
        return _real_response(
            tool="plan_routes",
            source=str(data.get("source", "app.engine.routing (A* on study grid)")),
            trip_request=args.trip_request,
            ok=data.get("ok"),
            routes=data.get("plans", []),
            message=data.get("message"),
            synthetic=bool(data.get("synthetic", True)),
            estimate=True,
        )
    return placeholder_response(
        tool="plan_routes",
        note=(
            "Will return 2-3 RoutePlan objects (waypoints, eta_hours, fuel_est_l, "
            "zones_crossed, max_wave_m, risk_exposure, effort_proxy, citations) "
            "from A* over the water-cell grid. This is placeholder data."
        ),
        trip_request=args.trip_request,
        routes=[],
    )


def get_effort_proxy(bbox: dict, month: int) -> dict[str, Any]:
    """Return a normalized historical effort-proxy grid for a month (PLACEHOLDER).

    Args:
        bbox: ``{min_lon, min_lat, max_lon, max_lat}`` in decimal degrees.
        month: Month of year, 1-12.
    """
    args = GetEffortProxyArgs(bbox=bbox, month=month)
    if _backend_ready():
        cells = _bridge.effort_grid(args.bbox.model_dump())
        return _real_response(
            tool="get_effort_proxy",
            source="app.engine.effort (SYNTHETIC proxy field, config/ports.yaml)",
            bbox=args.bbox.model_dump(),
            month=args.month,
            effort_cells=cells,
            synthetic=True,
            disclaimer="Effort proxy is an estimate of activity, not catch or revenue.",
        )
    return placeholder_response(
        tool="get_effort_proxy",
        note=(
            "Will return a 0..1 normalized historical fishing-effort grid "
            "(a proxy, NOT catch or revenue). This is placeholder data."
        ),
        bbox=args.bbox.model_dump(),
        month=args.month,
        effort_cells=[],
        disclaimer="Effort proxy is an estimate of activity, not catch or revenue.",
    )


def estimate_fuel(route: dict, vessel: str) -> dict[str, Any]:
    """Return an estimated fuel burn in liters for a route (PLACEHOLDER).

    Args:
        route: A ``RoutePlan``-shaped dict (must include >=2 waypoints).
        vessel: One of ``small_boat``, ``mid_trawler``, ``scalloper``.
    """
    args = EstimateFuelArgs(route=route, vessel=vessel)
    if _backend_ready():
        data = _bridge.estimate_fuel_real(args.route, args.vessel)
        return _real_response(
            tool="estimate_fuel",
            source=str(data.get("source", "config/vessels.yaml fuel_burn_l_per_h")),
            vessel=args.vessel,
            waypoint_count=len(args.route["waypoints"]),
            distance_nm=data.get("distance_nm"),
            hours=data.get("hours"),
            fuel_est_l=data.get("fuel_est_l"),
            is_estimate=True,
            synthetic=bool(data.get("synthetic", True)),
        )
    return placeholder_response(
        tool="estimate_fuel",
        note=(
            "Will return liters of fuel as a clearly-labelled ESTIMATE from the "
            "vessel burn model in config/vessels.yaml. This is placeholder data."
        ),
        vessel=args.vessel,
        waypoint_count=len(args.route["waypoints"]),
        fuel_est_l=None,
        is_estimate=True,
    )


def simulate_zone(candidate_polygon: dict, fleet_sample_id: str) -> dict[str, Any]:
    """Return the trade-off deltas for a candidate protection zone (PLACEHOLDER).

    Args:
        candidate_polygon: A GeoJSON ``Polygon`` for the proposed zone.
        fleet_sample_id: Id of the fleet sample to re-route.
    """
    args = SimulateZoneArgs(
        candidate_polygon=candidate_polygon, fleet_sample_id=fleet_sample_id
    )
    if _backend_ready():
        result = _bridge.simulate_candidate(args.candidate_polygon, prohibited=True)
        opt = result["options"][0] if result.get("options") else {}
        deltas = opt.get("deltas_pct", {})
        return _real_response(
            tool="simulate_zone",
            source="app.engine.simulator (synthetic fleet, config/ports.yaml)",
            fleet_sample_id=args.fleet_sample_id,
            candidate_polygon=args.candidate_polygon,
            baseline=result.get("baseline"),
            delta_risk_pct=deltas.get("risk"),
            delta_hours_pct=deltas.get("hours"),
            delta_fuel_pct=deltas.get("fuel"),
            delta_effort_access_pct=deltas.get("effort_access"),
            on_frontier=opt.get("on_frontier"),
            summary=opt.get("summary"),
            labels=result.get("labels"),
        )
    return placeholder_response(
        tool="simulate_zone",
        note=(
            "Will re-route the fleet sample around the candidate zone and return "
            "Δrisk%, Δhours%, Δfuel%, Δeffort_access%, and per-vessel detail. "
            "Vessel identities are anonymized. This is placeholder data."
        ),
        fleet_sample_id=args.fleet_sample_id,
        candidate_polygon=args.candidate_polygon,
        delta_risk_pct=None,
        delta_hours_pct=None,
        delta_fuel_pct=None,
        delta_effort_access_pct=None,
        per_vessel=[],
    )


def export_brief(route: dict, language: str) -> dict[str, Any]:
    """Return the path to a rendered one-page trip brief (PLACEHOLDER).

    Args:
        route: A ``RoutePlan``-shaped dict (must include >=2 waypoints).
        language: One of ``en``, ``pt``, ``es``.
    """
    args = ExportBriefArgs(route=route, language=language)
    if _backend_ready():
        try:
            html_doc = _bridge.render_brief_html(args.route, args.language)
            return _real_response(
                tool="export_brief",
                source="app.api.trip.render_brief (one-page printable HTML)",
                language=args.language,
                waypoint_count=len(args.route["waypoints"]),
                format="html",
                html=html_doc,
                synthetic=True,
            )
        except Exception as exc:  # brief needs a full RoutePlan shape
            return _real_response(
                tool="export_brief",
                source="app.api.trip.render_brief",
                language=args.language,
                error="could_not_render",
                detail=str(exc)[:200],
                hint="route must be a full RoutePlan (name, waypoints, eta_hours, fuel_est_l, ...)",
            )
    return placeholder_response(
        tool="export_brief",
        note=(
            "Will render a one-page HTML/PDF brief (waypoints, zone alerts, "
            "weather windows, data timestamps) and return its file path. Numbers "
            "and zone names are identical across languages. This is placeholder data."
        ),
        language=args.language,
        waypoint_count=len(args.route["waypoints"]),
        brief_path=None,
    )


#: Ordered registry of the eight tools, used by the server to register them.
TOOLS = [
    get_conditions,
    get_zones,
    get_whale_risk,
    plan_routes,
    get_effort_proxy,
    estimate_fuel,
    simulate_zone,
    export_brief,
]
