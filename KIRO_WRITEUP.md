# How we used Kiro to build Fathom

> Fill every section with REAL details and screenshots from `docs/kiro-evidence/`. Judges score "depth of understanding" and "experimentation". Specific beats long. Delete the hint lines when done.

## 1. Which Kiro tools did we use?
- Kiro IDE: (what for)
- Kiro CLI: (what for, and how it differed from the IDE)
- Kiro Web: (if used)
- Kiro Crew: (if used)

_Hint: even a small honest use of CLI or Web counts. Say what felt different._

## 2. Spec-driven development
- How we structured the spec (requirements in EARS format, design, tasks): link to `.kiro/specs/fathom/`
- How many requirements / tasks, and how many Kiro completed:
- What spec-driven did better than vibe coding (a concrete example, e.g. the routing engine):
- What vibe coding was still good for (UI polish):

## 3. Agent hooks
For each hook: what triggers it, what it automates, one real moment it helped.
- Risk model guard:
- Citation guard:
- Plain-language check:
- Evidence logger:

## 4. Steering docs
- Files we wrote and why: product, tech, structure (lanes), data-and-safety, testing-pbt
- The strategy that made the biggest difference (example: the safety rules meant Kiro never wrote "legally compliant"):

## 5. MCP
- `fetch` MCP: how it helped with the data reality check
- Our own `fathom` MCP server: tools exposed, how Kiro used them while building, how the in-app agent uses the same server
- What this made possible that would have been hard otherwise:

## 6. Property-based testing
- Properties we enabled and which requirements they map to:
- A real counterexample Hypothesis found that unit tests would have missed:

## 7. Kiro powers / integrations
- Powers used:
- Third-party tools we would not otherwise have used:

## 8. Honest lessons
- What worked, what did not, what we would do differently:
