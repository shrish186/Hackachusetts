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
  tryDemo: string;
  tryDemoHint: string;
  summary: string;
  printBrief: string;
  // manager mode
  simTitle: string;
  simIntro: string;
  scenarios: string;
  drawZone: string;
  finishZone: string;
  clearZone: string;
  drawHint: string;
  runSim: string;
  running: string;
  efficient: string;
  riskReduced: string;
  fleetCost: string;
  deltaRisk: string;
  deltaEffort: string;
  deltaHours: string;
  deltaFuel: string;
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
    tryDemo: 'Try the demo trip',
    tryDemoHint: 'Pre-fill Gloucester, small boat, 9 kn, 12 h, morning departure, safest',
    summary: 'Summary',
    printBrief: 'Print brief',
    simTitle: 'What-if simulator',
    simIntro: 'Compare candidate protection zones: whale strikes removed vs. the cost to the fleet. Highlighted options are on the efficient frontier.',
    scenarios: 'Scenarios',
    drawZone: 'Draw candidate zone',
    finishZone: 'Finish',
    clearZone: 'Clear',
    drawHint: 'Click the map to add corners. Finish when you have 3+.',
    runSim: 'Run simulation',
    running: 'Re-routing fleet…',
    efficient: 'efficient',
    riskReduced: 'Risk removed',
    fleetCost: 'Fleet cost',
    deltaRisk: 'Risk',
    deltaEffort: 'Fishing access',
    deltaHours: 'Steaming hrs',
    deltaFuel: 'Fuel',
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
    tryDemo: 'Testar viagem demo',
    tryDemoHint: 'Preenche Gloucester, barco pequeno, 9 nós, 12 h, partida de manhã, mais seguro',
    summary: 'Resumo',
    printBrief: 'Imprimir resumo',
    simTitle: 'Simulador hipotético',
    simIntro: 'Compare zonas de proteção candidatas: colisões com baleias evitadas vs. o custo para a frota. As opções destacadas estão na fronteira eficiente.',
    scenarios: 'Cenários',
    drawZone: 'Desenhar zona candidata',
    finishZone: 'Concluir',
    clearZone: 'Limpar',
    drawHint: 'Clique no mapa para adicionar cantos. Conclua com 3 ou mais.',
    runSim: 'Executar simulação',
    running: 'Redirecionando a frota…',
    efficient: 'eficiente',
    riskReduced: 'Risco removido',
    fleetCost: 'Custo da frota',
    deltaRisk: 'Risco',
    deltaEffort: 'Acesso à pesca',
    deltaHours: 'Horas de navegação',
    deltaFuel: 'Combustível',
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
    tryDemo: 'Probar viaje demo',
    tryDemoHint: 'Rellena Gloucester, bote pequeño, 9 nudos, 12 h, salida por la mañana, más seguro',
    summary: 'Resumen',
    printBrief: 'Imprimir resumen',
    simTitle: 'Simulador hipotético',
    simIntro: 'Compara zonas de protección candidatas: choques con ballenas evitados vs. el costo para la flota. Las opciones resaltadas están en la frontera eficiente.',
    scenarios: 'Escenarios',
    drawZone: 'Dibujar zona candidata',
    finishZone: 'Finalizar',
    clearZone: 'Borrar',
    drawHint: 'Haz clic en el mapa para añadir esquinas. Finaliza con 3 o más.',
    runSim: 'Ejecutar simulación',
    running: 'Redirigiendo la flota…',
    efficient: 'eficiente',
    riskReduced: 'Riesgo eliminado',
    fleetCost: 'Costo de flota',
    deltaRisk: 'Riesgo',
    deltaEffort: 'Acceso a pesca',
    deltaHours: 'Horas de navegación',
    deltaFuel: 'Combustible',
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
