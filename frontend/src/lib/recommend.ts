import type { RoutePlan } from '@/api/types';

/**
 * Pick the "recommended" plan with a single scoring function used for BOTH
 * live and mock data (task 5). The captain's risk-vs-speed preference
 * (`risk_pref`, 0 = fastest, 1 = safest) sets how much whale-strike risk
 * matters relative to ETA and fuel.
 *
 * Each metric is normalized to [0,1] across the candidate plans (min = best),
 * then combined into a cost where LOWER is better:
 *
 *   cost = w_risk * riskN + w_time * etaN + w_fuel * fuelN
 *   w_risk = 0.15 + 0.80 * risk_pref        (0.15 … 0.95)
 *   w_time = (1 - risk_pref) * 0.70         (0.70 … 0)
 *   w_fuel = (1 - risk_pref) * 0.30         (0.30 … 0)
 *
 * So at risk_pref = 0.8 the safest/lowest-risk route wins; at risk_pref = 0
 * the fastest/cheapest route wins. The recommended plan is the lowest cost.
 */
export function scorePlan(
  plan: RoutePlan,
  riskPref: number,
  ranges: { risk: Range; eta: Range; fuel: Range },
): number {
  const rp = clamp01(riskPref);
  const wRisk = 0.15 + 0.8 * rp;
  const wTime = (1 - rp) * 0.7;
  const wFuel = (1 - rp) * 0.3;

  const riskN = norm(plan.risk_exposure, ranges.risk);
  const etaN = norm(plan.eta_hours, ranges.eta);
  const fuelN = norm(plan.fuel_est_l, ranges.fuel);

  return wRisk * riskN + wTime * etaN + wFuel * fuelN;
}

export interface Range {
  min: number;
  max: number;
}

function metricRange(values: number[]): Range {
  return { min: Math.min(...values), max: Math.max(...values) };
}

function norm(v: number, r: Range): number {
  if (r.max === r.min) return 0; // all equal -> neutral
  return (v - r.min) / (r.max - r.min);
}

function clamp01(n: number): number {
  return Math.max(0, Math.min(1, n));
}

/**
 * Index of the recommended plan given the captain's risk preference.
 * Returns -1 for an empty list. Ties resolve to the earlier plan.
 */
export function recommendedIndex(plans: RoutePlan[], riskPref: number): number {
  if (plans.length === 0) return -1;
  if (plans.length === 1) return 0;

  const ranges = {
    risk: metricRange(plans.map((p) => p.risk_exposure)),
    eta: metricRange(plans.map((p) => p.eta_hours)),
    fuel: metricRange(plans.map((p) => p.fuel_est_l)),
  };

  let best = 0;
  let bestScore = Infinity;
  plans.forEach((p, i) => {
    const score = scorePlan(p, riskPref, ranges);
    if (score < bestScore - 1e-9) {
      bestScore = score;
      best = i;
    }
  });
  return best;
}

export type PlanClass = 'fastest' | 'balanced' | 'safest' | 'alternative';

/**
 * Classify each plan as Fastest / Safest / Balanced / Alternative for a plain
 * label (task 10, item 2). Fastest = lowest ETA, Safest = lowest risk; a plan
 * the backend named "Alternate track …" is "alternative"; the rest Balanced.
 */
export function classifyPlans(plans: RoutePlan[]): PlanClass[] {
  if (plans.length === 0) return [];

  let fastest = 0;
  let safest = 0;
  plans.forEach((p, i) => {
    if (p.eta_hours < plans[fastest].eta_hours) fastest = i;
    if (p.risk_exposure < plans[safest].risk_exposure) safest = i;
  });

  return plans.map((p, i) => {
    if (/alternate/i.test(p.name ?? '')) return 'alternative';
    if (plans.length === 1) return 'balanced';
    if (i === safest && safest !== fastest) return 'safest';
    if (i === fastest) return 'fastest';
    return 'balanced';
  });
}

/**
 * Sort plans into the display order Fastest, Balanced, Safest, Alternative
 * (item 2): primarily by ETA ascending, but any "Alternate track" plan is
 * pushed to the end. Returns a new array; does not mutate the input.
 */
export function sortPlans(plans: RoutePlan[]): RoutePlan[] {
  const isAlt = (p: RoutePlan) => /alternate/i.test(p.name ?? '');
  return [...plans].sort((a, b) => {
    const aAlt = isAlt(a) ? 1 : 0;
    const bAlt = isAlt(b) ? 1 : 0;
    if (aAlt !== bAlt) return aAlt - bAlt; // alternates last
    return a.eta_hours - b.eta_hours; // fastest first
  });
}
