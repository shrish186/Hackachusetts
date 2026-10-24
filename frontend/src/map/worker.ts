import { setWorkerUrl } from 'maplibre-gl';
// Import the worker as an emitted asset URL so Vite bundles it into
// dist/assets/ with a hashed name. Without this, MapLibre derives the worker
// URL from import.meta.url (e.g. /assets/maplibre-gl-worker.mjs?v=6.15.0),
// which is NOT emitted and the SPA rewrite serves index.html for it — the
// browser then rejects it ("non-JavaScript MIME type text/html / Worker failed
// to load") and the base map never initialises.
//
// maplibre-gl 6.x ships a single self-contained worker: maplibre-gl-worker.mjs.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

let done = false;

/** Point MapLibre at the bundled worker. Call once before creating a Map. */
export function configureMapLibreWorker(): void {
  if (done) return;
  setWorkerUrl(workerUrl);
  done = true;
}
