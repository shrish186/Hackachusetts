# How we used Kiro to build Fathom

> **First draft** assembled from `docs/kiro-evidence/LOG.md` and the real git
> history. Every claim below is traceable to a commit or a log line; TODOs mark
> where a teammate should add a screenshot or a final number before submission.
> Judges score depth of understanding and experimentation — specific beats long.

## 1. Which Kiro tools did we use?

- **Kiro CLI** — primary driver for Lane D (product/QA/MCP/docs): CI, security,
  the what-if simulator, MCP wiring, and these docs, committing after each task.
- **Kiro Web** — Lanes A and B worked from the Web client (per the evidence log):
  data ingest, the risk model, the API, and security hardening.
- **Kiro IDE** — initial project setup: spec, steering, hooks, and MCP config.
- Kiro Crew: TODO — state whether used.

We ran four parallel lanes (A data/geo, B backend/agent, C frontend, D
product/QA/MCP/story) against a shared `main`, which is why the git history
interleaves lanes and why our steering defines strict file ownership.

## 2. Spec-driven development

- The spec lives in [`.kiro/specs/fathom/`](.kiro/specs/fathom/):
  `requirements.md` (10 requirements in EARS form), `design.md` (14 sections:
  grid, risk model, routing, agent, simulator), and `tasks.md`.
- Spec-driven paid off most on the **deterministic engine**. The risk model was
  built straight from design §5 and requirements §3, including the invariants —
  and those invariants became property tests (see §6). Example commit:
  `0f840c3 Lane A: grid+land mask, zone/conditions ingest, whale risk model`.
- The **simulator** (this round) was coded directly against design §8: synthetic
  fleet, baseline vs. scenario, percent deltas, Pareto frontier, trilingual
  summaries — a well-specified task that a sub-agent could execute end to end.
- Vibe coding stayed useful for UI polish (Lane C) and doc wording.
- TODO: final count of tasks Kiro completed vs. total.

## 3. Agent hooks

Hooks live in [`.kiro/hooks/`](.kiro/hooks/). Real moments:

- **Risk model guard** (`risk-tests-on-save`) — on changes to `engine/**` or
  `config/risk.yaml`, runs the property tests and forbids editing tests to pass.
- **Citation guard** (`citation-guard-on-agent-change`) — enforces that agent
  output cites a tool result for every number/zone/date.
- **Plain-language check** (`plain-language-check`).
- **Evidence logger** (`evidence-log-on-task-done`) — appends to
  `docs/kiro-evidence/LOG.md`, which is the source for this write-up.
- **Secret scan on save** (`secret-scan`, added this round) — flags API keys,
  tokens, private keys, and raw `.env` content before they can be committed.
- TODO: screenshot of a hook catching/confirming an invariant.

## 4. Steering docs

Files in [`.kiro/steering/`](.kiro/steering/): `product.md`, `tech.md`,
`structure.md` (the lane ownership that kept four people off each other's files),
`data-and-safety.md`, and `testing-pbt.md`.

The highest-impact rule was **data-and-safety**: "anything not from a real source
must say `synthetic: true`." It drove a real honesty fix —
`d2bb1b7 Lane A (1.1): honesty fix — mark hand-authored snapshots synthetic:true`
— where hand-written data had been mislabeled as real and was corrected before
the demo. The safety rules also kept the agent from ever claiming "legally
compliant."

## 5. MCP

- **`fetch` MCP** — used for the hour-0 data reality check against public sources.
- **Our own `fathom` MCP server** ([`mcp/fathom_mcp/`](mcp/fathom_mcp/)) exposes
  the eight engine tools (design §7). This round we wired `get_zones`,
  `get_whale_risk`, `get_effort_proxy`, and `simulate_zone` to the real backend
  engine via a bridge (`b4f3623`), with graceful placeholder fallback when the
  backend isn't importable. `python -m fathom_mcp` boots clean, so we enabled the
  server in `.kiro/settings/mcp.json`.
- Payoff: Kiro (and the in-app agent) can query the **same** tested engine while
  we write code — e.g. asking the real zones/risk at the demo date instead of
  guessing — which is both a dev accelerator and a trust story.

## 6. Property-based testing

Using Hypothesis (steering `testing-pbt.md`), mapped to requirements:

- Risk ∈ [0,1]; risk monotonic non-decreasing in speed (Req 3.2); risk 0 on land
  (Req 3); adding a sighting never lowers risk (Req 3.3). 27 Lane A tests.
- Simulator (Req 6): no Pareto-frontier option is dominated; deltas consistent
  with totals; en/pt/es summaries carry identical numbers (Req 7.2).
- A real design insight surfaced via the invariants: to keep "adding a sighting
  never lowers risk," presence is mapped with a fixed saturating transform
  `1 - exp(-density/scale)` instead of data-dependent max-normalization, which
  would couple cells and could *lower* another cell's risk (logged 2026-10-24).
- TODO: paste a concrete Hypothesis counterexample if one was captured.

## 7. Kiro powers / integrations

- Powers available in-session included GitHub CLI (used for push/PR flow) and
  fetch/browser tooling.
- TODO: confirm the final list the team actually relied on.

## 8. Honest lessons

- **What worked:** strict lane ownership + commit-after-each-task + rebase-before-push
  kept four parallel contributors on one green `main`. The deterministic-engine /
  LLM-orchestrator split made the agent trustworthy and testable.
- **What was bumpy:** cross-lane interface churn. A mid-round refactor removed
  `app/api/_snapshots.py` and briefly broke `sim.py` on import; we caught it
  locally and shipped a one-line hotfix (`10233c9`). The evidence log's
  cross-lane handoff notes were essential to resolving these quickly.
- **What we'd do differently:** pin cross-lane interfaces (the router's
  `route_one` signature, the snapshot loader) in a contract doc earlier so
  dependent lanes aren't chasing renames under a deadline.

---

### Honesty note

As of this draft, the agent's routing (`plan_routes`) and the printable brief
(`export_brief`) are not yet wired to a real router/renderer, so those MCP tools
still return clearly-labeled placeholders. The risk model, zones, effort proxy,
and the what-if simulator are real and tested.
