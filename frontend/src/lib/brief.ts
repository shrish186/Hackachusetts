import type { Language, RoutePlan, TripRequest } from '@/api/types';
import { api } from '@/api/client';
import { DISCLAIMER } from '@/lib/i18n';
import { formatLocalShort } from '@/lib/time';

interface BriefOpts {
  zoneName: (id: string) => string;
  trip?: TripRequest;
}

/**
 * Open a printable one-page trip brief in a new window and trigger print
 * (requirements.md Req 8; tasks.md task 5). Prefers the backend brief
 * (POST /api/trip/brief) and falls back to a client-side HTML brief when the
 * backend is unreachable. The brief lists route waypoints, zone alerts, the
 * weather window, data timestamps, and the advisory disclaimer.
 */
export async function openBrief(
  plan: RoutePlan,
  language: Language,
  opts: BriefOpts,
): Promise<void> {
  const win = window.open('', '_blank', 'width=820,height=1000');
  if (!win) return; // popup blocked
  win.document.write(
    '<!doctype html><title>Fathom brief</title><body style="font-family:system-ui;padding:2rem">Preparing brief…</body>',
  );

  let html = await api.getBriefHtml(plan, language, opts.trip);
  if (!html) html = clientBrief(plan, language, opts);

  win.document.open();
  win.document.write(html);
  win.document.close();
  // Give the new document a tick to lay out before printing.
  win.setTimeout(() => win.print(), 350);
}

/** Build the brief entirely in the browser (demo / offline fallback). */
function clientBrief(plan: RoutePlan, language: Language, opts: BriefOpts): string {
  const title: Record<Language, string> = {
    en: 'Fathom trip brief',
    pt: 'Resumo de viagem Fathom',
    es: 'Resumen de viaje Fathom',
  };
  const labels: Record<Language, Record<string, string>> = {
    en: {
      route: 'Route waypoints',
      zones: 'Zone alerts',
      weather: 'Weather window',
      noZones: 'Avoids all known closures and managed zones.',
      eta: 'ETA',
      fuel: 'Fuel (estimate)',
      maxWave: 'Max wave',
      effort: 'Fishing access (estimate)',
      generated: 'Generated',
      demo: 'Demo data — generated in the browser',
    },
    pt: {
      route: 'Pontos da rota',
      zones: 'Alertas de zona',
      weather: 'Janela do tempo',
      noZones: 'Evita todos os fechamentos e zonas conhecidas.',
      eta: 'ETA',
      fuel: 'Combustível (estimativa)',
      maxWave: 'Onda máx.',
      effort: 'Acesso à pesca (estimativa)',
      generated: 'Gerado',
      demo: 'Dados demo — gerados no navegador',
    },
    es: {
      route: 'Puntos de la ruta',
      zones: 'Alertas de zona',
      weather: 'Ventana del tiempo',
      noZones: 'Evita todos los cierres y zonas conocidas.',
      eta: 'ETA',
      fuel: 'Combustible (estimación)',
      maxWave: 'Ola máx.',
      effort: 'Acceso a pesca (estimación)',
      generated: 'Generado',
      demo: 'Datos demo — generados en el navegador',
    },
  };
  const L = labels[language];

  const waypoints = plan.waypoints
    .map(([lon, lat], i) => `<tr><td>${i + 1}</td><td>${lat.toFixed(4)}</td><td>${lon.toFixed(4)}</td></tr>`)
    .join('');

  const zones =
    plan.zones_crossed.length === 0
      ? `<p>${esc(L.noZones)}</p>`
      : `<ul>${plan.zones_crossed
          .map((id) => `<li>${esc(opts.zoneName(id))}</li>`)
          .join('')}</ul>`;

  const ww = plan.weather_window;
  const weather = ww
    ? `<p>${esc(formatLocalShort(ww.from))} → ${esc(formatLocalShort(ww.to))}<br/>
       ${ww.max_wave_m.toFixed(1)} m · ${ww.max_wind_kn.toFixed(0)} kn<br/>${esc(ww.note)}</p>`
    : '<p>—</p>';

  return `<!doctype html>
<html lang="${language}"><head><meta charset="utf-8"/>
<title>${esc(title[language])}</title>
<style>
  @page { margin: 1.5cm; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color:#0b2432; max-width: 720px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .04em; color:#12506f; margin: 18px 0 6px; border-bottom:1px solid #cfe0e8; padding-bottom:3px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #cfe0e8; padding: 4px 8px; text-align: left; }
  .grid { display:flex; gap:24px; font-size:13px; }
  .grid div { flex:1; }
  .meta { color:#4a6b7a; font-size: 11px; margin-top: 4px; }
  .disclaimer { margin-top: 22px; padding-top: 10px; border-top: 1px solid #cfe0e8; font-size: 11px; color:#4a6b7a; }
  .badge { display:inline-block; background:#fce6cf; color:#9a5b1e; font-size:10px; font-weight:700; padding:2px 8px; border-radius:999px; }
</style></head>
<body>
  <h1>${esc(title[language])}${plan.name ? ` — ${esc(plan.name)}` : ''}</h1>
  <div class="meta">${esc(L.generated)}: ${esc(formatLocalShort(new Date().toISOString()))} · <span class="badge">${esc(L.demo)}</span></div>

  <div class="grid" style="margin-top:14px">
    <div><strong>${esc(L.eta)}</strong><br/>${plan.eta_hours.toFixed(1)} h</div>
    <div><strong>${esc(L.fuel)}</strong><br/>${plan.fuel_est_l.toFixed(0)} L</div>
    <div><strong>${esc(L.maxWave)}</strong><br/>${plan.max_wave_m.toFixed(1)} m</div>
    <div><strong>${esc(L.effort)}</strong><br/>${plan.effort_proxy.toFixed(2)}</div>
  </div>

  <h2>${esc(L.route)}</h2>
  <table><thead><tr><th>#</th><th>lat</th><th>lon</th></tr></thead><tbody>${waypoints}</tbody></table>

  <h2>${esc(L.zones)}</h2>
  ${zones}

  <h2>${esc(L.weather)}</h2>
  ${weather}

  <p class="disclaimer">${esc(DISCLAIMER[language])}</p>
</body></html>`;
}

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => {
    switch (c) {
      case '&':
        return '&amp;';
      case '<':
        return '&lt;';
      case '>':
        return '&gt;';
      case '"':
        return '&quot;';
      default:
        return '&#39;';
    }
  });
}
