import { useEffect, useRef, useState } from 'react';
import { useConn } from '@/hooks/useConn';
import { useAppState } from '@/state/AppState';
import type { Language } from '@/api/types';

interface DemoBadgeProps {
  /** True when the backend reports demo mode (bundled snapshots). */
  demoMode: boolean;
}

/** Honest provenance strings (EN/PT/ES) — item D. */
const PROV: Record<Language, {
  label: string;
  offline: string;
  waking: string;
  live: string;
  liveTitle: string;
  heading: string;
  liveHead: string;
  realHead: string;
  modelHead: string;
  liveItems: string;
  realItems: string;
  modelItems: string;
}> = {
  en: {
    label: 'Live NOAA data + modelled zones',
    offline: 'Offline — bundled data',
    waking: 'Waking server…',
    live: 'Live NOAA data + modelled zones',
    liveTitle: 'Connected to the live Fathom API.',
    heading: 'What is real, and what is modelled',
    liveHead: 'Live',
    realHead: 'Real records',
    modelHead: 'Modelled',
    liveItems: 'NOAA buoys 44013 / 44029, NWS marine forecast, eMOLT bottom temperature.',
    realItems: '60 OBIS right-whale sightings; NOAA seasonal management area dates and the 10 kn rule.',
    modelItems: 'Zone polygon shapes, the whale-risk model, and the 200-trip synthetic fleet.',
  },
  pt: {
    label: 'Dados NOAA ao vivo + zonas modeladas',
    offline: 'Offline — dados incluídos',
    waking: 'Acordando o servidor…',
    live: 'Dados NOAA ao vivo + zonas modeladas',
    liveTitle: 'Conectado à API Fathom ao vivo.',
    heading: 'O que é real e o que é modelado',
    liveHead: 'Ao vivo',
    realHead: 'Registos reais',
    modelHead: 'Modelado',
    liveItems: 'Boias NOAA 44013 / 44029, previsão marinha NWS, temperatura de fundo eMOLT.',
    realItems: '60 avistamentos de baleia-franca da OBIS; datas das áreas de gestão sazonal da NOAA e a regra de 10 nós.',
    modelItems: 'Formas dos polígonos das zonas, o modelo de risco de baleia e a frota sintética de 200 viagens.',
  },
  es: {
    label: 'Datos NOAA en vivo + zonas modeladas',
    offline: 'Sin conexión — datos incluidos',
    waking: 'Despertando el servidor…',
    live: 'Datos NOAA en vivo + zonas modeladas',
    liveTitle: 'Conectado a la API de Fathom en vivo.',
    heading: 'Qué es real y qué está modelado',
    liveHead: 'En vivo',
    realHead: 'Registros reales',
    modelHead: 'Modelado',
    liveItems: 'Boyas NOAA 44013 / 44029, pronóstico marino NWS, temperatura de fondo eMOLT.',
    realItems: '60 avistamientos de ballena franca de OBIS; fechas de las áreas de gestión estacional de NOAA y la regla de 10 nudos.',
    modelItems: 'Formas de los polígonos de zonas, el modelo de riesgo de ballena y la flota sintética de 200 viajes.',
  },
};

/**
 * Connection / data-provenance badge (requirements.md Req 10.2, audit item D).
 *
 * Replaces the old "Demo data" label with an honest neutral label — "Live NOAA
 * data + modelled zones" — that opens a popover listing exactly what is live,
 * what is a real record, and what is modelled. It never hides the modelled
 * parts. EN/PT/ES.
 */
export function DemoBadge({ demoMode }: DemoBadgeProps) {
  const conn = useConn();
  const { language } = useAppState();
  const s = PROV[language];

  if (conn === 'offline') {
    return <Badge tone="alert" label={s.offline} title={s.offline} />;
  }
  if (conn === 'waking') {
    return <Badge tone="mist" label={s.waking} title={s.waking} />;
  }
  // API up (demo mode OR live): the data is honestly "live NOAA + modelled
  // zones" either way, so show the same honest label with the provenance popover.
  if (demoMode || conn === 'online') {
    return <ProvenanceBadge strings={s} />;
  }
  return null;
}

function ProvenanceBadge({ strings: s }: { strings: (typeof PROV)[Language] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={s.liveTitle}
        className="inline-flex items-center gap-1.5 rounded-full border border-tide/50 bg-tide/15 px-3 py-1 text-xs font-semibold tracking-wide text-foam hover:bg-tide/25"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-kelp" />
        {s.label}
        <span aria-hidden className="ml-0.5 text-mist">ⓘ</span>
      </button>
      {open && (
        <div
          role="dialog"
          aria-label={s.heading}
          className="absolute right-0 z-50 mt-2 w-72 rounded-xl border border-depth bg-deep/95 p-3 text-xs leading-relaxed text-mist shadow-xl backdrop-blur"
        >
          <p className="mb-2 font-bold text-foam">{s.heading}</p>
          <p className="mb-1"><span className="font-semibold text-kelp">{s.liveHead}:</span> {s.liveItems}</p>
          <p className="mb-1"><span className="font-semibold text-surf">{s.realHead}:</span> {s.realItems}</p>
          <p><span className="font-semibold text-coral">{s.modelHead}:</span> {s.modelItems}</p>
        </div>
      )}
    </div>
  );
}

function Badge({
  tone,
  label,
  title,
}: {
  tone: 'alert' | 'mist';
  label: string;
  title: string;
}) {
  const tones: Record<string, string> = {
    alert: 'border-alert/50 bg-alert/15 text-alert',
    mist: 'border-depth bg-deep/80 text-mist',
  };
  const dot: Record<string, string> = { alert: 'bg-alert', mist: 'bg-mist' };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${tones[tone]}`}
      title={title}
      role="status"
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot[tone]}`} />
      {label}
    </span>
  );
}
