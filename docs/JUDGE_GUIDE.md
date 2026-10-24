# Judge guide — Fathom in 2 minutes

**Live app:** https://fathom-six-vert.vercel.app · **Repo:**
https://github.com/shrish186/Hackachusetts

No login, no API keys. Demo mode runs from bundled public/synthetic data.

## 5 steps (~2 minutes)

1. **Turn on "Replay whale season (15 Mar 2026)"** (top of the map). Seasonal
   Management Areas are only active in whale season, so in October the live date
   shows few active zones — the replay sets the clock to a day when the Cape Cod
   Bay SMA, Off Race Point SMA, the Stellwagen slow zone, and the Western Gulf of
   Maine closure are all active. *(~15 s)*
2. **Toggle layers and click a zone.** Turn weather, zones, and risk on/off.
   Click any zone to see its name, effective dates, restriction, and source. The
   data-timestamp strip and a "Demo data" badge stay visible. *(~20 s)*
3. **Captain mode — run the demo trip.** In the **port picker type `gl`** and
   pick **Gloucester**; open the **ground picker** (Jeffreys Ledge shows a red
   **"closed" chip** at this time) and pick **Stellwagen Bank**; vessel **small
   boat**. Click **Try the demo trip**. Watch the agent stream its tool calls,
   read the three ranked routes, tap **"Why"** (every number is cited) and the
   **"Why not that route?"** line on an alternative. Switch to Portuguese — the
   numbers stay identical. *(~35 s)*
4. **Manager mode — run the 3 presets.** Run *Extend closure east*, *Dynamic
   zone around recent sightings*, and *Seasonal 10-knot speed limit*. They return
   instantly (precomputed). Read the comparison (Pareto) chart: efficient options
   are highlighted. Note the honest baseline — **57 of 200 fleet trips already
   target grounds inside today's closed zones**, reported as lost access rather
   than silently relocated. Use **Share** to copy a link that reopens this exact
   view, and open **/about** for the data-sources page. *(~35 s)*
5. **Check the tests (optional).** `cd backend && pip install -r requirements.txt
   && pytest -q` → **183 passed, 1 skipped**, including Hypothesis property
   tests. *(~15 s)*

## What is real vs. synthetic (from `docs/DATA.md`)

| Layer | Status |
|---|---|
| Conditions (wave, wind, SST) | **Real** — NOAA NDBC buoys + NWS marine forecast |
| Whale sightings | **Real** — OBIS right-whale occurrences (CC-BY 4.0) |
| Whale risk | **Modelled over real inputs** — real OBIS sightings × the Vanderlaan & Taggart (2007) vessel-strike lethality curve; a screening model, flagged synthetic |
| Protection-zone **rules/dates** | **Real** — NOAA 2026 Seasonal Management Area bulletins and the 10 kn speed rule |
| Protection-zone **polygons** | **Hand-drawn** — approximations of the published shapes, labeled synthetic |
| Land mask / coastline | **Synthetic** — simplified approximation |
| Ports & grounds | **Real coordinates**; derived routes/effort are estimates |
| Effort proxy | **Synthetic** — an estimate of activity, not catch or revenue |
| Fleet (200 trips) | **Synthetic** — deterministic, anonymized; no real vessel identity |

Everything not from a real source is flagged `synthetic: true` in the API and
badged in the UI.

## Safety statement

Fathom is **advisory only**. It does not replace official NOAA notices, VHF
warnings, or the captain's judgment, and it never states that a plan is "legally
compliant" — it reports only which known zones a plan avoids. The whale-risk
layer is a transparent screening tool, not a prediction of a real strike.
