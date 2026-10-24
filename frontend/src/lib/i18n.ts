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
  portPlaceholder: string;
  pickPort: string;
  ground: string;
  anyGround: string;
  groundPlaceholder: string;
  closedPrefix: string; // "Closed" word for the chip
  copyLink: string;
  linkCopied: string;
  about: string;
  aboutWhatTitle: string;
  aboutWhatBody: string;
  aboutDataTitle: string;
  aboutKiroTitle: string;
  aboutKiroBody: string;
  aboutLimitsTitle: string;
  aboutLimitsBody: string;
  aboutTeamTitle: string;
  aboutBack: string;
  colLayer: string;
  colSource: string;
  colKind: string;
  colFetched: string;
  colLicense: string;
  real: string;
  synthetic: string;
  comparedWith: string; // "Compared with Fastest:"
  avoidsClosures: string; // "avoids {n} closure(s)"
  avoidsNoClosures: string; // "avoids no extra closures"
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
  planningCold: string; // cold-start spinner text (item 5)
  // replay whale season (item 1)
  today: string;
  replayWhaleSeason: string;
  replayBanner: string;
  // plan card clarity (task 10)
  fastestLabel: string;
  balancedLabel: string;
  safestLabel: string;
  alternativeLabel: string; // "Alternative" (item 2)
  advisoryShort: string;
  bundledDemoData: string;
  singleRouteNote: string;
  vsFastest: string; // "vs fastest"
  lessRisk: string; // "less whale risk"
  moreRisk: string; // "more whale risk"
  // access lost (item 4)
  accessLostTitle: string; // "Your target ground is closed on this date:"
  nearestOpen: string; // "Nearest open water:"
  planToNearest: string; // button
  accessLostTrips: string; // "trips lose access"
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
  cancel: string;
  simProgress: string;
  simTimeout: string;
  simBusy: string;
  simSlow: string;
  simError: string;
  retry: string;
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
    portPlaceholder: 'Search a port…',
    pickPort: 'Pick a port from the list',
    ground: 'Target ground',
    anyGround: 'Any ground',
    groundPlaceholder: 'Search a ground…',
    closedPrefix: 'Closed',
    copyLink: 'Copy link',
    linkCopied: 'Link copied',
    about: 'About',
    aboutWhatTitle: 'What Fathom does',
    aboutWhatBody:
      'Fathom is an advisory ocean decision copilot for Massachusetts captains and fisheries managers. It fuses weather, protection zones, and a whale-strike risk model into ranked, legal trip plans and a what-if simulator — balancing right-whale protection with fishing livelihoods.',
    aboutDataTitle: 'Data sources',
    aboutKiroTitle: 'How we used Kiro',
    aboutKiroBody:
      'Built spec-first with Kiro: requirements, design, and tasks specs; steering files for tech and product rules; agent hooks (citation guard, evidence log); an MCP server exposing the data/risk/route tools; and property-based tests for the risk and routing invariants.',
    aboutLimitsTitle: 'Limits',
    aboutLimitsBody:
      'Advisory only — never a substitute for official notices, VHF warnings, or the captain’s judgment. Zone polygons are hand-drawn approximations (their dates are real). The demo uses ~60 recent whale sightings. The effort proxy is an estimate, not catch or revenue.',
    aboutTeamTitle: 'Team',
    aboutBack: 'Back to the map',
    colLayer: 'Layer',
    colSource: 'Source',
    colKind: 'Real / synthetic',
    colFetched: 'Fetched',
    colLicense: 'License',
    real: 'Real',
    synthetic: 'Synthetic',
    comparedWith: 'Compared with Fastest:',
    avoidsClosures: 'avoids {n} closure(s)',
    avoidsNoClosures: 'no extra closures avoided',
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
    tryDemoHint: 'Pre-fill Gloucester, small boat, 9 kn, 12 h, replay whale season, safest',
    summary: 'Summary',
    printBrief: 'Print brief',
    planningCold: 'Planning routes… (the free server may take up to 60 s the first time)',
    today: 'Today',
    replayWhaleSeason: 'Replay whale season (15 Mar 2026)',
    replayBanner: 'Replaying 15 Mar 2026: whale-season closures are active',
    fastestLabel: 'Fastest',
    balancedLabel: 'Balanced',
    safestLabel: 'Safest',
    alternativeLabel: 'Alternative',
    advisoryShort: 'Advisory only',
    bundledDemoData: 'bundled demo data',
    singleRouteNote: 'Only one safe, legal route fits these limits. Relax max hours or the risk setting to see alternatives.',
    vsFastest: 'vs fastest',
    lessRisk: 'less whale risk',
    moreRisk: 'more whale risk',
    accessLostTitle: 'Your target ground is closed on this date:',
    nearestOpen: 'Nearest open water:',
    planToNearest: 'Plan to nearest open water',
    accessLostTrips: 'trips lose access to closed grounds',
    simTitle: 'What-if simulator',
    simIntro: 'Compare candidate protection zones: whale strikes removed vs. the cost to the fleet. Highlighted options are on the efficient frontier.',
    scenarios: 'Scenarios',
    drawZone: 'Draw candidate zone',
    finishZone: 'Finish',
    clearZone: 'Clear',
    drawHint: 'Click the map to add corners. Finish when you have 3+.',
    runSim: 'Run simulation',
    running: 'Re-routing fleet…',
    cancel: 'Cancel',
    simProgress: 'Re-routing ~200 trips (can take up to a minute)…',
    simTimeout: 'The simulation took too long. The free server may be busy — try again.',
    simBusy: 'Server busy — retry shortly.',
    simSlow: 'The server timed out. Try again in a moment.',
    simError: 'Could not run the simulation. Showing sample numbers.',
    retry: 'Retry',
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
    portPlaceholder: 'Buscar um porto…',
    pickPort: 'Escolha um porto da lista',
    ground: 'Pesqueiro-alvo',
    anyGround: 'Qualquer pesqueiro',
    groundPlaceholder: 'Buscar um pesqueiro…',
    closedPrefix: 'Fechado',
    copyLink: 'Copiar link',
    linkCopied: 'Link copiado',
    about: 'Sobre',
    aboutWhatTitle: 'O que o Fathom faz',
    aboutWhatBody:
      'O Fathom é um copiloto consultivo para capitães e gestores de pesca de Massachusetts. Reúne clima, zonas de proteção e um modelo de risco de colisão com baleias em planos de viagem legais e ranqueados e um simulador hipotético — equilibrando a proteção das baleias com o sustento da pesca.',
    aboutDataTitle: 'Fontes de dados',
    aboutKiroTitle: 'Como usamos o Kiro',
    aboutKiroBody:
      'Construído com especificações primeiro no Kiro: specs de requisitos, design e tarefas; arquivos de steering para regras de tecnologia e produto; hooks de agente (guarda de citações, registro de evidências); um servidor MCP expondo as ferramentas de dados/risco/rota; e testes baseados em propriedades para os invariantes de risco e rota.',
    aboutLimitsTitle: 'Limites',
    aboutLimitsBody:
      'Apenas informativo — nunca substitui avisos oficiais, alertas de VHF ou o julgamento do capitão. Os polígonos das zonas são aproximações desenhadas à mão (as datas são reais). A demo usa ~60 avistamentos recentes de baleias. O proxy de esforço é uma estimativa, não captura nem receita.',
    aboutTeamTitle: 'Equipe',
    aboutBack: 'Voltar ao mapa',
    colLayer: 'Camada',
    colSource: 'Fonte',
    colKind: 'Real / sintético',
    colFetched: 'Obtido em',
    colLicense: 'Licença',
    real: 'Real',
    synthetic: 'Sintético',
    comparedWith: 'Comparado com Mais rápida:',
    avoidsClosures: 'evita {n} fechamento(s)',
    avoidsNoClosures: 'nenhum fechamento extra evitado',
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
    tryDemoHint: 'Preenche Gloucester, barco pequeno, 9 nós, 12 h, repetir temporada de baleias, mais seguro',
    summary: 'Resumo',
    printBrief: 'Imprimir resumo',
    planningCold: 'Planejando rotas… (o servidor gratuito pode levar até 60 s na primeira vez)',
    today: 'Hoje',
    replayWhaleSeason: 'Repetir temporada de baleias (15 mar 2026)',
    replayBanner: 'Repetindo 15 mar 2026: fechamentos da temporada de baleias ativos',
    fastestLabel: 'Mais rápida',
    balancedLabel: 'Equilibrada',
    safestLabel: 'Mais segura',
    alternativeLabel: 'Alternativa',
    advisoryShort: 'Apenas informativo',
    bundledDemoData: 'dados demo incluídos',
    singleRouteNote: 'Só uma rota segura e legal cabe nestes limites. Aumente as horas máximas ou ajuste o risco para ver alternativas.',
    accessLostTitle: 'Seu pesqueiro-alvo está fechado nesta data:',
    nearestOpen: 'Água aberta mais próxima:',
    planToNearest: 'Planejar para a água aberta mais próxima',
    accessLostTrips: 'viagens perdem acesso a pesqueiros fechados',
    vsFastest: 'vs. mais rápida',
    lessRisk: 'menos risco de baleia',
    moreRisk: 'mais risco de baleia',
    simTitle: 'Simulador hipotético',
    simIntro: 'Compare zonas de proteção candidatas: colisões com baleias evitadas vs. o custo para a frota. As opções destacadas estão na fronteira eficiente.',
    scenarios: 'Cenários',
    drawZone: 'Desenhar zona candidata',
    finishZone: 'Concluir',
    clearZone: 'Limpar',
    drawHint: 'Clique no mapa para adicionar cantos. Conclua com 3 ou mais.',
    runSim: 'Executar simulação',
    running: 'Redirecionando a frota…',
    cancel: 'Cancelar',
    simProgress: 'Redirecionando ~200 viagens (pode levar até um minuto)…',
    simTimeout: 'A simulação demorou demais. O servidor gratuito pode estar ocupado — tente de novo.',
    simBusy: 'Servidor ocupado — tente novamente em breve.',
    simSlow: 'O servidor expirou. Tente novamente em instantes.',
    simError: 'Não foi possível executar a simulação. Mostrando números de exemplo.',
    retry: 'Tentar novamente',
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
    portPlaceholder: 'Buscar un puerto…',
    pickPort: 'Elige un puerto de la lista',
    ground: 'Zona objetivo',
    anyGround: 'Cualquier zona',
    groundPlaceholder: 'Buscar una zona…',
    closedPrefix: 'Cerrado',
    copyLink: 'Copiar enlace',
    linkCopied: 'Enlace copiado',
    about: 'Acerca de',
    aboutWhatTitle: 'Qué hace Fathom',
    aboutWhatBody:
      'Fathom es un copiloto consultivo para capitanes y gestores pesqueros de Massachusetts. Combina clima, zonas de protección y un modelo de riesgo de choque con ballenas en planes de viaje legales y clasificados y un simulador hipotético, equilibrando la protección de las ballenas con el sustento pesquero.',
    aboutDataTitle: 'Fuentes de datos',
    aboutKiroTitle: 'Cómo usamos Kiro',
    aboutKiroBody:
      'Construido con especificaciones primero en Kiro: specs de requisitos, diseño y tareas; archivos de steering para reglas de tecnología y producto; hooks de agente (guardia de citas, registro de evidencia); un servidor MCP que expone las herramientas de datos/riesgo/ruta; y pruebas basadas en propiedades para los invariantes de riesgo y ruta.',
    aboutLimitsTitle: 'Límites',
    aboutLimitsBody:
      'Solo informativo — nunca sustituye avisos oficiales, alertas de VHF ni el criterio del capitán. Los polígonos de zonas son aproximaciones dibujadas a mano (sus fechas son reales). La demo usa ~60 avistamientos recientes de ballenas. El proxy de esfuerzo es una estimación, no captura ni ingresos.',
    aboutTeamTitle: 'Equipo',
    aboutBack: 'Volver al mapa',
    colLayer: 'Capa',
    colSource: 'Fuente',
    colKind: 'Real / sintético',
    colFetched: 'Obtenido',
    colLicense: 'Licencia',
    real: 'Real',
    synthetic: 'Sintético',
    comparedWith: 'Comparado con Más rápida:',
    avoidsClosures: 'evita {n} cierre(s)',
    avoidsNoClosures: 'ningún cierre adicional evitado',
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
    tryDemoHint: 'Rellena Gloucester, bote pequeño, 9 nudos, 12 h, repetir temporada de ballenas, más seguro',
    summary: 'Resumen',
    printBrief: 'Imprimir resumen',
    planningCold: 'Planificando rutas… (el servidor gratuito puede tardar hasta 60 s la primera vez)',
    today: 'Hoy',
    replayWhaleSeason: 'Repetir temporada de ballenas (15 mar 2026)',
    replayBanner: 'Repitiendo 15 mar 2026: los cierres de temporada de ballenas están activos',
    fastestLabel: 'Más rápida',
    balancedLabel: 'Equilibrada',
    safestLabel: 'Más segura',
    alternativeLabel: 'Alternativa',
    advisoryShort: 'Solo informativo',
    bundledDemoData: 'datos demo incluidos',
    singleRouteNote: 'Solo una ruta segura y legal cabe en estos límites. Aumenta las horas máximas o ajusta el riesgo para ver alternativas.',
    accessLostTitle: 'Tu zona de pesca objetivo está cerrada en esta fecha:',
    nearestOpen: 'Agua abierta más cercana:',
    planToNearest: 'Planificar a la agua abierta más cercana',
    accessLostTrips: 'viajes pierden acceso a zonas cerradas',
    vsFastest: 'vs. más rápida',
    lessRisk: 'menos riesgo de ballena',
    moreRisk: 'más riesgo de ballena',
    simTitle: 'Simulador hipotético',
    simIntro: 'Compara zonas de protección candidatas: choques con ballenas evitados vs. el costo para la flota. Las opciones resaltadas están en la frontera eficiente.',
    scenarios: 'Escenarios',
    drawZone: 'Dibujar zona candidata',
    finishZone: 'Finalizar',
    clearZone: 'Borrar',
    drawHint: 'Haz clic en el mapa para añadir esquinas. Finaliza con 3 o más.',
    runSim: 'Ejecutar simulación',
    running: 'Redirigiendo la flota…',
    cancel: 'Cancelar',
    simProgress: 'Redirigiendo ~200 viajes (puede tardar hasta un minuto)…',
    simTimeout: 'La simulación tardó demasiado. El servidor gratuito puede estar ocupado — inténtalo de nuevo.',
    simBusy: 'Servidor ocupado — reintenta en breve.',
    simSlow: 'El servidor expiró. Inténtalo de nuevo en un momento.',
    simError: 'No se pudo ejecutar la simulación. Mostrando números de ejemplo.',
    retry: 'Reintentar',
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

