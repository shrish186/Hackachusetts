/**
 * Shown when the map cannot render (WebGL/worker failure). The planner stays
 * usable on top of this (task 3). Never a blank page.
 */
export function MapUnavailable({ detail }: { detail?: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-abyss">
      <div className="max-w-sm px-6 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-depth bg-deep text-xl">
          🌊
        </div>
        <h2 className="text-base font-bold text-foam">Map unavailable on this device</h2>
        <p className="mt-1 text-sm leading-snug text-mist">
          The interactive map needs WebGL, which your browser or device blocked.
          The trip planner still works — use the panel to plan a trip.
        </p>
        {detail && (
          <p className="mt-2 break-words text-[10px] text-mist/60">{detail}</p>
        )}
      </div>
    </div>
  );
}
