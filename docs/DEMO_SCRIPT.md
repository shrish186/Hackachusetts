# Fathom — 3-minute demo video script

Total **3:00**. Screen recording + voiceover only. **No copyrighted music and no
third-party logos** (brand marks, company logos, stock tracks are all out). Use
**preset scenarios only** in Manager mode — they are precomputed and return
instantly, so there is no spinner on camera. Pre-load: live app open in demo
mode, Captain mode, Gloucester selected, a whale-season date (15 March).

| Time | Segment | On screen | Voiceover |
|------|---------|-----------|-----------|
| 0:00–0:15 | **Hook (15 s)** | Map of Massachusetts Bay with zones and the risk heatmap on | "At 4 a.m. a Gloucester fisherman has to thread between a whale slow zone that changed yesterday, a closure, a wind-construction area, and worsening weather. Today he checks five websites and guesses. On the other side, a manager must decide whether to close an area — and can't see what it costs the fleet. Fathom gives both of them the same trusted picture." |
| 0:15–1:15 | **Captain flow (60 s)** | Toggle layers; click a slow zone → popup with name, dates, source link. Type the trip request. Agent feed streams tool calls. Three plans appear; open "why" on the best. Drag the risk slider; switch to Portuguese. | "Everything on the map has a source and a timestamp. The captain types the trip in plain language: leave Gloucester, twelve hours, small boat, nine knots, fish near Stellwagen, safest option. Watch the agent — it isn't guessing, it's calling tested tools: zones, whale risk, route planning. Three ranked plans come back. Open 'why': the zones it avoids, the risk it removes for a few extra minutes, and a citation on every number — including a plain label when the source is bundled demo data. Slide toward 'safest' and the route shifts. Switch to Portuguese for New Bedford's fleet — same numbers, new language." |
| 1:15–2:15 | **Manager flow (60 s)** | Manager mode. Click preset "Extend closure east" (instant), then "Seasonal 10-knot speed limit." Trade-off chart with the efficient frontier highlighted; read the summary. Point at an "access lost" figure. | "Now the manager. Pick a candidate — extend the closure east. Fathom instantly re-routes a 200-boat synthetic fleet and shows the trade-off: whale risk removed versus the cost in steaming time, fuel, and lost access to grounds. Try a seasonal speed limit instead. On the frontier chart, the speed limit removes most of the risk at a fraction of the closure's livelihood cost — the efficient option is highlighted. When a closure sits on a fishing ground, Fathom reports that ground as access lost, honestly, instead of pretending the fleet just fishes elsewhere." |
| 2:15–2:50 | **Kiro usage (35 s)** | Flip through: spec files, steering list, a hook firing, Kiro calling the `fathom` MCP, a Hypothesis counterexample | "We built Fathom with Kiro, spec-first: ten EARS requirements, a design doc, and fifty-plus tasks across four lanes. Steering rules taught Kiro our safety and honesty standards once. Hooks ran our property tests and the citation guard on every change. Our own MCP server exposes the engine, so Kiro queried the same tested tools while writing code. And property-based testing caught a real modelling bug — a closure that looked like it saved fleet time was actually destroying access." |
| 2:50–3:00 | **Safety & close (10 s)** | Advisory disclaimer and "Demo data" badge visible | "Fathom is advisory only — it never claims legal compliance and uses public or clearly-labeled synthetic data. Protecting whales and protecting livelihoods isn't a zero-sum fight. It's a routing and information problem. That's Fathom." |

**Recording notes**

- Pause ~1 s on each citation and on the frontier chart so they read on video.
- Keep the "Demo data" badge and advisory disclaimer visible at least once.
- Show only synthetic/public data; never display a real vessel identity.
- Presets are instant; if you must show a custom draw, keep the polygon small
  (the live path is bounded to 8 s and will otherwise ask you to simplify it).
