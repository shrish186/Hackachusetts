import { useEffect, useState } from 'react';

/**
 * Minimal client-side router (item 5). No dependency; uses the History API.
 * `navigate` pushes a path and notifies listeners; `useRoute` returns the
 * current pathname and re-renders on back/forward and programmatic navigation.
 */
const listeners = new Set<() => void>();

export function navigate(path: string): void {
  if (window.location.pathname === path) return;
  window.history.pushState(null, '', path);
  listeners.forEach((fn) => fn());
}

export function useRoute(): string {
  const [path, setPath] = useState<string>(() => window.location.pathname);
  useEffect(() => {
    const onChange = () => setPath(window.location.pathname);
    listeners.add(onChange);
    window.addEventListener('popstate', onChange);
    return () => {
      listeners.delete(onChange);
      window.removeEventListener('popstate', onChange);
    };
  }, []);
  return path;
}
