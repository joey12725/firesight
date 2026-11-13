import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import assistant  # noqa: E402
import scenarios  # noqa: E402
import storage  # noqa: E402

EXAMPLES = storage.list_example_profiles()


def small(profile, runs=4, years=3):
    return {**profile, "num_simulations": runs, "simulate_years": years}


@pytest.mark.parametrize("slug", sorted(EXAMPLES))
def test_example_profiles_are_complete_and_run(slug):
    example = EXAMPLES[slug]
    assert example["title"] and example["summary"]
    summary, results = scenarios.run(small(example["profile"]), seed=1)
    assert summary["runs"] == 4 and len(results) == 4
    assert summary["annual_income"] > summary["annual_expenses"] > 0
    assert 0 < summary["savings_rate"] < 1


def test_example_profiles_reach_fi_within_their_horizon():
    profile = EXAMPLES["side-hustle-landlord"]["profile"]
    summary, _ = scenarios.run({**profile, "num_simulations": 10}, seed=3)
    assert summary["runs_reaching_fi"] >= 5
    assert profile["age"] < summary["median_retirement_age"] < profile["age"] + profile["simulate_years"]


def test_apply_changes_does_not_touch_original():
    base = EXAMPLES["early-career-saver"]["profile"]
    snapshot = json.dumps(base, sort_keys=True)
    new = scenarios.apply_changes(base, {
        "income_multiplier": 1.5,
        "budget_changes": {"rent": 1000},
        "remove_budget_items": ["gym"],
        "new_budget_items": [{"name": "Dog", "value": 150, "frequency": "monthly"}],
        "allocation": {"Index Funds": 3, "Bonds": 1},
        "post_retirement_expenses": 60000,
    })
    assert json.dumps(base, sort_keys=True) == snapshot
    assert new["income"][0]["amount"] == base["income"][0]["amount"] * 1.5
    assert next(b for b in new["budget_items"] if b["type"] == "rent")["value"] == 1000
    assert not any(b["type"] == "gym" for b in new["budget_items"])
    assert any(b["name"] == "Dog" for b in new["budget_items"])
    assert new["investment_index_funds"] == 75 and new["investment_bonds"] == 25
    assert new["investment_retirement_accounts"] == 0
    assert new["post_retirement_expenses"] == 60000


def test_compare_with_no_changes_is_identical_on_shared_seed():
    profile = small(EXAMPLES["dual-income-family"]["profile"])
    result = scenarios.compare(profile, {}, seed=11)
    assert result["baseline"]["median_final_net_worth"] == pytest.approx(result["scenario"]["median_final_net_worth"])


def test_spending_less_retires_earlier():
    profile = {**EXAMPLES["early-career-saver"]["profile"], "num_simulations": 8}
    result = scenarios.compare(profile, {"post_retirement_expenses": 35000, "income_multiplier": 1.3}, seed=5)
    assert result["scenario"]["success_rate"] >= result["baseline"]["success_rate"]
    assert result["scenario"]["median_retirement_age"] < (result["baseline"]["median_retirement_age"] or 999)


def test_password_hashing_round_trip_and_legacy_sha256():
    stored = storage.hash_password("hunter22")
    assert stored.startswith("pbkdf2_sha256$")
    assert storage.verify_password("hunter22", stored)
    assert not storage.verify_password("wrong", stored)
    legacy = "9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c"  # sha256("pass123")
    assert storage.verify_password("pass123", legacy)


def test_local_store_accounts_and_profiles(tmp_path):
    store = storage.LocalStore(tmp_path / "users.json")
    user_id = store.create_user("Someone@Example.com", "pw")
    assert store.find_by_email("someone@example.com")["userid"] == user_id
    assert json.loads(store.get_profile_json(user_id)) == {}
    store.put_profile_json(user_id, json.dumps({"age": 40}))
    assert json.loads(store.get_profile_json(user_id)) == {"age": 40}


# ---- FIRESight GPT tool loop, with a scripted stand-in for the Claude client ----
def block(**kw):
    return SimpleNamespace(**kw)


def test_assistant_runs_tools_and_returns_final_text():
    profile = small(EXAMPLES["side-hustle-landlord"]["profile"])
    replies = [
        SimpleNamespace(stop_reason="tool_use", content=[
            block(type="text", text="Running your plan."),
            block(type="tool_use", id="t1", name="scenario_analysis",
                  input={"changes": {"budget_changes": {"dining_out": 100}}, "charts": ["net_worth_comparison"]}),
        ]),
        SimpleNamespace(stop_reason="end_turn", content=[block(type="text", text="Cutting dining out helps a little.")]),
    ]
    sent, payloads = [], []

    def fake_create(messages):
        sent.append(list(messages))
        return replies.pop(0)

    messages = [{"role": "user", "content": "What if I eat out less?"}]
    reply = assistant.run_turn(fake_create, messages, profile, on_tool_result=payloads.append, seed=2)
    assert reply == "Cutting dining out helps a little."
    tool_result = messages[2]["content"][0]
    assert tool_result["tool_use_id"] == "t1" and "is_error" not in tool_result
    assert set(json.loads(tool_result["content"])) == {"baseline", "scenario"}
    assert payloads[0]["kind"] == "scenario" and payloads[0]["charts"] == ["net_worth_comparison"]
    assert len(sent) == 2


def test_assistant_reports_bad_tool_input_as_error():
    text, payload, is_error = assistant.execute_tool(
        "scenario_analysis", {"changes": {"allocation": {"Bonds": 0}}}, small(EXAMPLES["early-career-saver"]["profile"]))
    assert is_error and payload is None and text.startswith("Error")
