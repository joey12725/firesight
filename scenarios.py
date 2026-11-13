"""What-if helpers shared by the Scenario Analysis page and FIRESight GPT.

``apply_changes`` takes a saved profile plus a flat dict of tweaks (easy to
build from a form or from an LLM tool call) and returns a new profile.
``compare`` runs the baseline and the scenario on the same random seed, so the
difference between them comes from the change and not from luck.
"""
from __future__ import annotations

import copy
import random

import numpy as np

from FIRE import INVESTMENT_TYPES, User, run_monte_carlo_simulation

ALLOCATION_KEYS = {name: f"investment_{name.lower().replace(' ', '_').replace('-', '_')}"
                   for name in INVESTMENT_TYPES}

# Top-level profile fields a scenario may overwrite directly
SCALAR_FIELDS = {
    "post_retirement_expenses": float,
    "average_post_retirement_income": float,
    "withdrawal_rate": float,
    "inflation": float,
    "expenditure_growth_beyond_inflation": float,
    "simulate_years": int,
    "num_simulations": int,
    "married": bool,
    "dependents": int,
}


def _matches(item: dict, name: str) -> bool:
    name = name.strip().lower()
    return name in {str(item.get("name", "")).strip().lower(), str(item.get("type", "")).strip().lower()}


def apply_changes(profile: dict, changes: dict) -> dict:
    """Return a copy of ``profile`` with ``changes`` applied.

    Supported keys:

    * any of ``SCALAR_FIELDS`` (e.g. ``post_retirement_expenses``, ``inflation``)
    * ``income_multiplier``: scale every income amount (1.1 = a 10% raise)
    * ``income_growth_percent``: annual raise applied to every salary/bonus
    * ``budget_changes``: ``{budget item name or type: new value}``
    * ``new_budget_items``: list of ``{name, value, frequency}``
    * ``remove_budget_items``: list of budget item names or types
    * ``allocation``: ``{"Index Funds": 80, "Bonds": 20, ...}``, rescaled to 100%
    * ``add_milestones``: milestone dicts in the same shape the profile uses
    """
    new = copy.deepcopy(profile)

    for key, cast in SCALAR_FIELDS.items():
        if changes.get(key) is not None:
            new[key] = cast(changes[key])

    multiplier = changes.get("income_multiplier")
    growth = changes.get("income_growth_percent")
    for source in new.get("income", []):
        if multiplier is not None:
            for field in ("amount", "rent_per_unit", "average_take_home_per_gig", "sales_target"):
                if field in source:
                    source[field] = source[field] * float(multiplier)
        if growth is not None and source.get("income_type") in ("salary/hourly", "bonus"):
            source["has_growth"] = True
            source["growth_type"] = "percentage"
            source["growth_percentage"] = float(growth)

    budget = new.setdefault("budget_items", [])
    for name, value in (changes.get("budget_changes") or {}).items():
        for item in budget:
            if _matches(item, name):
                item["value"] = float(value)
    removals = changes.get("remove_budget_items") or []
    new["budget_items"] = budget = [b for b in budget if not any(_matches(b, n) for n in removals)]
    for item in changes.get("new_budget_items") or []:
        budget.append({
            "type": "other",
            "name": item["name"],
            "value": float(item["value"]),
            "frequency": item.get("frequency", "monthly"),
            "changes_if_not_working": False,
        })

    allocation = changes.get("allocation")
    if allocation:
        total = sum(float(v) for v in allocation.values())
        if total <= 0:
            raise ValueError("Allocation must include at least one asset class above 0%.")
        for name, key in ALLOCATION_KEYS.items():
            new[key] = 100.0 * float(allocation.get(name, 0)) / total

    if changes.get("add_milestones"):
        new.setdefault("milestones", []).extend(copy.deepcopy(changes["add_milestones"]))

    return new


def retirement_ages(results) -> list[float]:
    """Age at the first month each run stopped working (runs that never got there are skipped)."""
    ages = []
    for df in results:
        retired = ~df["working"].astype(bool)
        if retired.any():
            ages.append(float(df.loc[retired, "age"].iloc[0]))
    return ages


def net_worth_bands(results, percentiles=(10, 50, 90)) -> dict[int, np.ndarray]:
    """Per-month net-worth percentiles across runs."""
    length = min(len(df) for df in results)
    matrix = np.array([df["net_worth"].to_numpy()[:length] for df in results])
    return {p: np.percentile(matrix, p, axis=0) for p in percentiles}


def first_year_snapshot(profile: dict) -> dict:
    """Income, spending, taxes and savings rate over the first simulated year."""
    random_state = random.getstate(), np.random.get_state()
    try:
        user = User(profile)
        for _ in range(12):
            user.step_month()
        months = user.time_series
    finally:
        random.setstate(random_state[0])
        np.random.set_state(random_state[1])
    income = float(months["income"].sum())
    expenses = float(months["expenses"].sum())
    taxes = float(user.yearly_taxes)
    withdrawal = profile.get("withdrawal_rate", 0.04) or 0.04
    fire_number = max(0.0, profile.get("post_retirement_expenses", 0) - profile.get("average_post_retirement_income", 0)) / withdrawal
    return {
        "annual_income": income,
        "annual_expenses": expenses,
        "annual_taxes": taxes,
        "savings_rate": (income - expenses - taxes) / income if income > 0 else 0.0,
        "fire_number": fire_number,
        "starting_net_worth": float(months["net_worth"].iloc[0]),
    }


def summarize(profile: dict, results) -> dict:
    ages = retirement_ages(results)
    finals = [float(df["net_worth"].iloc[-1]) for df in results]
    return {
        "runs": len(results),
        "runs_reaching_fi": len(ages),
        "success_rate": len(ages) / len(results) if results else 0.0,
        "retirement_ages": ages,
        "median_retirement_age": float(np.median(ages)) if ages else None,
        "mean_retirement_age": float(np.mean(ages)) if ages else None,
        "median_final_net_worth": float(np.median(finals)),
        "p10_final_net_worth": float(np.percentile(finals, 10)),
        "p90_final_net_worth": float(np.percentile(finals, 90)),
        **first_year_snapshot(profile),
    }


def run(profile: dict, seed: int | None = None) -> tuple[dict, list]:
    _, _, _, results = run_monte_carlo_simulation(profile, seed=seed)
    return summarize(profile, results), results


def compare(profile: dict, changes: dict, seed: int | None = None) -> dict:
    """Run baseline and scenario on the same seed and return both summaries."""
    seed = random.randrange(2**31) if seed is None else seed
    scenario_profile = apply_changes(profile, changes)
    base_summary, base_results = run(profile, seed=seed)
    new_summary, new_results = run(scenario_profile, seed=seed)
    return {
        "seed": seed,
        "profile": scenario_profile,
        "baseline": base_summary,
        "scenario": new_summary,
        "baseline_results": base_results,
        "scenario_results": new_results,
    }
