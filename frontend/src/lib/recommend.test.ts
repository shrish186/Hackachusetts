import { describe, it, expect } from 'vitest';
import { recommendedIndex, classifyPlans } from './recommend';
import type { RoutePlan } from '@/api/types';

function plan(over: Partial<RoutePlan>): RoutePlan {
  return {
    name: 'x',
    waypoints: [[-70, 42], [-70.1, 42.3]],
    eta_hours: 4,
    fuel_est_l: 200,
    zones_crossed: [],
    max_wave_m: 1.5,
    risk_exposure: 0.3,
    effort_proxy: 0.6,
    citations: [],
    ...over,
  };
}

// The three mock routes (Direct / Eastern / Safest), highest -> lowest risk.
const DIRECT = plan({ name: 'Direct run', eta_hours: 3.8, fuel_est_l: 215, risk_exposure: 0.42 });
const EASTERN = plan({ name: 'Eastern balance', eta_hours: 4.4, fuel_est_l: 248, risk_exposure: 0.21 });
const SAFEST = plan({ name: 'Safest, slower', eta_hours: 5.1, fuel_est_l: 286, risk_exposure: 0.12 });
const ROUTES = [DIRECT, EASTERN, SAFEST];

describe('recommendedIndex', () => {
  it('recommends the lowest-risk route when the slider is toward safe (the reported bug)', () => {
    // risk_pref 0.8 => must NOT pick the highest-risk "Direct run".
    const idx = recommendedIndex(ROUTES, 0.8);
    expect(ROUTES[idx].risk_exposure).toBe(0.12);
    expect(ROUTES[idx].name).toBe('Safest, slower');
    expect(idx).not.toBe(0);
  });

  it('recommends the fastest route when the slider is toward fast', () => {
    const idx = recommendedIndex(ROUTES, 0.0);
    expect(ROUTES[idx].eta_hours).toBe(3.8);
    expect(ROUTES[idx].name).toBe('Direct run');
  });

  it('is monotonic: raising risk_pref never moves toward a higher-risk plan', () => {
    let prevRisk = Infinity;
    for (const rp of [0, 0.25, 0.5, 0.75, 1]) {
      const risk = ROUTES[recommendedIndex(ROUTES, rp)].risk_exposure;
      expect(risk).toBeLessThanOrEqual(prevRisk + 1e-9);
      prevRisk = risk;
    }
  });

  it('handles a single plan and an empty list', () => {
    expect(recommendedIndex([DIRECT], 0.5)).toBe(0);
    expect(recommendedIndex([], 0.5)).toBe(-1);
  });

  it('picks the extreme-safe plan at risk_pref = 1', () => {
    const idx = recommendedIndex(ROUTES, 1);
    expect(ROUTES[idx].risk_exposure).toBe(0.12);
  });
});

describe('classifyPlans', () => {
  it('labels fastest, safest and balanced distinctly', () => {
    const labels = classifyPlans(ROUTES);
    expect(labels[0]).toBe('fastest'); // lowest ETA
    expect(labels[2]).toBe('safest'); // lowest risk
    expect(labels[1]).toBe('balanced');
  });

  it('labels a single plan balanced', () => {
    expect(classifyPlans([DIRECT])).toEqual(['balanced']);
  });
});
