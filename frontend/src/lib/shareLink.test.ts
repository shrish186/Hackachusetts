import { describe, it, expect } from 'vitest';
import {
  encodePlannerState,
  parsePlannerStateFromHash,
  type PlannerState,
} from './shareLink';

const BASE: PlannerState = {
  port: 'gloucester',
  vessel: 'small_boat',
  cruiseKn: 9,
  maxHours: 12,
  departure: '2026-03-15T09:00',
  ground: 'stellwagen_bank',
  riskPref: 0.8,
  replay: true,
  language: 'pt',
};

describe('shareLink round-trip', () => {
  it('encodes and parses back the same valid state', () => {
    const hash = `#plan=${encodeURIComponent(encodePlannerState(BASE))}`;
    const out = parsePlannerStateFromHash(hash);
    expect(out).toMatchObject(BASE);
  });

  it('returns {} when no plan hash is present', () => {
    expect(parsePlannerStateFromHash('#other=1')).toEqual({});
    expect(parsePlannerStateFromHash('')).toEqual({});
  });
});

describe('shareLink validation / clamping (never trust the hash)', () => {
  it('clamps out-of-range numbers', () => {
    const hash = '#plan=' + encodeURIComponent('kn=999&hrs=999&risk=5');
    const out = parsePlannerStateFromHash(hash);
    expect(out.cruiseKn).toBe(18); // clamped to max
    expect(out.maxHours).toBe(48); // clamped to max
    expect(out.riskPref).toBe(1); // clamped to [0,1]
  });

  it('ignores unknown vessel and language', () => {
    const hash = '#plan=' + encodeURIComponent('vessel=submarine&lang=fr');
    const out = parsePlannerStateFromHash(hash);
    expect(out.vessel).toBeUndefined();
    expect(out.language).toBeUndefined();
  });

  it('ignores malformed departure and unsafe ids', () => {
    const hash =
      '#plan=' + encodeURIComponent('dep=not-a-date&port=<script>&ground=a b');
    const out = parsePlannerStateFromHash(hash);
    expect(out.departure).toBeUndefined();
    expect(out.port).toBeUndefined();
    expect(out.ground).toBeUndefined();
  });

  it('accepts a lon,lat ground id (nearest open water)', () => {
    const hash = '#plan=' + encodeURIComponent('ground=-70.325,42.925');
    const out = parsePlannerStateFromHash(hash);
    expect(out.ground).toBe('-70.325,42.925');
  });
});
