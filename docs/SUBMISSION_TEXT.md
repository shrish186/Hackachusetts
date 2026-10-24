# Submission

**Track:** Climate Tech & Clean Energy (blue economy, coastal livelihoods, ocean protection)
**Live app:** https://fathom-six-vert.vercel.app
**Repository:** https://github.com/shrish186/Hackachusetts
**Team (4):** Vidhaan, Shrish, Anant, Aayush

## Project description (~210 words)

Fathom is an ocean decision copilot for Massachusetts' working waterfront. In
these waters, endangered right whales, fishing closures, seasonal slow zones,
offshore wind, and fast-changing weather all overlap — and the people affected
make decisions from scattered sources. Fathom gives them one trusted picture.

For a fisherman, it turns a plain-language trip request ("leaving Gloucester at
5am, 12-hour trip, small boat, 9 knots, fish near Stellwagen, safest option")
into 2–3 ranked routes that avoid closures, respect slow-zone speed limits, and
weigh whale risk against time — each with a cited "why" and a printable brief in
English, Portuguese, or Spanish.

For a harbor or fisheries manager, Fathom's what-if simulator re-routes a
representative fleet around a candidate protection zone and reports the
trade-off: whale risk removed versus the cost in steaming hours, fuel, and lost
access to fishing grounds. Options are compared on a Pareto frontier, so a
seasonal speed limit that removes most of the risk at a fraction of a closure's
cost is obvious at a glance.

The engineering point: the language model never computes risk, routes, or zone
facts — a deterministic, tested Python engine does, and the agent must cite every
number. The same engine is exposed as an MCP server.

## How to test

No keys needed — demo mode runs from bundled public/synthetic data.

1. Open the live app and accept the intro card. Toggle the weather, zones, and
   risk layers; click a zone to see its dates and source.
2. **Captain mode:** click "Try the demo trip," watch the agent stream its tool
   calls, open a plan's "why" to see citations, drag the risk slider, switch the
   language (numbers stay identical).
3. **Manager mode:** pick a preset scenario (extend closure east / dynamic zone /
   seasonal speed limit) — results are instant (precomputed) — and read the
   trade-off chart and the plain-language summary.
4. **Run the tests:** `cd backend && pip install -r requirements.txt && pytest -q`
   (112 tests, including Hypothesis property tests).

API quick check:
```
curl -X POST https://fathom-six-vert.vercel.app/api/sim/run \
  -H 'Content-Type: application/json' -d '{"scenario_id":"seasonal_speed_limit"}'
```

## Data honesty

Fathom uses only public or synthetic data. Every layer carries its source,
fetch time, and a cached/synthetic flag; anything not from a real source is
flagged `synthetic: true` and badged in the UI. The whale-risk model is a
transparent screening tool based on the Vanderlaan & Taggart (2007) vessel-strike
lethality curve — not a prediction — and the fishing-effort figure is an estimate
of activity, **not** catch or revenue. The fleet in the simulator is synthetic
and anonymized; no real vessel identity is shown.

## Safety

Advisory only. Fathom does not replace official NOAA notices, VHF warnings, or
the captain's judgment, and it never states that a plan is "legally compliant" —
it reports which known zones a plan avoids. This appears on every plan.
