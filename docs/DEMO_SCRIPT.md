# Fathom — demo video script (2:40)

Target length **2 minutes 40 seconds**. Screen recording + voiceover only.
**No music, no logos, no intro animation.** Pre-load: demo mode on a whale-season
snapshot day (15 March), Captain mode open, Gloucester selected. Practice until
the live portion fits its windows; if anything breaks, cut to a backup clip and
keep talking.

| Time | On screen | Voiceover |
|------|-----------|-----------|
| 0:00–0:20 | Static map of Massachusetts Bay with zones visible | "At 4 a.m. Captain Joe leaves Gloucester. Between him and his fishing ground: a whale slow zone that changed yesterday, a closure, a wind construction area, and weather that turns by noon. Today he checks five websites and guesses." |
| 0:20–0:35 | Pan to the open water / a zone outline | "On the other side of the same ocean, a fisheries manager has to decide whether to close an area. She sees the whale data. She can't see what it costs the fleet. So it becomes whales versus jobs — when it's really a routing and information problem." |
| 0:35–0:45 | Fathom app, full map with layer toggles | "Fathom gives both of them the same trusted picture of the ocean." |
| 0:45–1:00 | Toggle conditions, zones, risk heatmap; click a slow zone → popup with name, dates, source link | "Weather, regulatory zones, whale risk — one map. Click any zone: name, effective dates, and a source link. Everything carries a source and a timestamp." |
| 1:00–1:15 | Type into Captain panel: "Leaving Gloucester at 5am, 12-hour trip, small boat, 9 knots, fish near Stellwagen — safest option that still gets me there." | "The captain just types the trip in plain language." |
| 1:15–1:35 | Agent feed streams tool calls: get_zones, get_whale_risk, plan_routes | "Watch the agent. It isn't guessing — it's calling tested tools. The language model never computes the risk or the route. A deterministic engine does, using sighting data and a published speed-lethality curve." |
| 1:35–1:55 | Three ranked plans; open "why" on the top one: zones avoided, risk reduced %, extra minutes, weather window, citations | "Three ranked plans. Open 'why': which zones it avoids, how much risk it removes for how many extra minutes, and a citation on every number." |
| 1:55–2:05 | Drag risk-preference slider; route visibly shifts. Then switch language to Portuguese | "Slide from fastest to safest — the route shifts. Switch to Portuguese for New Bedford's fleet. Same numbers, new language." |
| 2:05–2:30 | Manager mode. Select "extend closure east," then "seasonal 10-knot speed limit." Trade-off chart: risk removed vs. fleet cost; efficient option highlighted | "Now the manager. Test a candidate: extend the closure east. Then a seasonal speed limit instead. Fathom re-routes a whole fleet and shows the trade-off — risk removed versus livelihood cost — and highlights the efficient option. Often a speed limit removes most of the risk at a fraction of a closure's cost. Effort is an estimate, not revenue, and we say so." |
| 2:30–2:40 | Plain-language summary sentence on screen; advisory disclaimer visible | "One sentence a board member could repeat. Advisory only — and built with Kiro, spec-driven, with an MCP server Kiro used while writing the code. Whales and fishermen don't have to lose for the other to win." |

**Recording notes**

- Keep the cursor deliberate; pause ~1 s on each citation and the trade-off chart.
- Make sure the "Demo data" badge and the advisory disclaimer are visible at least once.
- Show only synthetic/public data; do not display any real vessel identity.
