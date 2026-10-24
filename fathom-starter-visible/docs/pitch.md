# Fathom — Pitch, Demo Script, and Judge Prep

## One-line pitch

**Fathom helps Massachusetts fishermen stay profitable and keep right whales alive, and lets regulators test a protection rule before it hurts anyone.**

## Why this wins (say this to yourselves)

1. **Real, local, famous conflict.** Right whales, fishing closures, and offshore wind all collide in Massachusetts waters. Every MA judge knows the headlines.
2. **Nobody else will pick it.** Most teams go for healthcare or civic chatbots. Ocean is rare, so you stand out.
3. **Real data, no private documents.** Public ocean data, so no access problem.
4. **The LLM is not the product.** The risk engine and router are real and tested. The agent orchestrates and explains. That reads as serious engineering.
5. **The what-if simulator is the memorable moment.** It turns "save whales vs. save jobs" into a measurable trade-off.
6. **Kiro is visibly used in depth:** specs, steering, hooks, and an MCP server Kiro itself used.

---

## 3-minute pitch structure

**0:00–0:25 — Story, not stats**
"Captain Joe leaves Gloucester at 4 a.m. Between him and his fishing ground are a whale slow zone that changed yesterday, a closure, a wind construction area, and a wave forecast that gets worse by noon. He checks five websites and guesses. If he guesses wrong he loses a day of fuel, a fine, or hits a whale."

**0:25–0:50 — Problem on both sides**
"On the other side of the same ocean, a fisheries manager has to decide whether to close an area. She can see the whale data. She cannot see what it costs the fleet. So the debate becomes whales versus jobs, when it's really a routing and information problem."

**0:50–1:00 — Solution**
"Fathom gives both of them the same trusted picture of the ocean."

**1:00–2:15 — Live demo** (script below)

**2:15–2:45 — How it's built, briefly**
"The LLM never computes risk. A tested engine does: sightings, seasonal presence, and a published speed-lethality curve. The agent calls tools and cites every claim. Our data layer is an MCP server that Kiro used while building it."

**2:45–3:00 — Close**
"Harbor masters, fishermen's associations, NOAA partners, and offshore wind developers all need this. Whales and fishermen don't have to lose for the other to win."

---

## Demo script (practice until it takes < 75 seconds)

**Pre-loaded:** demo mode on a stable snapshot day in whale season, Captain mode open, Gloucester selected.

1. **Show the map (10s).** Toggle layers: conditions, zones, risk heatmap. Click a slow zone: name, dates, source link appear. *"Everything has a source and a timestamp."*
2. **Type the request (10s):** "Leaving Gloucester at 5am, 12-hour trip, small boat, 9 knots, want to fish near Stellwagen. I want the safest option that still gets me there."
3. **Watch the agent (15s).** Tool calls stream: get_zones, get_whale_risk, plan_routes. *"It's not guessing. It's calling tools."*
4. **Show 3 plans (15s).** Open "why" on the best one: zones avoided, risk reduced X% for Y extra minutes, weather window, citations.
5. **Slide the risk preference (5s).** The route visibly shifts.
6. **Switch to Portuguese (5s).** Same numbers, new language. *"New Bedford's fleet is largely Portuguese-speaking."*
7. **Manager mode (20s).** Select the "extend closure east" scenario, then "seasonal speed limit." Show the trade-off chart: risk removed vs. fleet cost. Highlight the efficient option.
8. **Read the summary (5s).** One plain sentence a board member could repeat.

**Backup plan:** if live breaks, flip to the recorded video immediately and keep talking.

---

## "How Kiro built this" slide (judges will look for this)

- **Spec-driven:** show the requirements (EARS), design, and tasks files. Say how many requirements and tasks you completed.
- **Steering:** show product/tech/data-and-safety files. "Kiro knew our safety rules without us repeating them."
- **Hooks:** show a screenshot of the risk-test hook catching or confirming an invariant, and the citation-guard hook.
- **MCP:** screenshot Kiro calling `fathom` MCP to look up real zones while writing tests.
- **Honest metric:** e.g., "X% of code merged was generated from spec tasks; Y bugs caught by hooks." Use real numbers only.

---

## Likely judge questions and answers

**"Where does your data come from?"** Name each source on one slide. Say which layers are live, cached, or synthetic. *Honesty is the strongest answer.*

**"Is the whale risk model validated?"** "It's a transparent screening model based on published speed-lethality research and sighting patterns, not a prediction. Parameters are in a config file and every cell shows its breakdown. A real deployment would be calibrated with NOAA and WHOI scientists."

**"Does it replace official notices?"** "No. It's advisory and says so on every plan. It helps people act on official data faster."

**"What about catch and revenue?"** "We don't have catch data, so we use fishing-effort patterns from vessel tracks as a proxy and label it. Partnering with fishermen's associations would let us replace it with real data."

**"Why would fishermen trust it?"** "Every claim is cited, there's no black box, it works from a printed brief, and it speaks their language."

**"What's the business or adoption path?"** Free tier for fishermen via harbor masters and associations; paid dashboards for state agencies, NGOs, and wind developers who need conflict forecasting.

**"What would you build next?"** Live AIS, real-time acoustic detections, wind construction schedule alerts, fisherman feedback loop for closures.

---

## Facts to verify before they go on a slide

I did not verify these. Check each against NOAA or the original paper and cite it on the slide:
- Current estimate of the North Atlantic right whale population.
- Vanderlaan & Taggart (2007) lethality numbers (speed at which lethal injury probability reaches ~50%).
- Exact dates and speed limits of current seasonal management areas and slow zones.
- Names and boundaries of wind lease areas you display.

## Team roles on stage

- **Speaker 1 (D):** story and close.
- **Speaker 2 (C):** live demo driver.
- **Speaker 3 (B):** technical architecture and Kiro slide.
- **Speaker 4 (A):** data honesty, Q&A on the model.
