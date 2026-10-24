# Final audit (solo, last 30 min) — Fathom

Audited the backend (uvicorn) and the built frontend against the promises in
`docs/JUDGE_GUIDE.md` and `docs/API_CONTRACT.md`. Done with Kiro. Specs/steering
used: `.kiro/specs/fathom/{requirements,design,tasks}.md`,
`.kiro/steering/{product,tech,structure,data-and-safety,testing-pbt}.md`.

## Results

| Item | Status | How verified |
|---|---|---|
| **A. Time slider playback** | **Fixed** | Root cause: the player's functional `setSliceIndex(prev => prev+1)` read a stale `sliceIndex` (derived from `departure` in context), so play jumped once and stalled ("~a day then stops"); and replay pinned the window to the whale instant so the slider never scrubbed. Fix: ref-based absolute counter in `TimeSlider` that runs 0→last, **stops at the end and resets the play button**; `layerTimeIso` now follows the slider in both modes (dragging updates zones/risk/conditions); replay starts the window at **2026-03-15** with the slider at the **left end** (`windowStartIso(replay)`). Tests: `frontend/src/lib/time.test.ts` (window + player advance). `npm test` green. |
| **B. Source links** | **Fixed** | `curl -sIL` on every URL. Dead (404): two NOAA Fisheries pages, BOEM MA page, the Vanderlaan DOI. Replaced with verified 200s: vessel-strike → `/national/.../reducing-vessel-strikes-north-atlantic-right-whales`; closures → `/region/new-england-mid-atlantic`; BOEM → `/massachusetts-activities`; paper → the Dalhousie PDF (DOI 404s). Fixed in `data/snapshots/zones.json`, `backend/app/api/meta.py`, frontend mocks, and docs. New test `backend/tests/test_source_urls.py` fails on any empty/malformed source_url in `/api/meta/sources` and the snapshots. |
| **C. Manager graph** | **Fixed / already-solid** | Chart already had axes, labels, legend, and a plain-language summary + error-retry (429/504/timeout) states in `ManagerPanel`. Added: NaN/null guards on every delta so a bad value can't render NaN or overflow, and a native SVG `<title>` **tooltip** per point with an enlarged hover target. Verified `npm run build` + all four scenarios return via precompute. |
| **D. "Demo data" badge** | **Fixed** | Replaced the amber "Demo data" badge with an honest neutral label **"Live NOAA data + modelled zones"** that opens a click/hover popover listing **Live** (NOAA buoys 44013/44029, NWS forecast, eMOLT), **Real records** (60 OBIS sightings, NOAA SMA dates + 10 kn rule), and **Modelled** (zone polygons, risk model, 200-trip synthetic fleet). Never hides the modelled parts. EN/PT/ES. Offline still shows a clear red "Offline — bundled data". |
| **E. Plan cards (dominated plans)** | **Fixed (drop); button is a known gap** | Added `_drop_dominated()` in `backend/app/engine/routing.py`: any plan slower AND riskier than a sibling is dropped before return, always keeping ≥1 (the fastest). The backend already returns a friendly "No legal route within N h" message naming the binding constraint; the **one-click "Set max hours to 16" button was NOT added** in this time box (the Captain panel has a max-hours field the user can raise manually). Marked as a known limitation rather than claimed. Tests: `backend/tests/test_routing.py::test_e_*` (unit + "no returned plan is dominated" + no Balanced-with-Alternative mislabel). |
| **F. Other** | **Partially addressed** | tsc/`npm run lint` clean (no type errors); build clean. The large `MapView` JS chunk warning is pre-existing and benign. PT/ES strings for the new badge are included. 390 px / 1440 px layouts and keyboard focus were not exhaustively re-walked in the time box — see "still weak" below. |

## Verification run

- Backend: `pytest -q` → **241 passed, 1 skipped**; `ruff check --select E4,E7,E9,F` → clean.
- Frontend: `npm run lint` (tsc) clean; `npm test` → **22 passed**; `npm run build` → success.

## Still weak / known limitations

- Did not exhaustively re-test every control at 390 px and 1440 px or full
  keyboard-only navigation within the time box (no regressions seen in build/lint).
- Source URLs were reachability-checked by hand with `curl`; the automated test
  is **structural** (scheme + host), not a live network check, to keep CI offline
  and fast.
- The Vanderlaan & Taggart 2007 DOI is dead upstream; we cite the open Dalhousie
  PDF of the same paper instead.
- Item E's one-click "Set max hours to 16" button was not implemented in the
  time box; the no-route message is shown and the user can raise max hours
  manually. Deferred rather than shipped half-done.
