# Fathom — 3-minute demo video script

Total **3:00**. Screen recording + voiceover only, against the live app at
**https://fathom-six-vert.vercel.app**. **No copyrighted music, no third-party
logos** (brand marks, company logos, stock tracks all out). Use **preset
scenarios only** in Manager mode — they are precomputed and return instantly, so
there is no spinner on camera.

**Pre-flight (before recording):** open the live app, dismiss the intro card,
turn **"Replay whale season (15 Mar 2026)" ON**, select **Gloucester**, vessel
**small boat**. This makes the seasonal closures and slow zones active.

| Time | Segment | On screen | Voiceover |
|------|---------|-----------|-----------|
| 0:00–0:15 | **Hook** | Map of Massachusetts Bay, zones + risk heatmap visible | "Right whales versus fishing boats — a safe route in seconds. In these waters a captain must thread between a whale slow zone that changed yesterday, a closure, a wind-construction area, and worsening weather. Fathom turns that into one trusted picture for fishermen and for the regulators who protect the whales." |
| 0:15–1:15 | **Captain flow** | "Replay whale season" ON; Gloucester, small boat. Click **Try the demo trip**. Agent feed streams tool calls. Three routes draw; point at the trade-off line. Tap **"Why"** on the best plan → show one citation. Switch language to **PT**. | "Replay whale season so the closures are live. Gloucester, small boat — Try the demo trip. The agent isn't guessing; it streams real tool calls: zones, whale risk, route planning. Three ranked routes come back with a risk-versus-time trade-off line. Tap 'Why' — every number is cited, down to a plain label when the source is bundled demo data. Switch to Portuguese for New Bedford's fleet: same numbers, new language." |
| 1:15–2:15 | **Manager flow** | Manager mode. Run the three presets: **Extend closure east**, **Dynamic zone around recent sightings**, **Seasonal 10-knot speed limit**. Point at the **Pareto chart** and the highlighted efficient options; read a plain-language summary. | "Now the manager. Run three candidate policies — extend the closure east, a dynamic zone around recent sightings, and a seasonal ten-knot speed limit instead of a closure. Fathom instantly re-routes a 200-boat synthetic fleet and plots the trade-off: whale risk removed versus the cost in steaming time, fuel, and lost access to grounds. On the Pareto chart the efficient options are highlighted — the speed limit removes much of the risk at a fraction of a closure's livelihood cost. And it's honest: even before any new rule, 57 of 200 trips already target grounds inside today's closed zones, reported as lost access, not quietly relocated." |
| 2:15–2:50 | **Kiro usage** | Flip through: spec files, steering list, a hook firing, Kiro calling the `fathom` MCP, a Hypothesis counterexample | "We built Fathom with Kiro, spec-first: 10 EARS requirements, a design doc, and 52 tasks across four lanes. Steering files taught Kiro our safety and honesty rules once. Agent hooks ran our property tests and the citation guard on every change. Our own MCP server exposes the engine, so Kiro queried the same tested tools while writing code. Property-based testing even caught a real modelling bug — a closure that looked like it saved fleet time was actually destroying access." |
| 2:50–3:00 | **Safety & data honesty** | Advisory disclaimer + "Demo data" badge visible | "Fathom is advisory only — it never claims legal compliance. The weather is real NOAA buoy and NWS forecast data, the sightings are real OBIS records; the zone shapes are hand-drawn approximations and labeled as such. Protecting whales and protecting livelihoods isn't zero-sum. It's a routing and information problem. That's Fathom." |

## On-screen click checklist (with timings)

| At | Click / action | Expected on screen |
|----|----------------|--------------------|
| 0:00 | Already on the map, "Replay whale season" ON | Active zones + risk heatmap visible |
| 0:18 | Confirm Gloucester + small boat selected | Captain panel shows Gloucester |
| 0:25 | Click **Try the demo trip** | Agent feed starts streaming tool calls |
| 0:40 | Wait for **3 routes** to draw | Three ranked route cards + trade-off line |
| 0:55 | Tap **"Why"** on the top plan | Citations list; point at one source label |
| 1:05 | Switch language to **PT** | Same numbers, Portuguese labels |
| 1:15 | Open **Manager mode** | Draw/scenario panel + empty chart |
| 1:25 | Run preset **Extend closure east** | Result + point appears on Pareto chart |
| 1:40 | Run preset **Dynamic zone around recent sightings** | Second point on chart |
| 1:55 | Run preset **Seasonal 10-knot speed limit** | Third point; efficient options highlighted |
| 2:05 | Hover the efficient (frontier) point; read summary | Plain-language trade-off sentence |
| 2:50 | Scroll to show advisory disclaimer + Demo badge | Disclaimer visible for the close |

## Recording notes

- Pause ~1 s on each citation and on the Pareto chart so they read on video.
- Keep the "Demo data" badge and advisory disclaimer visible at least once.
- Show only synthetic/public data; never display a real vessel identity.
- Presets are instant. If you must show a custom-drawn polygon, keep it small —
  the live path is bounded to 8 s and will otherwise ask you to simplify it.
- Evidence stills for the writeup: `13-live-map.png`, `14-manager-result.png`,
  `15-mobile-390.png`.
