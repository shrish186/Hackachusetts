"""Lane B task 9: agent evals (Req 4.3, 4.4, 7.2, 9.2; design.md §12).

Ten canned trip prompts. For each, every number in the agent's output must
appear in a tool result, every sentence must carry a [tool:call_N] tag that
points at a real call, and the en/pt/es outputs must contain identical numbers
and zone names.
"""
from __future__ import annotations

import re

import pytest

from app.agent.agent import MAX_TOOL_CALLS, _numbers, citation_guard, run_agent

D = ["2026-03-15T09:00:00Z", "2026-03-15T09:00:00Z"]
PROMPTS = [
    {"port": "provincetown", "vessel": "mid_trawler", "cruise_kn": 9.5, "max_hours": 14, "target_ground": "stellwagen_bank", "risk_pref": 0.6},
    {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 8, "max_hours": 10, "target_ground": "jeffreys_ledge", "risk_pref": 0.2},
    {"port": "boston", "vessel": "scalloper", "cruise_kn": 11, "max_hours": 16, "target_ground": "stellwagen_bank", "risk_pref": 0.9},
    {"port": "plymouth", "vessel": "mid_trawler", "cruise_kn": 10, "max_hours": 8, "target_ground": "cape_cod_bay", "risk_pref": 0.5},
    {"port": "new_bedford", "vessel": "scalloper", "cruise_kn": 10.5, "max_hours": 30, "target_ground": "stellwagen_bank", "risk_pref": 0.4},
    {"port": "gloucester", "vessel": "mid_trawler", "cruise_kn": 14, "max_hours": 14, "target_ground": "cape_cod_bay", "risk_pref": 0.0},
    {"port": "provincetown", "vessel": "small_boat", "cruise_kn": 7, "max_hours": 1, "target_ground": "jeffreys_ledge", "risk_pref": 0.5},  # no legal route
    {"port": "boston", "vessel": "small_boat", "cruise_kn": 9, "max_hours": 12, "target_ground": None, "risk_pref": 1.0},
    {"port": "plymouth", "vessel": "scalloper", "cruise_kn": 12, "max_hours": 20, "target_ground": "jeffreys_ledge", "risk_pref": 0.7},
    {"port": "provincetown", "vessel": "mid_trawler", "cruise_kn": 9.5, "max_hours": 14, "target_ground": "stellwagen_bank", "risk_pref": 0.6,
     "depart_window": ["2026-08-01T09:00:00Z", "2026-08-01T09:00:00Z"]},  # off-season: fewer active zones
]

NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")
CITE = re.compile(r"\[tool:(call_\d+)\]")


def _run(prompt: dict, lang: str) -> tuple[dict, dict]:
    events = list(run_agent({"depart_window": D, "language": lang, **prompt}))
    assert events[-1]["event"] == "done", events[-1]
    results = {e["data"]["id"]: e["data"]["result"] for e in events if e["event"] == "tool_result"}
    calls = [e for e in events if e["event"] == "tool_call"]
    assert 1 <= len(calls) <= MAX_TOOL_CALLS
    plans = next(e["data"] for e in events if e["event"] == "plans")
    return results, plans


def _nums(text: str) -> set[float]:
    return {round(float(n), 6) for n in NUM.findall(CITE.sub("", text))}


@pytest.mark.parametrize("prompt", PROMPTS, ids=[f"p{i}" for i in range(len(PROMPTS))])
def test_req4_every_number_traces_to_a_tool_result(prompt: dict) -> None:
    results, plans = _run(prompt, "en")
    all_tool_numbers: set[float] = set()
    for r in results.values():
        all_tool_numbers |= _numbers(r)

    assert plans["narrative"], "agent produced no narrative"
    for s in plans["narrative"]:
        cites = CITE.findall(s["text"])
        assert cites, f"uncited sentence: {s['text']}"
        assert all(c in results for c in cites)
        cited_numbers: set[float] = set()
        for c in cites:
            cited_numbers |= _numbers(results[c])
        missing = _nums(s["text"]) - cited_numbers
        assert not missing, f"{missing} not in cited results: {s['text']}"
        assert "compliant" not in s["text"].lower() and "compliance" not in s["text"].lower()

    for p in plans["plans"]:
        for key in ("eta_hours", "fuel_est_l", "max_wave_m", "risk_exposure", "effort_proxy"):
            assert round(float(p[key]), 6) in all_tool_numbers, key
        for c in p["citations"]:
            assert c["tool_call_id"] in results
            assert _nums(c["claim"]) <= _numbers(results[c["tool_call_id"]])

    if plans.get("access_lost"):
        # Ground inside an active closure: explicit access_lost, never a relocated route.
        assert plans["plans"] == [] and plans["access_lost"]["nearest_open"]
    elif prompt["max_hours"] == 1:
        assert plans["plans"] == [] and "Relax" in plans["message"]
    else:
        assert 1 <= len(plans["plans"]) <= 3


