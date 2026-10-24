# Fathom — Requirements

> Put this file at `.kiro/specs/fathom/requirements.md`

## Introduction

**Fathom** is an ocean decision copilot for Massachusetts' working waterfront. It fuses open ocean, regulatory, and whale-risk data into (1) a **trip planner agent** for fishermen and (2) a **policy what-if simulator** for harbor and fisheries managers. The point is to show that protecting the ocean and protecting coastal livelihoods are a *routing and information problem*, not only a trade-off.

Hackathon tracks: **C5 Sustainable blue economy and coastal livelihoods** (primary), **C4 Understanding and protecting the ocean** (secondary).

## Personas

| Persona | Who | Core need |
|---|---|---|
| **Captain Joe** | Small-boat commercial fisherman out of Gloucester/New Bedford | "Where can I fish safely, legally, and profitably tomorrow, without hitting a closure, a slow zone, or bad weather?" |
| **Dana** | Harbor master / state fisheries analyst / NGO ocean-policy analyst | "If we protect this area, who pays the cost, and how much risk do we actually remove?" |

## Glossary

- **Cell**: one 0.05° x 0.05° grid square of the study area.
- **Protection zone**: any polygon where vessel behavior is restricted (whale seasonal management area, slow zone, fishing closure, wind construction exclusion).
- **Whale risk score**: 0–1 value for expected lethal-encounter risk for a vessel in a cell at a given speed and time.
- **Effort proxy**: historical fishing activity inferred from vessel tracks, used as a stand-in for catch value.
- **Demo mode**: the app running entirely from cached snapshots, with no live network calls.

---

## Requirement 1 — Unified conditions map

**User story:** As Captain Joe, I want one map showing weather, sea state, and water conditions so that I don't check five websites before leaving the dock.

**Acceptance criteria**
1. WHEN the map loads, THE SYSTEM SHALL render wave height, wind, and sea-surface temperature layers for the selected region within 5 seconds.
2. WHEN the user changes the forecast time slider, THE SYSTEM SHALL update all time-dependent layers to that time.
3. IF a live data source is unreachable, THEN THE SYSTEM SHALL use the most recent cached snapshot AND label the layer with its timestamp and a "cached" badge.
4. THE SYSTEM SHALL let the user toggle each layer on and off independently.

## Requirement 2 — Protection and regulatory zones

**User story:** As Captain Joe, I want to see every zone that restricts me so that I never wander into one by accident.

**Acceptance criteria**
1. THE SYSTEM SHALL display whale seasonal management areas, active slow zones, fishing closures, and offshore wind lease/construction areas as distinct, labeled polygons.
2. WHEN the user clicks a zone, THE SYSTEM SHALL show its name, type, effective dates, restriction summary, and source link.
3. WHEN a zone is not active at the selected time, THE SYSTEM SHALL render it as inactive (dimmed) rather than hiding it.
4. THE SYSTEM SHALL always label zone data with its source and last-updated date.

## Requirement 3 — Whale encounter risk

**User story:** As either persona, I want a defensible risk score per area so that decisions are grounded in evidence rather than guesses.

**Acceptance criteria**
1. THE SYSTEM SHALL compute a whale risk score (0–1) for each cell from: seasonal presence prior, recent sighting decay, and vessel speed lethality.
2. WHEN vessel speed increases and all other inputs are fixed, THE SYSTEM SHALL return a risk score that is greater than or equal to the previous one (monotonic in speed).
3. WHEN a new sighting is added inside a cell, THE SYSTEM SHALL increase that cell's and neighboring cells' risk score, decaying with distance and age.
4. WHEN the user selects a cell, THE SYSTEM SHALL show a breakdown of which factors contributed to its score.

## Requirement 4 — Trip planner agent

**User story:** As Captain Joe, I want to describe my trip in plain language and get ranked, safe, legal options so that I can decide quickly.

