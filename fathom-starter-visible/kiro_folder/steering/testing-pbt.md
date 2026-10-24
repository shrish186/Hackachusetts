---
inclusion: fileMatch
fileMatchPattern: "backend/tests/**/*.py"
---
# Property-based testing rules
Use Hypothesis for invariants, plain pytest for examples. Required properties (one test each, name starts with the requirement number):
- risk(cell, t, speed) is always within [0, 1]
- risk is monotonic non-decreasing in speed when everything else is fixed
- risk is 0 for land cells
- adding a sighting never lowers risk in any cell
- a route never contains a land cell
- a route never enters an active prohibited zone
- Pareto frontier: no returned frontier option is dominated by another option
- Portuguese/Spanish/English briefs contain identical numbers and zone names
When a property test fails, keep the minimized counterexample in the test as a regression example and note it in docs/kiro-evidence/LOG.md (this is evidence for the Kiro write-up).
Never edit a test to make it pass. Fix the code or ask.
