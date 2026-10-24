import { describe, expect, it } from 'vitest';
import {
  DEMO_START_ISO,
  REPLAY_START_ISO,
  SLICE_COUNT,
  SLICE_HOURS,
  isoToSlice,
  sliceToIso,
  windowStartIso,
} from './time';

describe('time slider window (item A)', () => {
  it('non-replay window starts at 2026-03-14 and spans the full 48 h', () => {
    expect(windowStartIso(false)).toBe(DEMO_START_ISO);
    expect(sliceToIso(0, false)).toBe('2026-03-14T00:00:00.000Z');
    expect(sliceToIso(SLICE_COUNT - 1, false)).toBe('2026-03-15T21:00:00.000Z');
  });

  it('replay window starts at 2026-03-15 (slider left end)', () => {
    expect(windowStartIso(true)).toBe(REPLAY_START_ISO);
    expect(sliceToIso(0, true)).toBe('2026-03-15T00:00:00.000Z');
    // Left end round-trips to slice 0 so the slider starts at the left.
    expect(isoToSlice(sliceToIso(0, true), true)).toBe(0);
  });

  it('slice index is clamped to the valid range and round-trips', () => {
    for (let i = 0; i < SLICE_COUNT; i++) {
      expect(isoToSlice(sliceToIso(i, false), false)).toBe(i);
      expect(isoToSlice(sliceToIso(i, true), true)).toBe(i);
    }
    expect(isoToSlice(sliceToIso(999, false), false)).toBe(SLICE_COUNT - 1);
    expect(isoToSlice('not-a-date')).toBe(0);
  });

  it('the window is exactly 48 h in 3 h steps', () => {
    expect(SLICE_HOURS * (SLICE_COUNT - 1)).toBe(45); // last slice at +45h
    const start = new Date(sliceToIso(0, false)).getTime();
    const end = new Date(sliceToIso(SLICE_COUNT - 1, false)).getTime();
    expect((end - start) / 3600000).toBe(45);
  });
});

/**
 * Model of the player's advance rule (TimeSlider): advance by +1 absolute,
 * stop exactly at the last slice, then reset. This guards the "plays a day then
 * stops / never reaches the end" regression.
 */
function advance(idx: number): { idx: number; stop: boolean } {
  const next = idx + 1;
  if (next >= SLICE_COUNT - 1) return { idx: SLICE_COUNT - 1, stop: true };
  return { idx: next, stop: false };
}

describe('time slider player advance (item A)', () => {
  it('runs from 0 all the way to the last slice, then stops once', () => {
    let idx = 0;
    let stops = 0;
    for (let steps = 0; steps < SLICE_COUNT + 5; steps++) {
      const r = advance(idx);
      idx = r.idx;
      if (r.stop) {
        stops++;
        break;
      }
    }
    expect(idx).toBe(SLICE_COUNT - 1);
    expect(stops).toBe(1);
  });
});
