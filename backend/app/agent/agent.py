"""Deterministic trip-planning agent (Lane B, task 7, design.md §7).

Runs a fixed tool sequence (at most 8 calls), streams each call and result,
and writes the explanation from templates in English, Portuguese and Spanish.
Every narrative sentence carries a ``[tool:call_N]`` citation, and numbers and
zone names are copied verbatim from tool results, so they are identical across
languages.

No LLM is needed. If ``ANTHROPIC_API_KEY`` is set, the LLM may rewrite only the
narrative from the tool results; :func:`citation_guard` then drops any
sentence whose numbers or zone names are uncited or not found in the cited
tool results. If the guard drops everything, the template narrative is used.

The agent never says a plan is legally compliant. It says which known zones a
plan avoids.
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterator
from typing import Any

from app.agent.tools import call_tool
from app.models import TripRequest

log = logging.getLogger("fathom.agent")

MAX_TOOL_CALLS = 8

LABELS: dict[str, dict[str, str]] = {
    "en": {"get_conditions": "Checking weather and sea state…", "get_zones": "Checking protection zones…",
           "get_whale_risk": "Checking whale risk…", "get_effort_proxy": "Checking fishing access…",
           "plan_routes": "Planning routes…", "estimate_fuel": "Estimating fuel…"},
    "pt": {"get_conditions": "Verificando clima e estado do mar…", "get_zones": "Verificando zonas de proteção…",
           "get_whale_risk": "Verificando risco de baleia…", "get_effort_proxy": "Verificando acesso à pesca…",
           "plan_routes": "Planejando rotas…", "estimate_fuel": "Estimando combustível…"},
    "es": {"get_conditions": "Revisando clima y estado del mar…", "get_zones": "Revisando zonas de protección…",
           "get_whale_risk": "Revisando riesgo de ballena…", "get_effort_proxy": "Revisando acceso a pesca…",
           "plan_routes": "Planificando rutas…", "estimate_fuel": "Estimando combustible…"},
}

DISCLAIMER = {
    "en": "Advisory only. This does not replace official notices, VHF warnings, or the captain's judgment.",
    "pt": "Apenas orientativo. Não substitui avisos oficiais, alertas por VHF nem o julgamento do capitão.",
    "es": "Solo orientativo. No reemplaza avisos oficiales, alertas por VHF ni el criterio del capitán.",
}

PLAN_NAMES = {
    "en": {"Fastest": "Fastest", "Balanced": "Balanced", "Safest": "Safest", "Wide berth": "Wide berth", "Alternate track": "Alternate track"},
    "pt": {"Fastest": "Mais rápida", "Balanced": "Equilibrada", "Safest": "Mais segura", "Wide berth": "Distância ampla", "Alternate track": "Rota alternativa"},
    "es": {"Fastest": "Más rápida", "Balanced": "Equilibrada", "Safest": "Más segura", "Wide berth": "Margen amplio", "Alternate track": "Ruta alternativa"},
}

# Templates. {c} is the citation tag. Numbers/zone names are inserted verbatim.
T = {
    "en": {
        "zones_active": "{n} known zones are active at departure: {names} {c}.",
        "zones_none": "No known zones are active at departure {c}.",
        "zones_synthetic": "Some zone shapes are hand-drawn demo data (synthetic), so check official charts {c}.",
        "conditions": "Latest readings show waves up to {wave} m and wind up to {wind} kn {c}.",
        "conditions_none": "No sea-state readings are available for this area {c}.",
        "risk": "At {speed} kn the highest whale risk in the area is {risk} on a 0 to 1 scale {c}.",
        "plan": "{name}: about {eta} h each way ({rt} h round trip), estimated fuel {fuel} L {c}.",
        "crossed": "{name} passes through {zones} {c}.",
        "crossed_none": "{name} passes through no known zones {c}.",
        "slow": "Speed limits there add about {slow} h to the trip {c}.",
        "avoided": "{name} avoids these known closed areas: {zones} {c}.",
        "exposure": "{name} whale risk exposure is {exp} (risk times hours) and max wave on the track is about {wave} m {c}.",
        "effort": "The fishing effort estimate at {ground} is {effort} on a 0 to 1 scale, an estimate and not catch or revenue {c}.",
        "no_route": "{message} {c}",
        "window_note": "Based on the latest bundled readings; conditions can change.",
    },
    "pt": {
        "zones_active": "{n} zonas conhecidas estão ativas na saída: {names} {c}.",
        "zones_none": "Nenhuma zona conhecida está ativa na saída {c}.",
        "zones_synthetic": "Algumas zonas são dados de demonstração desenhados à mão (sintéticos), confira as cartas oficiais {c}.",
        "conditions": "As leituras mais recentes mostram ondas de até {wave} m e vento de até {wind} kn {c}.",
        "conditions_none": "Não há leituras do estado do mar para esta área {c}.",
        "risk": "A {speed} kn o maior risco de baleia na área é {risk} numa escala de 0 a 1 {c}.",
        "plan": "{name}: cerca de {eta} h por trecho ({rt} h ida e volta), combustível estimado {fuel} L {c}.",
        "crossed": "{name} passa por {zones} {c}.",
        "crossed_none": "{name} não passa por nenhuma zona conhecida {c}.",
        "slow": "Os limites de velocidade ali somam cerca de {slow} h à viagem {c}.",
        "avoided": "{name} evita estas áreas fechadas conhecidas: {zones} {c}.",
        "exposure": "{name} tem exposição ao risco de baleia de {exp} (risco vezes horas) e onda máxima na rota de cerca de {wave} m {c}.",
        "effort": "A estimativa de esforço de pesca em {ground} é {effort} numa escala de 0 a 1, uma estimativa e não captura ou receita {c}.",
        "no_route": "{message} {c}",
        "window_note": "Com base nas leituras mais recentes incluídas; as condições podem mudar.",
    },
    "es": {
        "zones_active": "{n} zonas conocidas están activas a la salida: {names} {c}.",
        "zones_none": "Ninguna zona conocida está activa a la salida {c}.",
        "zones_synthetic": "Algunas zonas son datos de demostración dibujados a mano (sintéticos), revise las cartas oficiales {c}.",
        "conditions": "Las lecturas más recientes muestran olas de hasta {wave} m y viento de hasta {wind} kn {c}.",
        "conditions_none": "No hay lecturas del estado del mar para esta área {c}.",
        "risk": "A {speed} kn el mayor riesgo de ballena en la zona es {risk} en una escala de 0 a 1 {c}.",
        "plan": "{name}: unas {eta} h por trayecto ({rt} h ida y vuelta), combustible estimado {fuel} L {c}.",
        "crossed": "{name} pasa por {zones} {c}.",
        "crossed_none": "{name} no pasa por ninguna zona conocida {c}.",
        "slow": "Los límites de velocidad allí suman unas {slow} h al viaje {c}.",
        "avoided": "{name} evita estas áreas cerradas conocidas: {zones} {c}.",
        "exposure": "{name} tiene una exposición al riesgo de ballena de {exp} (riesgo por horas) y ola máxima en la ruta de unos {wave} m {c}.",
        "effort": "La estimación de esfuerzo pesquero en {ground} es {effort} en una escala de 0 a 1, una estimación y no captura ni ingresos {c}.",
        "no_route": "{message} {c}",
        "window_note": "Según las lecturas más recientes incluidas; las condiciones pueden cambiar.",
    },
}

_NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")
_CITE_RE = re.compile(r"\[tool:(call_\d+)\]")
_BANNED_RE = re.compile(r"\b(legally|compliant|compliance|conforme|cumpre|cumple|cumplimiento|conformidade)\b", re.IGNORECASE)


def fmt(x: float) -> str:
    """Language-neutral number text (dot decimal) so all languages match."""
    return f"{x:g}" if isinstance(x, float) else str(x)


def _cite(call_id: str) -> str:
    return f"[tool:{call_id}]"


def _source_label(source_url: str | None, synthetic: bool) -> str:
    """Human-readable source label for a citation.

    When a tool result has no ``source_url`` (several of our bundled demo
    layers), the plan narrative must still show *where* the fact came from, so
    we label it explicitly instead of leaving a bare ``null`` the UI can't
    render (task 5). Synthetic sources say so.
    """
    if source_url:
        return source_url
    return "bundled demo data (synthetic)" if synthetic else "bundled demo data"


def _citation(call_id: str, tool: str, claim: str, *, source_url: str | None, synthetic: bool) -> dict[str, Any]:
    """Build a citation record carrying both the url and a human source label."""
    return {
        "tool_call_id": call_id,
        "tool": tool,
        "claim": claim,
        "source_url": source_url,
        "source_label": _source_label(source_url, synthetic),
    }


def _sse(event: str, data: Any) -> dict[str, Any]:
    return {"event": event, "data": data}


def _area_bbox(origin: tuple[float, float], dest: tuple[float, float], pad: float = 0.25) -> list[float]:
    return [round(min(origin[0], dest[0]) - pad, 3), round(min(origin[1], dest[1]) - pad, 3),
            round(max(origin[0], dest[0]) + pad, 3), round(max(origin[1], dest[1]) + pad, 3)]


def _numbers(obj: Any) -> set[float]:
    """Every number (and number inside a string) in a tool result."""
    out: set[float] = set()
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.add(round(float(obj), 6))
    elif isinstance(obj, str):
        out |= {round(float(m), 6) for m in _NUM_RE.findall(obj)}
    elif isinstance(obj, dict):
        for v in obj.values():
            out |= _numbers(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out |= _numbers(v)
    return out


def citation_guard(sentences: list[str], results: dict[str, Any], zone_names: list[str]) -> list[dict[str, Any]]:
    """Keep only sentences whose facts are cited and found in the cited results.

    A sentence is dropped if it contains a number or a zone name and has no
    valid ``[tool:call_N]`` tag, if a number does not appear in the cited tool
    results, or if it claims legal compliance.
    """
    kept = []
    for s in sentences:
        s = s.strip()
        if not s or _BANNED_RE.search(s):
            continue
        cites = [c for c in _CITE_RE.findall(s) if c in results]
        body = _CITE_RE.sub("", s)
        nums = {round(float(n), 6) for n in _NUM_RE.findall(body)}
        names = [z for z in zone_names if z and z in body]
        if (nums or names) and not cites:
            continue
        allowed: set[float] = set()
        text = ""
        for c in cites:
            allowed |= _numbers(results[c])
            text += json.dumps(results[c], ensure_ascii=False)
        if not nums <= allowed:
            continue
        if any(z not in text for z in names):
            continue
        if not cites and not _CITE_RE.search(s):
            continue  # every sentence must be cited (factual by construction here)
        kept.append({"text": s, "citations": cites})
    return kept


def _template_narrative(lang: str, ids: dict[str, str], res: dict[str, Any], trip: TripRequest) -> list[str]:
    t = T[lang]
    out: list[str] = []
    zones = res[ids["get_zones"]]
    active = [z for z in zones["zones"] if z["active"]]
    c1 = _cite(ids["get_zones"])
    if active:
        out.append(t["zones_active"].format(n=zones["active_count"], names="; ".join(z["name"] for z in active), c=c1))
    else:
        out.append(t["zones_none"].format(c=c1))
    if zones.get("synthetic"):
        out.append(t["zones_synthetic"].format(c=c1))
    cond = res[ids["get_conditions"]]
    c2 = _cite(ids["get_conditions"])
    if cond["count"]:
        out.append(t["conditions"].format(wave=fmt(cond["max_wave_m"]), wind=fmt(cond["max_wind_kn"]), c=c2))
    else:
        out.append(t["conditions_none"].format(c=c2))
    risk = res[ids["get_whale_risk"]]
    out.append(t["risk"].format(speed=fmt(risk["speed_kn"]), risk=fmt(risk["max_risk"]), c=_cite(ids["get_whale_risk"])))

    plan = res[ids["plan_routes"]]
    c4 = _cite(ids["plan_routes"])
    zn = plan["zone_names"]
    if not plan["ok"]:
        out.append(t["no_route"].format(message=plan["message"], c=c4))
        return out
    for p in plan["plans"]:
        name = PLAN_NAMES[lang].get(p["name"], p["name"])
        out.append(t["plan"].format(name=name, eta=fmt(p["eta_hours"]), rt=fmt(p["round_trip_hours"]), fuel=fmt(p["fuel_est_l"]), c=c4))
        if p["zones_crossed"]:
            out.append(t["crossed"].format(name=name, zones="; ".join(zn.get(z, z) for z in p["zones_crossed"]), c=c4))
            if p["slow_zone_hours"] > 0:
                out.append(t["slow"].format(slow=fmt(p["slow_zone_hours"]), c=c4))
        else:
            out.append(t["crossed_none"].format(name=name, c=c4))
        if p["zones_avoided"]:
            out.append(t["avoided"].format(name=name, zones="; ".join(zn.get(z, z) for z in p["zones_avoided"]), c=c4))
        out.append(t["exposure"].format(name=name, exp=fmt(p["risk_exposure"]), wave=fmt(p["max_wave_m"]), c=c4))
    if "get_effort_proxy" in ids:
        ground_val = plan["plans"][0]["effort_proxy"]
        out.append(t["effort"].format(ground=plan["ground_name"], effort=fmt(ground_val),
                                      c=_cite(ids["plan_routes"]) + " " + _cite(ids["get_effort_proxy"])))
    return out


def _llm_rewrite(lang: str, results: dict[str, Any], template: list[str]) -> list[str] | None:
    """Optional narrative rewrite by Claude. Returns sentences or None on any failure."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import httpx

        prompt = (
            "Rewrite this fishing-trip briefing in plain words at a grade 8 reading level, in language '"
            + lang + "'. Rules: use only facts in the TOOL RESULTS; copy numbers and zone names exactly; "
            "end every sentence with the matching [tool:call_N] tag; never say a plan is legally compliant, "
            "only which known zones it avoids; one sentence per line; no other text.\n\nTOOL RESULTS:\n"
            + json.dumps(results, ensure_ascii=False)[:60000] + "\n\nDRAFT:\n" + "\n".join(template)
        )
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"), "max_tokens": 1200,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=8.0,
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        return [line for line in text.splitlines() if line.strip()]
    except Exception:  # noqa: BLE001 - fall back to templates
        log.warning("LLM rewrite failed; using template narrative")
        return None