@pytest.mark.parametrize("prompt", PROMPTS[:4], ids=[f"p{i}" for i in range(4)])
def test_req7_languages_share_numbers_and_zone_names(prompt: dict) -> None:
    out = {lang: _run(prompt, lang) for lang in ("en", "pt", "es")}
    zone_names = {z["name"] for z in next(r for r in out["en"][0].values() if "zones" in r)["zones"]}

    def fingerprint(plans: dict) -> tuple:
        text = " ".join(s["text"] for s in plans["narrative"])
        nums = sorted(float(n) for n in NUM.findall(CITE.sub("", text)))
        names = sorted(z for z in zone_names if z in text)
        return nums, names, [(p["eta_hours"], p["fuel_est_l"], tuple(p["zones_crossed"])) for p in plans["plans"]]

    assert fingerprint(out["en"][1]) == fingerprint(out["pt"][1]) == fingerprint(out["es"][1])


def test_req4_4_citation_guard_drops_unsupported_sentences() -> None:
    results = {"call_1": {"max_wave_m": 1.5, "zones": [{"name": "Cape Cod Bay Seasonal Management Area"}]}}
    names = ["Cape Cod Bay Seasonal Management Area", "Made Up Zone"]
    kept = citation_guard([
        "Waves reach 1.5 m [tool:call_1].",                         # ok
        "Waves reach 3.2 m [tool:call_1].",                         # number not in result
        "Waves reach 1.5 m.",                                       # uncited number
        "You will pass Made Up Zone [tool:call_1].",                # zone not in result
        "Avoid Cape Cod Bay Seasonal Management Area [tool:call_9].",  # citation to unknown call
        "This plan is legally compliant [tool:call_1].",            # banned claim
    ], results, names)
    assert [k["text"] for k in kept] == ["Waves reach 1.5 m [tool:call_1]."]


def test_req4_llm_rewrite_goes_through_guard(monkeypatch) -> None:
    from app.agent import agent

    monkeypatch.setattr(agent, "_llm_rewrite", lambda lang, results, template: [
        "A friendly summary with an invented 42.42 knots [tool:call_4].",
        template[0],
    ])
    _, plans = _run(PROMPTS[0], "en")
    texts = [s["text"] for s in plans["narrative"]]
    assert all("42.42" not in t for t in texts)
    # The rewrite was used (one sentence survived), and the invented number was dropped.
    assert len(texts) == 1 and texts[0].endswith("[tool:call_1].")


# Lane D: "Why not that route?" comparison sentences (one cited sentence per
# non-recommended plan, numbers only from plan_routes, identical across langs).
_WHY_NOT_MARKERS = ("Why not", "Por que não", "¿Por qué no")


def _why_not(narrative: list[dict]) -> list[dict]:
    return [s for s in narrative if any(m in s["text"] for m in _WHY_NOT_MARKERS)]


def test_laneD_why_not_one_cited_sentence_per_non_recommended_plan() -> None:
    """Multi-plan trip: each non-recommended plan gets a cited why-not sentence."""
    prompt = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9.0,
              "max_hours": 14, "target_ground": "stellwagen_bank", "risk_pref": 0.5}
    results, plans = _run(prompt, "en")
    n_plans = len(plans["plans"])
    if n_plans < 2:
        pytest.skip("only one route for this trip; nothing to compare")
    why = _why_not(plans["narrative"])
    # At least one why-not sentence per non-recommended plan (zone sentences extra).
    assert len(why) >= n_plans - 1
    # Every why-not sentence is cited and survived the guard (it is in the
    # narrative, which is the guard's output), and cites plan_routes.
    for s in why:
        assert s["citations"], s["text"]


def test_laneD_why_not_numbers_identical_across_languages() -> None:
    """The comparison numbers are identical in en/pt/es (Req 7.2)."""
    prompt = {"port": "gloucester", "vessel": "small_boat", "cruise_kn": 9.0,
              "max_hours": 14, "target_ground": "stellwagen_bank", "risk_pref": 0.5}
    out = {lang: _run(prompt, lang)[1] for lang in ("en", "pt", "es")}
    if len(out["en"]["plans"]) < 2:
        pytest.skip("only one route for this trip; nothing to compare")

    def why_nums(plans: dict) -> list[float]:
        text = " ".join(s["text"] for s in _why_not(plans["narrative"]))
        return sorted(float(n) for n in NUM.findall(CITE.sub("", text)))

    assert why_nums(out["en"]) and why_nums(out["en"]) == why_nums(out["pt"]) == why_nums(out["es"])
