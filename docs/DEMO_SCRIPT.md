# Fathom — 3-minute demo video script

Total **≤ 3:00**. Screen recording + voiceover only, against the live app at
**https://fathom-six-vert.vercel.app**. **No copyrighted music, no third-party
logos** (brand marks, company logos, stock tracks all out). Use **preset
scenarios only** in Manager mode — they are precomputed and return instantly, so
there is no spinner on camera.

**Pre-flight (before recording):** open the live app, dismiss the intro card,
turn **"Replay whale season (15 Mar 2026)" ON**, vessel **small boat**. This
makes the seasonal closures and slow zones active.

| Time | Segment | On screen | Voiceover |
|------|---------|-----------|-----------|
| 0:00–0:15 | **Hook** | Map of Massachusetts Bay, zones + risk heatmap visible | "Right whales versus fishing boats — a safe route in seconds. A captain has to thread between a whale slow zone that changed yesterday, a closure, a wind-construction area, and worsening weather. Fathom turns that into one trusted picture for fishermen and for the regulators who protect the whales." |
| 0:15–1:20 | **Captain flow** | "Replay whale season" ON. In the **port picker type `gl`** → pick **Gloucester**. Open the **ground picker**: Jeffreys Ledge shows a red **"closed" chip**; pick **Stellwagen Bank**. Click **Try the demo trip**. Agent feed streams tool calls. Three routes draw. Tap **"Why"** on the recommended plan → show a citation and a **"Why not that route?"** line on an alternative. Switch language to **PT**. | "Type 'gl', pick Gloucester. Open the grounds — Jeffreys Ledge is flagged closed today because it sits in an active closure, so we pick Stellwagen Bank. Try the demo trip. The agent isn't guessing; it streams real tool calls — zones, whale risk, route planning — and returns three ranked routes. Tap 'Why': every number is cited. And 'Why not that route?' explains each alternative — this one adds time and whale risk over the pick. Switch to Portuguese: same numbers, new language." |
| 1:20–2:15 | **Manager flow** | Manager mode. Run the four presets: **Extend closure east**, **Dynamic zone around recent sightings**, **Seasonal 10-knot speed limit**, **Seasonal 8-knot speed limit**. Point at the **comparison chart** (Pareto) and read a summary. | "Now the manager. Run four candidate policies over a 200-boat synthetic fleet. The two closures — extend east, and a dynamic zone on the sighting cluster — each cut whale risk about 33 to 35 percent, but they're expensive: they shut a productive ground, so fishing access drops almost 40 percent. The eight-knot speed limit is the interesting one: it cuts risk about 8 percent and actually *keeps* the fleet on the water, just slower. And Fathom is honest about what doesn't work — the ten-knot limit changes almost nothing, because most of this fleet already cruises at or below ten knots. Even the baseline is honest: 57 of 200 trips already target a ground inside today's Gulf of Maine closure, reported as lost access, not quietly relocated." |
| 2:15–2:35 | **Share link + /about** | Click **Share** → copy the link, paste in a new tab: the same trip + replay state reload. Open **/about**. | "Share the exact view — the link reopens the same trip and whale-season replay. The About page lists every data source and says plainly what's real and what's hand-drawn." |
| 2:35–2:52 | **Kiro usage** | Flip through: spec files, steering list, a hook firing, Kiro calling the `fathom` MCP, a Hypothesis counterexample | "We built Fathom with Kiro, spec-first: 10 requirements, a design doc, and 52 tasks across four lanes. Steering files taught Kiro our safety and honesty rules once. Agent hooks ran our property tests and the citation guard on every change. Our own MCP server — now nine tools — exposes the engine, so Kiro queried the same tested tools while writing code. Property-based testing even caught a real bug: a closure that looked like it saved fleet time was actually destroying access." |
| 2:52–3:00 | **Safety & data honesty** | Advisory disclaimer + "Demo data" badge visible | "Fathom is advisory only — it never claims legal compliance. Weather is real NOAA buoy and NWS forecast data; sightings are real OBIS records; zone shapes are hand-drawn and labeled. Whales and fishermen don't have to lose for the other to win. That's Fathom." |

## On-screen click checklist (with timings)

| At | Click / action | Expected on screen |
|----|----------------|--------------------|
| 0:00 | Map loaded, **"Replay whale season" ON** | Active zones + risk heatmap visible |
| 0:18 | In **port picker type `gl`** → select **Gloucester** | Port set to Gloucester |
| 0:26 | Open **ground picker** | **Jeffreys Ledge** shows a red "closed" chip |
| 0:30 | Select **Stellwagen Bank**; vessel **small boat** | Ground + vessel set |
| 0:40 | Click **Try the demo trip** | Agent feed streams tool calls |
| 0:52 | Wait for **3 routes** to draw | Three ranked route cards |
| 1:00 | Tap **"Why"** on the recommended plan | Citations list; point at a source label |
| 1:08 | Point at a **"Why not that route?"** line on an alternative | Cited comparison sentence |
| 1:14 | Switch language to **PT** | Same numbers, Portuguese labels |
| 1:20 | Open **Manager mode** | Scenario panel + empty comparison chart |
| 1:28 | Run preset **Extend closure east** | Point at ~-33% risk / high cost |
| 1:38 | Run preset **Dynamic zone around recent sightings** | Point at ~-35% risk / high cost |
| 1:48 | Run preset **Seasonal 10-knot speed limit** | Near-origin point (~0% risk) — the honest no-op |
| 1:58 | Run preset **Seasonal 8-knot speed limit** | Point at ~-8% risk, slight cost (keeps access) |
| 2:08 | Hover a point; read the plain-language summary | Trade-off sentence (incl. the 10 kn "changes little" note) |
| 2:15 | Click **Share**, paste link in a new tab | Same trip + replay state reloads |
| 2:28 | Open **/about** | Data-sources / honesty page |
| 2:52 | Show advisory disclaimer + Demo badge | Disclaimer visible for the close |

## Recording notes

- Pause ~1 s on each citation, the "Why not" line, and the comparison chart so
  they read on video.
- Keep the "Demo data" badge and advisory disclaimer visible at least once.
- Show only synthetic/public data; never display a real vessel identity.
- Presets are instant. If you must show a custom-drawn polygon, keep it small —
  the live path is bounded to 8 s and will otherwise ask you to simplify it.
- Evidence stills: `13-live-map.png`, `14-manager-result.png`, `15-mobile-390.png`,
  `16-whale-season-replay.png`, `17-access-lost.png`.
