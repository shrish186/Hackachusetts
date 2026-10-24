# Kiro evidence log

Real events only. This file feeds KIRO_WRITEUP.md. Hooks append here; humans can add lines too.
Format: `YYYY-MM-DD HH:MM | who | tool (IDE/CLI/Web/Crew) | what happened | issue caught (if any)`

2026-10-24 | setup | IDE | Spec, steering, hooks and MCP config created and committed |
2026-10-24 | Lane A | Web | Tasks 1.1-1.4.1: grid+land mask, zone ingest, conditions ingest (cache flag), whale risk model (config/risk.yaml) + Hypothesis property tests (bounded [0,1], monotonic in speed, 0 on land, adding a sighting never lowers risk). 27 Lane A tests pass. | Preserved "adding a sighting never lowers risk" by mapping presence with a fixed saturating transform (1-exp(-density/scale)) instead of data-dependent max-normalization, which would couple cells and could lower risk.
2026-10-24 | Lane A | Web | CROSS-LANE HANDOFF for Lane B: shipping real data/snapshots/conditions.json flips that layer's provenance from synthetic->cached in _snapshots.py (by design). This makes tests/test_layers_api.py::test_req1_conditions_layer_has_provenance fail (it asserts synthetic is True). I did NOT edit Lane B's test (testing-pbt: never edit a test to make it pass). Lane B: the conditions layer is now legitimately cached (real NOAA buoy snapshot), not synthetic -- please update that assertion to expect cached=True / synthetic=False. The real risk model in app/engine/risk.py is also ready to replace app/api/_risk_stub.py when Lane B wires it. | Stale cross-lane test assumption surfaced; flagged rather than silently changed.