**Acceptance criteria**
1. WHEN the user submits a trip request (port, vessel type, speed range, target species or ground, departure window, max hours), THE SYSTEM SHALL return 2–3 ranked trip plans.
2. EACH trip plan SHALL include a route, ETA, estimated fuel, weather window, zones crossed, whale risk summary, and expected effort-proxy score.
3. WHEN the agent states a fact about conditions, zones, or risk, THE SYSTEM SHALL attach a citation to the tool result or dataset that produced it.
4. IF the agent cannot ground a claim in a tool result, THEN THE SYSTEM SHALL say it does not know instead of guessing.
5. THE SYSTEM SHALL stream the agent's tool calls to the UI so users can see what it checked.

## Requirement 5 — Route generation

**User story:** As Captain Joe, I want a route that avoids restricted zones and bad weather so that I don't have to plan around them manually.

**Acceptance criteria**
1. THE SYSTEM SHALL generate routes that never cross land and never enter a currently closed or prohibited zone.
2. WHEN a route must cross an active slow zone, THE SYSTEM SHALL cap planned speed inside it at the zone's limit AND include the added time in the ETA.
3. WHEN the user changes the risk-vs-time preference slider, THE SYSTEM SHALL regenerate routes within 3 seconds.
4. IF no legal route exists within the max-hours constraint, THEN THE SYSTEM SHALL say so and suggest which constraint to relax.

## Requirement 6 — Policy what-if simulator

**User story:** As Dana, I want to test a proposed protection zone before it's adopted so that I can see both the ecological benefit and the livelihood cost.

**Acceptance criteria**
1. WHEN the user draws or selects a candidate zone, THE SYSTEM SHALL re-route a representative fleet around it and report: change in risk-weighted vessel-hours, change in added steaming time and fuel, and change in effort-proxy access.
2. THE SYSTEM SHALL present the result as a trade-off view (risk reduced vs. livelihood cost) comparing at least 3 candidate options.
3. WHEN options are compared, THE SYSTEM SHALL highlight which options are on the efficient frontier (no other option is better on both axes).
4. THE SYSTEM SHALL clearly label the effort proxy as an estimate, not actual catch or revenue.
5. THE SYSTEM SHALL generate a plain-language summary a non-technical board member could read.

## Requirement 7 — Multilingual output

**User story:** As a Portuguese- or Spanish-speaking captain, I want trip briefs in my language so that nothing is lost in translation.

**Acceptance criteria**
1. THE SYSTEM SHALL produce trip briefs in English, Portuguese, and Spanish.
2. WHEN the language is changed, THE SYSTEM SHALL keep zone names, coordinates, and numeric values identical across languages.

## Requirement 8 — Printable trip brief and compliance log

**User story:** As Captain Joe, I want a one-page brief I can print or save because I may have no signal at sea.

**Acceptance criteria**
1. WHEN the user accepts a plan, THE SYSTEM SHALL export a one-page brief (PDF or printable HTML) containing route waypoints, zone alerts, weather windows, and data timestamps.
2. THE SYSTEM SHALL record the zones checked and their data timestamps in a trip log the user can export.

## Requirement 9 — Safety, honesty, and scope

**Acceptance criteria**
1. THE SYSTEM SHALL display on every plan that it is advisory only and does not replace official notices, VHF warnings, or the captain's judgment.
2. THE SYSTEM SHALL NOT state that a plan is "legally compliant"; it SHALL say which known zones the plan avoids.
3. THE SYSTEM SHALL use only public or synthetic data and SHALL NOT collect personal data beyond a vessel type and port.

## Requirement 10 — Reliability and demo mode

**Acceptance criteria**
1. THE SYSTEM SHALL run end to end in demo mode using only bundled snapshots.
2. WHEN demo mode is on, THE SYSTEM SHALL show a visible "Demo data" badge.
3. THE SYSTEM SHALL return an agent response or a clear error within 30 seconds.

---

## Out of scope (say this in the pitch)

- Real-time AIS ingestion at scale (we use a historical sample to simulate a fleet).
- Actual catch or revenue data (we use an effort proxy).
- Legal compliance certification.
- Native mobile app.

## Stretch goals (only after the core demo is stable)

- Photo upload: identify a possible right whale or entangled gear and file a report to the right agency contact.
- Offshore wind construction schedule overlay with per-day conflict alerts.
- Voice input for the trip request.
