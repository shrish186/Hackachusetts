# Lane A (Anant) — data honesty work log

Format: `YYYY-MM-DD HH:MM EDT | what | result`

2026-10-24 | START: pulled --rebase --autostash; baseline `pytest -q` = 97 passed. Network reachable from sandbox: NDBC, NWS (api.weather.gov), OBIS, Natural Earth all 200. | baseline green
2026-10-24 | REAL sightings: added backend/app/ingest/obis.py; OBIS has 6793 real Eubalaena glacialis records in bbox. Wrote 400 most-recent real records to sightings.json (synthetic:false, CC-BY, fetched_at). | sightings now REAL
2026-10-24 | REAL conditions: added backend/app/ingest/nws.py (api.weather.gov gridpoint waveHeight/windSpeed, real). refresh_snapshots.py now writes conditions.json = 2 NDBC buoy cells + 5 NWS forecast cells, all real (synthetic:false). | conditions now REAL + study-wide coverage
2026-10-24 | Real data broke Lane B agent_evals (max_wave_m IDW value cited to get_conditions, which only holds raw readings). Minimal honest fix in app/agent/agent.py: cite interpolated max_wave_m to plan_routes (whose result carries that number), keep conditions source_url for reference. 16/16 evals pass. | cross-lane citation bug fixed honestly
2026-10-24 | Removed TODO-VERIFY from API source names (meta.py risk layer name, layers.py sightings_provenance comment). Risk params already VERIFIED (Vanderlaan & Taggart 2007) in config/risk.yaml. Risk layer stays synthetic:true honestly (it is a derived model, not an observation). | no more TODO-VERIFY in served source names
2026-10-24 | Fixed my test_risk.py hardcoded len==8 (now >0) for real OBIS data. Full pytest -q = 97 passed with real data. | green checkpoint
