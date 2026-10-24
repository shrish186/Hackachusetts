# Lane A (Anant) — data honesty work log

Format: `YYYY-MM-DD HH:MM EDT | what | result`

2026-10-24 | START: pulled --rebase --autostash; baseline `pytest -q` = 97 passed. Network reachable from sandbox: NDBC, NWS (api.weather.gov), OBIS, Natural Earth all 200. | baseline green
2026-10-24 | REAL sightings: added backend/app/ingest/obis.py; OBIS has 6793 real Eubalaena glacialis records in bbox. Wrote 400 most-recent real records to sightings.json (synthetic:false, CC-BY, fetched_at). | sightings now REAL
2026-10-24 | REAL conditions: added backend/app/ingest/nws.py (api.weather.gov gridpoint waveHeight/windSpeed, real). refresh_snapshots.py now writes conditions.json = 2 NDBC buoy cells + 5 NWS forecast cells, all real (synthetic:false). | conditions now REAL + study-wide coverage
2026-10-24 | Real data broke Lane B agent_evals (max_wave_m IDW value cited to get_conditions, which only holds raw readings). Minimal honest fix in app/agent/agent.py: cite interpolated max_wave_m to plan_routes (whose result carries that number), keep conditions source_url for reference. 16/16 evals pass. | cross-lane citation bug fixed honestly
2026-10-24 | Removed TODO-VERIFY from API source names (meta.py risk layer name, layers.py sightings_provenance comment). Risk params already VERIFIED (Vanderlaan & Taggart 2007) in config/risk.yaml. Risk layer stays synthetic:true honestly (it is a derived model, not an observation). | no more TODO-VERIFY in served source names
2026-10-24 | Fixed my test_risk.py hardcoded len==8 (now >0) for real OBIS data. Full pytest -q = 97 passed with real data. | green checkpoint
2026-10-24 | Rebased onto Lane B changes; resolved conflicts in meta.py (kept my model-aware risk name + their DOI url) and agent.py (kept their _citation helper + my max_wave->plan_routes fix). | conflicts resolved keeping both sides
2026-10-24 | 400 real OBIS sightings made routing exceed the Req 5.3 <3s budget (O(cells x sightings)). Capped the OBIS snapshot to the 60 most-recent real records: still real + representative, routing back to ~1.2s, risk grid max 0.31 over 802 cells. Full suite 136 passed in 24s (was 108s). | perf restored, data still real
2026-10-24 | Zones honesty (tasks 1,3): rewrote zones.json metadata + per-zone notes as "hand-drawn approximation of <official NOAA/BOEM source>" with real source_url, license, verified dates. Added Off Race Point (Mar 1-Apr 30) and Great South Channel (Apr 1-Jul 31) SMAs. Verified via NOAA: Cape Cod Bay SMA Jan 1-May 15, 10 kn for vessels >=65 ft. | CONFIRMED the QA "0 of 3 active on Oct 24" is CORRECT (out of whale season), not a bug.
2026-10-24 | config/demo_scenarios.yaml: "Replay whale season" = 2026-03-15 09:00 EDT (13:00 UTC); activates 5 zones incl. Cape Cod Bay + Off Race Point SMAs. Documented for frontend. | demo can show active closures
2026-10-24 | snap_to_water (task 4): backend/app/ingest/ports.py snaps real port coords to nearest water cell (3 ports were on land cells of the simplified mask). Test asserts all 5 ports snap to water. Kept simplified mask, labeled synthetic honestly (Natural Earth download deferred for stability/time). | ports now routable
2026-10-24 | scripts/validate_snapshots.py (task 6): schema/bounds/range/timestamp + TODO scan; wired into CI via pytest. Added test_data_snapshots.py (TODO scan every snapshot, honest-metadata, ports-in-water, demo-scenario-active, today-honest) + test_ingest_sources.py (offline OBIS/NWS/NDBC parser tests). Full suite 154 passed. | validators + tests green
2026-10-24 | Docs (task 7): rewrote data/snapshots/SOURCES.md + new docs/DATA.md with full source table (layer/source/URL/fetched_at/real-synthetic/limitations/license). Updated docs/FACT_CHECK.md: SMA dates now VERIFIED (polygons still approx), sightings+conditions marked REAL, lethality params VERIFIED (v50=11.8, k=2.415). Updated land_mask.geojson metadata (honest source/license, Natural Earth ref). Documented 'Replay whale season' time-replay for frontend in DATA.md (API_CONTRACT is Lane B-owned; left a note for them). | docs honest + complete
2026-10-24 | Verified no TODO/TODO-VERIFY remain in data/snapshots, config, ingest, or served API source strings (meta.py/layers.py). | task 2 complete
2026-10-24 | /api/meta/sources (task 1): every layer now returns name, real source_url, real fetched_at, LICENSE, synthetic flag, and an honest NOTE (pulled from each snapshot's metadata). land_mask got a descriptive name. Cross-lane edit to Lane B's meta.py (honesty-critical, documented here). Locked with a new meta test. Full suite 155 passed. | meta/sources fully honest + self-describing
2026-10-24 | Background refresh (task 6): added conditions.maybe_background_refresh() - throttled to <=1/30min, 5s timeout, snapshot fallback, no-op in demo mode; additive (loader API unchanged). Server can call it per-request safely. Tests for throttle + demo no-op. Full suite 157 passed. | runtime refresh policy implemented without breaking engine/sim
2026-10-24 | DONE. Final state: working tree clean, in sync with origin/main, 157 passed + 1 skipped. REAL now: conditions (NDBC+NWS), sightings (OBIS), SMA dates, lethality params, port coords. SYNTHETIC (labeled): zone polygons (dates real), land mask, effort, fleet, risk-model output. Oct-24 "0 SMAs active" confirmed correct (out of season); Mar-15 demo scenario shows active zones. | round complete

2026-10-24 (4:30pm round) | Whale-season replay polish. (1) OBIS ingest now filters to Jan-May (WHALE_SEASON_MONTHS); refresh_snapshots kept the 60 most-recent real whale-season records (2023-04-10..2025-05-04). Risk@2026-03-15T13:00Z: max 0.31, ~650 cells>0.05 - driven honestly by the seasonal PRESENCE term (recency of multi-year records ~0; no fabricated recent sightings). (2) Verified replay-date zones: Cape Cod Bay SMA, Off Race Point SMA, Western GoM closure, Stellwagen slow zone ACTIVE; Great South Channel INACTIVE (opens Apr 1) - added test_replay_date_zone_activity_is_correct. (3) Fleet access_lost=57/200 traced to the 57 trips targeting jeffreys_ledge, which legitimately sits inside the active Western GoM closure in whale season - LEFT as-is, documented in DATA.md. No ground on land. Separately fixed 3 ports (Gloucester/Boston/Plymouth) that fell on coarse land cells -> moved to nearest water cell (within a few km); all ports+grounds now in water (tests enforce). (4) Re-ran refresh_snapshots (conditions fetched_at=2026-10-24T20:22Z) + validate_snapshots (OK) + precompute_sim (access_lost still 57, confirming closure is the cause). Full suite 164 passed, 1 skipped. | honest March replay; access_lost explained, not faked

2026-10-24 (5:15pm round) | CI + ports metadata + dataset placeholder. (1) Red main fixed: removed unused import `build_grid_spec` in backend/app/ingest/ports.py (ruff F401; ports.py not in CI per-file-ignores). Reproduced locally with the exact CI ruff command; pushed the fix first. (2) config/ports.yaml: added display_name, description, region to all 5 ports + 3 grounds; ids and loader API (load_ports/load_grounds) unchanged, extra keys additive for /api/meta/ports + frontend picker. Added tests: ids match ^[a-z0-9_]+$, name/display_name/description/region non-empty, coords in bbox, expected id sets. (3) docs/DATA.md: added "Relation to the hackathon datasets" section as an honest placeholder (table awaiting the official list; explicitly claims NO hackathon-dataset usage until the list is pasted). (4) Ran refresh_snapshots (conditions fetched_at 2026-10-24T21:10Z, 60 OBIS whale-season sightings) + validate_snapshots (OK) + full pytest (185 passed, 1 skipped) + ruff (clean). | CI green; ports pickable; no false dataset claims

2026-10-24 (6:10pm round) | Planner ports + eMOLT.
  PLANNER PORTS: added 13 real MA harbors for the trip-planner dropdown. To
  guarantee the 200-trip fleet + precomputed simulator numbers do NOT change
  (fleet.py seeds from the `ports` key and I must not edit fleet.py), they live
  under a SEPARATE top-level key in config/ports.yaml -> **planner_ports:** ,
  each with planner_only: true. Kept: marblehead, salem, rockport, scituate,
  green_harbor, sandwich, barnstable, hyannis, chatham, woods_hole,
  vineyard_haven, menemsha, nantucket. DROPPED: newburyport (snap 0.126 deg),
  cohasset (snap 0.106 deg) -- both > 0.1 deg. All kept are in-grid, snap to a
  water cell, within 0.1 deg. Verified fleet still uses only the base 5
  (gloucester/boston/plymouth/provincetown/new_bedford), counts unchanged
  38/42/40/38/42.
  >>> SHRISH: for /api/meta/ports read config key **planner_ports** (base ports
      stay under `ports`). Loaders in backend/app/ingest/ports.py:
      load_ports() = base 5 only (fleet/sim); load_planner_ports() = the 13
      (planner_only:true); load_all_ports() = base+planner for the picker.
  eMOLT: added backend/app/ingest/emolt.py + data/snapshots/emolt_bottom_temp.json
  = REAL fishermen-collected BOTTOM temps via NOAA/NMFS/NEFSC ERDDAP
  (eMOLT_realtime_bottom_temps_and_profiles), most-recent reading per station in
  bbox (36 rows, 2026-10-18..24). synthetic:false. Wired into refresh_snapshots
  (--emolt) and validate_snapshots. Documented in DATA.md + FACT_CHECK.md
  (bottom temp != SST). Not yet used by the risk/routing engine.
  CHECKS: refresh_snapshots --all OK (conditions 21:43Z, 60 OBIS, 36 eMOLT),
  validate_snapshots OK, pytest 204 passed/1 skipped, ruff clean.