def run_agent(trip_request: dict[str, Any] | TripRequest) -> Iterator[dict[str, Any]]:
    """Yield SSE-ready events: tool_call, tool_result, plans, done (or error)."""
    try:
        trip = trip_request if isinstance(trip_request, TripRequest) else TripRequest.model_validate(trip_request)
    except Exception:
        yield _sse("error", {"error": "Invalid trip request."})
        return
    lang = trip.language
    labels = LABELS[lang]
    from app.engine.routing import RoutingError, place_lonlat, ports_config

    ground = trip.target_ground or "stellwagen_bank"
    try:
        origin = place_lonlat("ports", trip.port)
        dest = place_lonlat("fishing_grounds", ground)
    except RoutingError as exc:
        yield _sse("error", {"error": str(exc)})
        return
    bbox = _area_bbox(origin, dest)
    depart = trip.depart_window[0].isoformat().replace("+00:00", "Z")
    trip_json = trip.model_dump(mode="json")
    trip_json["target_ground"] = ground

    plan_steps: list[tuple[str, dict[str, Any]]] = [
        ("get_zones", {"bbox": bbox, "time": depart}),
        ("get_conditions", {}),  # whole study area: routes interpolate from every buoy
        ("get_whale_risk", {"bbox": bbox, "time": depart, "speed_kn": trip.cruise_kn}),
        ("plan_routes", {"trip_request": trip_json}),
        ("get_effort_proxy", {"bbox": _area_bbox(dest, dest, 0.1), "month": trip.depart_window[0].month}),
    ]
    assert len(plan_steps) <= MAX_TOOL_CALLS
    ids: dict[str, str] = {}
    results: dict[str, Any] = {}
    for n, (tool, args) in enumerate(plan_steps[:MAX_TOOL_CALLS], start=1):
        cid = f"call_{n}"
        ids[tool] = cid
        yield _sse("tool_call", {"id": cid, "tool": tool, "label": labels[tool], "status": "running", "args": args})
        try:
            out = call_tool(tool, args)
        except Exception:
            log.exception("tool %s failed", tool)
            yield _sse("tool_result", {"id": cid, "tool": tool, "label": labels[tool], "status": "error", "detail": "failed"})
            yield _sse("error", {"error": f"Tool {tool} failed."})
            return
        if tool == "plan_routes":
            out["ground_name"] = ports_config()["fishing_grounds"][ground]["name"]
        results[cid] = out
        yield _sse("tool_result", {"id": cid, "tool": tool, "label": labels[tool], "status": "done",
                                   "detail": _detail(tool, out), "result": out})

    template = _template_narrative(lang, ids, results, trip)
    zone_names = sorted({z["name"] for z in results[ids["get_zones"]]["zones"]}
                        | set(results[ids["plan_routes"]]["zone_names"].values()), key=len, reverse=True)
    narrative = citation_guard(template, results, zone_names)
    rewritten = _llm_rewrite(lang, results, template)
    if rewritten:
        guarded = citation_guard(rewritten, results, zone_names)
        if guarded:
            narrative = guarded

    yield _sse("plans", {
        "plans": _route_plans(lang, ids, results),
        "narrative": narrative,
        "language": lang,
        "disclaimer": DISCLAIMER[lang],
        "message": results[ids["plan_routes"]]["message"],
        "synthetic": any(r.get("synthetic") for r in results.values()),
    })
    yield _sse("done", {"tool_calls": len(results)})


