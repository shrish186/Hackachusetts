import { useEffect, useState } from 'react';
import { useAppState } from '@/state/AppState';

const DISMISS_KEY = 'fathom.intro.dismissed.v1';

/**
 * First-visit intro (tasks.md task 6): two sentences for the current mode,
 * dismissible, remembered in localStorage so it only shows once.
 */
export function IntroCard() {
  const { mode } = useAppState();
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    try {
      setDismissed(localStorage.getItem(DISMISS_KEY) === '1');
    } catch {
      setDismissed(false);
    }
  }, []);

  if (dismissed) return null;

  function dismiss() {
    try {
      localStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* ignore */
    }
    setDismissed(true);
  }

  const copy =
    mode === 'captain'
      ? {
          title: 'Welcome, Captain',
          body: 'Describe your trip and Fathom suggests 2–3 ranked routes that avoid closures, slow zones, and bad weather. Every number is traceable to a data source — tap "Why" on any plan.',
        }
      : {
          title: 'Welcome, Manager',
          body: 'Draw or pick a candidate protection zone and re-route a sample fleet to see whale risk removed against the cost to fishing access. Highlighted options are on the efficient frontier.',
        };

  return (
    <div className="pointer-events-auto absolute left-1/2 top-1/2 z-40 w-[min(92vw,26rem)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-depth bg-deep/95 p-5 shadow-2xl backdrop-blur">
      <h2 className="text-base font-bold text-foam">{copy.title}</h2>
      <p className="mt-2 text-sm leading-snug text-mist">{copy.body}</p>
      <p className="mt-2 text-[11px] text-mist/80">
        Advisory only — Fathom supports, but never replaces, the captain&apos;s judgment.
      </p>
      <button
        onClick={dismiss}
        className="mt-4 min-h-10 w-full rounded-lg bg-tide font-semibold text-foam transition-colors hover:bg-surf focus-visible:ring-2 focus-visible:ring-surf"
      >
        Got it
      </button>
    </div>
  );
}
