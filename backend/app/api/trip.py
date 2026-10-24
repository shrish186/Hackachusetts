"""Trip endpoints (Lane B, task 8, design.md §9).

    POST /api/trip/plan   -> text/event-stream (tool_call, tool_result, plans, done, error)
    POST /api/trip/brief  -> one-page printable HTML
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Literal

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ingest.conditions import demo_mode

from app.agent.agent import DISCLAIMER, run_agent
from app.api.layers import snapshot_meta
from app.engine.routing import ports_config, zone_names
from app.models import TripRequest

router = APIRouter(tags=["trip"])

_ID = r"^[a-z0-9_]{1,40}$"
MAX_WINDOW = timedelta(days=14)
MAX_PAST = timedelta(days=7)
#: Bundled demo data is from mid-March 2026; demo-mode trips may depart from then on.
DEMO_EPOCH = datetime(2026, 3, 14, tzinfo=timezone.utc)


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def earliest_departure(now: datetime | None = None) -> datetime:
    """Oldest allowed departure: 7 days before now (or before the demo data in demo mode)."""
    now = _utc(now or datetime.now(timezone.utc))
    anchor = min(now, DEMO_EPOCH) if demo_mode() else now
    return anchor - MAX_PAST


class TripPlanBody(BaseModel):
    """TripRequest with API-boundary bounds (frontend/src/api/types.ts TripRequest)."""

    model_config = ConfigDict(extra="forbid")

    port: str = Field(..., pattern=_ID)
    vessel: Literal["small_boat", "mid_trawler", "scalloper"]
    cruise_kn: float = Field(..., gt=0, le=30)
    max_hours: float = Field(..., gt=0, le=72)
    depart_window: tuple[datetime, datetime]
    target_ground: str | None = Field(None, pattern=_ID)
    risk_pref: float = Field(..., ge=0, le=1)
    language: Literal["en", "pt", "es"] = "en"

    @field_validator("depart_window")
    @classmethod
    def _window(cls, v: tuple[datetime, datetime]) -> tuple[datetime, datetime]:
        start, end = _utc(v[0]), _utc(v[1])
        if end < start:
            raise ValueError("depart_window start must not be after end")
        if end - start > MAX_WINDOW:
            raise ValueError("depart_window must be at most 14 days long")
        if start < earliest_departure():
            raise ValueError("depart_window start is more than 7 days in the past")
        return (start, end)

    @field_validator("port")
    @classmethod
    def _known_port(cls, v: str) -> str:
        if v not in ports_config()["ports"]:
            raise ValueError("unknown port")
        return v

    @field_validator("target_ground")
    @classmethod
    def _known_ground(cls, v: str | None) -> str | None:
        if v is not None and v not in ports_config()["fishing_grounds"]:
            raise ValueError("unknown fishing ground")
        return v

    def to_trip(self) -> TripRequest:
        return TripRequest.model_validate(self.model_dump())


def _sse_lines(events: Iterator[dict[str, Any]]) -> Iterator[str]:
    try:
        for ev in events:
            yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'], ensure_ascii=False, default=str)}\n\n"
    except Exception:  # noqa: BLE001 - stream a generic error, never a traceback
        yield 'event: error\ndata: {"error": "Planning failed."}\n\n'


@router.post("/trip/plan")
def trip_plan(body: TripPlanBody) -> StreamingResponse:
    """Stream the agent's tool calls, then the ranked plans (Req 4, 4.5)."""
    return StreamingResponse(
        _sse_lines(run_agent(body.to_trip())),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


class WeatherWindowIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    from_: str | None = Field(None, alias="from", max_length=40)
    to: str | None = Field(None, max_length=40)
    max_wave_m: float | None = Field(None, ge=0, le=30)
    max_wind_kn: float | None = Field(None, ge=0, le=150)
    note: str | None = Field(None, max_length=300)


class PlanIn(BaseModel):
    """RoutePlan as sent back by the frontend (bounded)."""

    model_config = ConfigDict(extra="ignore")
    name: str | None = Field(None, max_length=60)
    waypoints: list[tuple[float, float]] = Field(..., min_length=1, max_length=500)
    eta_hours: float = Field(..., ge=0, le=200)
    fuel_est_l: float = Field(..., ge=0, le=1e6)
    zones_crossed: list[str] = Field(default_factory=list, max_length=50)
    zones_avoided: list[str] = Field(default_factory=list, max_length=50)
    max_wave_m: float = Field(..., ge=0, le=30)
    risk_exposure: float = Field(..., ge=0, le=1e4)
    effort_proxy: float = Field(0.0, ge=0, le=1)
    weather_window: WeatherWindowIn | None = None

    @field_validator("waypoints")
    @classmethod
    def _lonlat(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for lon, lat in v:
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("waypoint out of range")
        return v


class BriefBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: PlanIn
    language: Literal["en", "pt", "es"] = "en"
    trip: TripPlanBody | None = None


B = {
    "en": {"title": "Fathom trip brief", "route": "Route", "waypoints": "Waypoints", "zones": "Zone alerts",
           "crosses": "Crosses", "avoids": "Avoids (known closed areas)", "none": "none", "weather": "Weather window",
           "eta": "ETA each way", "fuel": "Estimated fuel", "risk": "Whale risk exposure", "effort": "Fishing effort estimate (not catch or revenue)",
           "data": "Data timestamps", "generated": "Generated", "wave": "Max wave", "wind": "Max wind", "from": "From", "to": "To",
           "port": "Port", "ground": "Ground", "vessel": "Vessel"},
    "pt": {"title": "Resumo da viagem Fathom", "route": "Rota", "waypoints": "Pontos de rota", "zones": "Alertas de zonas",
           "crosses": "Passa por", "avoids": "Evita (áreas fechadas conhecidas)", "none": "nenhuma", "weather": "Janela de tempo",
           "eta": "Tempo por trecho", "fuel": "Combustível estimado", "risk": "Exposição ao risco de baleia", "effort": "Estimativa de esforço de pesca (não é captura nem receita)",
           "data": "Horários dos dados", "generated": "Gerado", "wave": "Onda máx.", "wind": "Vento máx.", "from": "De", "to": "Até",
           "port": "Porto", "ground": "Pesqueiro", "vessel": "Embarcação"},
    "es": {"title": "Resumen de viaje Fathom", "route": "Ruta", "waypoints": "Puntos de ruta", "zones": "Alertas de zonas",
           "crosses": "Pasa por", "avoids": "Evita (áreas cerradas conocidas)", "none": "ninguna", "weather": "Ventana meteorológica",
           "eta": "Tiempo por trayecto", "fuel": "Combustible estimado", "risk": "Exposición al riesgo de ballena", "effort": "Estimación de esfuerzo pesquero (no es captura ni ingresos)",
           "data": "Hora de los datos", "generated": "Generado", "wave": "Ola máx.", "wind": "Viento máx.", "from": "Desde", "to": "Hasta",
           "port": "Puerto", "ground": "Caladero", "vessel": "Embarcación"},
}


def _g(x: float) -> str:
    return f"{x:g}"


def render_brief(body: BriefBody) -> str:
    """One-page printable HTML. All user strings are HTML-escaped."""
    e = html.escape
    t = B[body.language]
    p = body.plan
    names = zone_names()
    zn = lambda ids: ", ".join(e(names.get(z, z)) for z in ids) or t["none"]  # noqa: E731
    rows = "".join(f"<tr><td>{i}</td><td>{lat:.4f}</td><td>{lon:.4f}</td></tr>" for i, (lon, lat) in enumerate(p.waypoints, 1))
    w = p.weather_window
    wx = (f"<p>{t['from']} {e(w.from_ or '-')} {t['to']} {e(w.to or '-')}. {t['wave']} {_g(w.max_wave_m or p.max_wave_m)} m"
          + (f", {t['wind']} {_g(w.max_wind_kn)} kn" if w.max_wind_kn is not None else "") + f". {e(w.note or '')}</p>") if w \
        else f"<p>{t['wave']} {_g(p.max_wave_m)} m</p>"
    stamps = []
    for label, fname in [("conditions", "conditions.json"), ("zones", "zones.json"), ("sightings", "sightings.json")]:
        m = snapshot_meta(fname)
        stamps.append(f"<li>{label}: {e(str(m.get('fetched_at') or '-'))}{' (synthetic)' if m.get('synthetic') else ''}</li>")
    trip = ""
    if body.trip:
        pc = ports_config()
        port = pc["ports"][body.trip.port]["name"]
        ground = pc["fishing_grounds"].get(body.trip.target_ground or "stellwagen_bank", {}).get("name", "")
        trip = f"<p>{t['port']}: {e(port)} · {t['ground']}: {e(ground)} · {t['vessel']}: {e(body.trip.vessel)}</p>"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="{body.language}"><head><meta charset="utf-8"><title>{t['title']}</title>
<style>
@page {{ size: letter; margin: 12mm; }}
body {{ font: 12px/1.35 system-ui, sans-serif; color: #111; max-width: 190mm; margin: 0 auto; }}
h1 {{ font-size: 18px; margin: 0 0 4px; }} h2 {{ font-size: 13px; margin: 10px 0 4px; border-bottom: 1px solid #999; }}
table {{ border-collapse: collapse; width: 100%; font-size: 11px; }} td, th {{ border: 1px solid #ccc; padding: 2px 4px; text-align: left; }}
.disc {{ border: 2px solid #b00; padding: 6px; font-weight: 600; margin-top: 10px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2px 12px; }}
</style></head><body>
<h1>{t['title']}: {e(p.name or t['route'])}</h1>
{trip}
<div class="grid">
<div>{t['eta']}: <b>{_g(p.eta_hours)} h</b></div><div>{t['fuel']}: <b>{_g(p.fuel_est_l)} L</b></div>
<div>{t['risk']}: <b>{_g(p.risk_exposure)}</b></div><div>{t['effort']}: <b>{_g(p.effort_proxy)}</b></div>
</div>
<h2>{t['zones']}</h2>
<p>{t['crosses']}: {zn(p.zones_crossed)}</p>
<p>{t['avoids']}: {zn(p.zones_avoided)}</p>
<h2>{t['weather']}</h2>
{wx}
<h2>{t['waypoints']}</h2>
<table><tr><th>#</th><th>Lat</th><th>Lon</th></tr>{rows}</table>
<h2>{t['data']}</h2>
<ul>{''.join(stamps)}</ul>
<p>{t['generated']}: {now}</p>
<div class="disc">{e(DISCLAIMER[body.language])}</div>
</body></html>"""


@router.post("/trip/brief", response_class=HTMLResponse)
def trip_brief(body: BriefBody) -> HTMLResponse:
    """Printable one-page brief (Req 8.1)."""
    return HTMLResponse(render_brief(body), headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
                                                       "Cache-Control": "no-store"})