def _detail(tool: str, out: dict[str, Any]) -> str:
    if tool == "get_zones":
        return f"{sum(z['active'] for z in out['zones'])} of {out['count']} zones active"
    if tool == "get_conditions":
        return f"{out['count']} readings, max wave {fmt(out['max_wave_m'])} m" if out["count"] else "no readings"
    if tool == "get_whale_risk":
        return f"max risk {fmt(out['max_risk'])} at {fmt(out['speed_kn'])} kn"
    if tool == "plan_routes":
        return f"{len(out['plans'])} plans" if out["ok"] else "no legal route"
    if tool == "get_effort_proxy":
        return f"max effort estimate {fmt(out['max_effort'])}"
    return "done"


def _route_plans(lang: str, ids: dict[str, str], res: dict[str, Any]) -> list[dict[str, Any]]:
    """RoutePlan objects (frontend/src/api/types.ts) with citations."""
    plan_cid = ids["plan_routes"]
    plan = res[plan_cid]
    zones_by_id = {z["id"]: z for z in res[ids["get_zones"]]["zones"]}
    cond_cid = ids["get_conditions"]
    cond_url = res[cond_cid].get("source_url")
    cond_synth = bool(res[cond_cid].get("synthetic"))
    plan_synth = bool(res[plan_cid].get("synthetic"))
    out = []
    for p in plan["plans"]:
        name = PLAN_NAMES[lang].get(p["name"], p["name"])
        cites = [
            _citation(plan_cid, "plan_routes",
                      f"eta_hours {fmt(p['eta_hours'])}, fuel_est_l {fmt(p['fuel_est_l'])}, risk_exposure {fmt(p['risk_exposure'])}",
                      source_url=None, synthetic=plan_synth),
            _citation(cond_cid, "get_conditions",
                      f"max_wave_m {fmt(p['max_wave_m'])} interpolated from buoy readings",
                      source_url=cond_url, synthetic=cond_synth),
        ]
        for zid in p["zones_crossed"] + p["zones_avoided"]:
            z = zones_by_id.get(zid)
            cites.append(_citation(
                ids["get_zones"], "get_zones",
                f"{'crosses' if zid in p['zones_crossed'] else 'avoids'} {plan['zone_names'].get(zid, zid)}",
                source_url=z.get("source_url") if z else None,
                synthetic=bool(z.get("synthetic")) if z else True,
            ))
        out.append({
            "name": name,
            "waypoints": [list(w) for w in p["waypoints"]],
            "eta_hours": p["eta_hours"],
            "round_trip_hours": p["round_trip_hours"],
            "fuel_est_l": p["fuel_est_l"],
            "zones_crossed": p["zones_crossed"],
            "zones_avoided": p["zones_avoided"],
            "slow_zone_hours": p["slow_zone_hours"],
            "max_wave_m": p["max_wave_m"],
            "risk_exposure": p["risk_exposure"],
            "effort_proxy": p["effort_proxy"],
            "weather_window": {**p["weather_window"], "note": T[lang]["window_note"]},
            "citations": cites,
            "estimate": True,
        })
    return out
