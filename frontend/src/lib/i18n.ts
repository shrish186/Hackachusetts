import type { Language } from '@/api/types';

/**
 * Lightweight i18n for Captain-facing plan text (requirements.md Req 7).
 *
 * Only *words* are translated. Numbers, coordinates, and zone names are passed
 * through verbatim so they are identical across English, Portuguese, and
 * Spanish (data-and-safety steering + Req 7.2). Keep the reading level simple
 * (product steering: grade ~8, short sentences).
 */

export const LANGUAGES: { id: Language; label: string; flag: string }[] = [
  { id: 'en', label: 'English', flag: 'EN' },
  { id: 'pt', label: 'Português', flag: 'PT' },
  { id: 'es', label: 'Español', flag: 'ES' },
];

interface Strings {
  planTripTitle: string;
  port: string;
  vessel: string;
  cruiseSpeed: string;
  maxHours: string;
  departure: string;
  fastest: string;
  safest: string;
  planRoutes: string;
  planning: string;
  checking: string;
  agentFeedTitle: string;
  option: string;
  recommended: string;
  risk: string;
  eta: string;
  fuelEst: string;
  maxWave: string;
  effortEst: string;
  why: string;
  hide: string;
  zonesCrossed: string;
  noZones: string;
  riskSummary: string;
  weatherWindow: string;
  citations: string;
  showOnMap: string;
  shownOnMap: string;
  effortNote: string;
  language: string;
  hours: string;
  knots: string;
  liters: string;
  meters: string;
  // vessel labels
  small_boat: string;
  mid_trawler: string;
  scalloper: string;
  // units / phrases for narrative
  riskLevelLow: string;
  riskLevelModerate: string;
  riskLevelHigh: string;
}

const STRINGS: Record<Language, Strings> = {
  en: {
    planTripTitle: 'Plan a trip',
    port: 'Port',
    vessel: 'Vessel',
    cruiseSpeed: 'Cruise speed',
    maxHours: 'Max hours',
    departure: 'Departure',
    fastest: 'Fastest',
    safest: 'Safest',
    planRoutes: 'Plan routes',
    planning: 'Planning…',
    checking: 'Working…',
    agentFeedTitle: 'What the assistant checked',
    option: 'Option',
    recommended: 'recommended',
    risk: 'risk',
    eta: 'ETA',
    fuelEst: 'Fuel (est.)',
    maxWave: 'Max wave',
    effortEst: 'Fishing access (est.)',
    why: 'Why',
    hide: 'Hide',
    zonesCrossed: 'Zones crossed',
    noZones: 'Avoids all known closures and managed zones.',
    riskSummary: 'Whale risk',
    weatherWindow: 'Weather window',
    citations: 'Sources',
    showOnMap: 'Show on map',
    shownOnMap: 'Shown on map',
    effortNote: 'Fishing access is an estimate, not catch or revenue.',
    language: 'Language',
    hours: 'h',
    knots: 'kn',
    liters: 'L',
    meters: 'm',
    small_boat: 'Small boat',
    mid_trawler: 'Mid trawler',
    scalloper: 'Scalloper',
    riskLevelLow: 'low',
    riskLevelModerate: 'moderate',
    riskLevelHigh: 'high',
  },
  pt: {
    planTripTitle: 'Planejar uma viagem',
    port: 'Porto',
    vessel: 'Embarcação',
    cruiseSpeed: 'Velocidade de cruzeiro',
    maxHours: 'Horas máx.',
    departure: 'Partida',
    fastest: 'Mais rápido',
    safest: 'Mais seguro',
    planRoutes: 'Planejar rotas',
    planning: 'Planejando…',
    checking: 'Trabalhando…',
    agentFeedTitle: 'O que o assistente verificou',
    option: 'Opção',
    recommended: 'recomendado',
    risk: 'risco',
    eta: 'ETA',
    fuelEst: 'Combustível (est.)',
    maxWave: 'Onda máx.',
    effortEst: 'Acesso à pesca (est.)',
    why: 'Por quê',
    hide: 'Ocultar',
    zonesCrossed: 'Zonas cruzadas',
    noZones: 'Evita todos os fechamentos e zonas conhecidas.',
    riskSummary: 'Risco de baleia',
    weatherWindow: 'Janela do tempo',
    citations: 'Fontes',
    showOnMap: 'Mostrar no mapa',
    shownOnMap: 'Mostrado no mapa',
    effortNote: 'O acesso à pesca é uma estimativa, não captura nem receita.',
    language: 'Idioma',
    hours: 'h',
    knots: 'nós',
    liters: 'L',
    meters: 'm',
    small_boat: 'Barco pequeno',
    mid_trawler: 'Arrastão médio',
    scalloper: 'Barco de vieiras',
    riskLevelLow: 'baixo',
    riskLevelModerate: 'moderado',
    riskLevelHigh: 'alto',
  },
  es: {
    planTripTitle: 'Planificar un viaje',
    port: 'Puerto',
    vessel: 'Embarcación',
    cruiseSpeed: 'Velocidad de crucero',
    maxHours: 'Horas máx.',
    departure: 'Salida',
    fastest: 'Más rápido',
    safest: 'Más seguro',
    planRoutes: 'Planificar rutas',
    planning: 'Planificando…',
    checking: 'Trabajando…',
    agentFeedTitle: 'Lo que revisó el asistente',
    option: 'Opción',
    recommended: 'recomendado',
    risk: 'riesgo',
    eta: 'ETA',
    fuelEst: 'Combustible (est.)',
    maxWave: 'Ola máx.',
    effortEst: 'Acceso a pesca (est.)',
    why: 'Por qué',
    hide: 'Ocultar',
    zonesCrossed: 'Zonas cruzadas',
    noZones: 'Evita todos los cierres y zonas conocidas.',
    riskSummary: 'Riesgo de ballena',
    weatherWindow: 'Ventana del tiempo',
    citations: 'Fuentes',
    showOnMap: 'Mostrar en el mapa',
    shownOnMap: 'Mostrado en el mapa',
    effortNote: 'El acceso a la pesca es una estimación, no captura ni ingresos.',
    language: 'Idioma',
    hours: 'h',
    knots: 'nudos',
    liters: 'L',
    meters: 'm',
    small_boat: 'Bote pequeño',
    mid_trawler: 'Arrastrero mediano',
    scalloper: 'Barco vieiras',
    riskLevelLow: 'bajo',
    riskLevelModerate: 'moderado',
    riskLevelHigh: 'alto',
  },
};

export function t(lang: Language): Strings {
  return STRINGS[lang];
}

/** Bucket a 0..1 risk exposure into a translated level word. */
export function riskLevelWord(lang: Language, exposure: number): string {
  const s = STRINGS[lang];
  if (exposure < 0.2) return s.riskLevelLow;
  if (exposure < 0.4) return s.riskLevelModerate;
  return s.riskLevelHigh;
}

/** Advisory-only disclaimer, per language (requirements.md Req 9.1). */
export const DISCLAIMER: Record<Language, string> = {
  en: 'Advisory only. Does not replace official notices, VHF warnings, or the captain’s judgment.',
  pt: 'Apenas informativo. Não substitui avisos oficiais, alertas de VHF nem o julgamento do capitão.',
  es: 'Solo informativo. No reemplaza avisos oficiales, alertas de VHF ni el criterio del capitán.',
};
