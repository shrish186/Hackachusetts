import { useEffect, useRef, useState } from 'react';
import { useAppState } from '@/state/AppState';
import { SLICE_COUNT, SLICE_HOURS, formatLocal, sliceToIso } from '@/lib/time';

/**
 * Bottom time slider. Steps the forecast in 3-hour slices (design.md §6) and
 * updates every time-dependent layer via app state. Includes a play button.
 */
export function TimeSlider() {
  const { sliceIndex, setSliceIndex, replay } = useAppState();
  const [playing, setPlaying] = useState(false);
  const timer = useRef<number | null>(null);
  // Mirror the latest slice index so the interval reads a fresh value rather
  // than a stale closure (the "plays a day then stops" bug). The player owns an
  // absolute counter and advances by setting absolute indices.
  const idxRef = useRef(sliceIndex);
  idxRef.current = sliceIndex;

  useEffect(() => {
    if (!playing) {
      if (timer.current) window.clearInterval(timer.current);
      timer.current = null;
      return;
    }
    // If starting from the last slice, restart at the left end.
    if (idxRef.current >= SLICE_COUNT - 1) {
      idxRef.current = 0;
      setSliceIndex(0);
    }
    timer.current = window.setInterval(() => {
      const next = idxRef.current + 1;
      if (next >= SLICE_COUNT - 1) {
        // Land exactly on the last slice, then stop and reset the button.
        idxRef.current = SLICE_COUNT - 1;
        setSliceIndex(SLICE_COUNT - 1);
        setPlaying(false);
        return;
      }
      idxRef.current = next;
      setSliceIndex(next);
    }, 900);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
      timer.current = null;
    };
    // setSliceIndex is stable enough for our use; we intentionally re-run only
    // when `playing` flips.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  const iso = sliceToIso(sliceIndex, replay);

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex justify-center p-3 sm:p-4">
      <div className="pointer-events-auto w-full max-w-3xl rounded-2xl border border-depth bg-deep/85 p-3 backdrop-blur sm:p-4">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? 'Pause' : 'Play'}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-tide text-foam transition-colors hover:bg-surf"
            >
              {playing ? (
                <span className="text-sm">❚❚</span>
              ) : (
                <span className="ml-0.5 text-sm">▶</span>
              )}
            </button>
            <div className="text-sm font-semibold text-foam">{formatLocal(iso)}</div>
          </div>
          <div className="text-xs text-mist">
            {SLICE_HOURS}-hour slices · {SLICE_COUNT * SLICE_HOURS}h window
          </div>
        </div>
        <input
          type="range"
          min={0}
          max={SLICE_COUNT - 1}
          step={1}
          value={sliceIndex}
          onChange={(e) => setSliceIndex(Number(e.target.value))}
          aria-label="Forecast time"
          className="h-10 w-full cursor-pointer accent-surf"
        />
      </div>
    </div>
  );
}