/** Plain plan-class label (Fastest / Balanced / Safest / Alternative). */
export function planClassLabel(
  lang: Language,
  cls: 'fastest' | 'balanced' | 'safest' | 'alternative',
): string {
  const s = STRINGS[lang];
  if (cls === 'fastest') return s.fastestLabel;
  if (cls === 'safest') return s.safestLabel;
  if (cls === 'alternative') return s.alternativeLabel;
  return s.balancedLabel;
}

/**
 * One-line trade-off vs the fastest plan, e.g. "+40 min, 55% less whale risk"
 * (task 10). Numbers are language-neutral; only words translate.
 */
export function tradeoffLine(
  lang: Language,
  deltaMinutes: number,
  riskChangePct: number,
): string {
  const s = STRINGS[lang];
  const timePart =
    deltaMinutes <= 0 ? '' : `+${Math.round(deltaMinutes)} min`;
  const absRisk = Math.abs(Math.round(riskChangePct));
  const riskWord = riskChangePct <= 0 ? s.lessRisk : s.moreRisk;
  const riskPart = `${absRisk}% ${riskWord}`;
  return timePart ? `${timePart}, ${riskPart}` : riskPart;
}

/** Advisory-only disclaimer, per language (requirements.md Req 9.1). */
export const DISCLAIMER: Record<Language, string> = {
  en: 'Advisory only. Does not replace official notices, VHF warnings, or the captain’s judgment.',
  pt: 'Apenas informativo. Não substitui avisos oficiais, alertas de VHF nem o julgamento do capitão.',
  es: 'Solo informativo. No reemplaza avisos oficiales, alertas de VHF ni el criterio del capitán.',
};
