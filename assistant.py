"""FIRESight GPT: a Claude-powered chat assistant that can run the simulator.

Claude gets two tools. ``run_simulation`` runs the Monte Carlo model on the
saved profile, and ``scenario_analysis`` runs a what-if (see
``scenarios.apply_changes``) against the same random seed. The assistant
answers with numbers from those runs instead of guessing.

Provider selection (env var or Streamlit secret):

* ``ANTHROPIC_API_KEY`` set -> the Claude API (default)
* ``FIRESIGHT_LLM_PROVIDER=bedrock`` -> Claude on Amazon Bedrock, using the
  normal AWS credential chain and ``FIRESIGHT_AWS_REGION`` (default us-east-1)
* ``FIRESIGHT_MODEL`` overrides the model id
"""
from __future__ import annotations

import json

import scenarios

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_BEDROCK_MODEL = "anthropic.claude-opus-5-5"
MAX_TOOL_ROUNDS = 6

CHANGE_PROPERTIES = {
    "income_multiplier": {"type": "number", "description": "Scale every income source, e.g. 1.1 for a 10% raise, 0.5 for half-time."},
    "income_growth_percent": {"type": "number", "description": "Annual raise for salaries and bonuses, in percent (3 = 3%/yr)."},
    "budget_changes": {"type": "object", "additionalProperties": {"type": "number"},
                       "description": "Map of existing budget item name or type to its new value (same frequency as before)."},
    "new_budget_items": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "value": {"type": "number"},
        "frequency": {"type": "string", "enum": ["weekly", "monthly", "annual"]}},
        "required": ["name", "value", "frequency"]}},
    "remove_budget_items": {"type": "array", "items": {"type": "string"}},
    "allocation": {"type": "object", "additionalProperties": {"type": "number"},
                   "description": "New portfolio mix in percent. Keys: " + ", ".join(scenarios.ALLOCATION_KEYS) + ". Rescaled to 100."},
    "post_retirement_expenses": {"type": "number", "description": "Annual spending in retirement, today's dollars."},
    "average_post_retirement_income": {"type": "number", "description": "Annual non-portfolio income in retirement (pension, part-time work)."},
    "withdrawal_rate": {"type": "number", "description": "Safe withdrawal rate as a fraction, e.g. 0.035."},
    "inflation": {"type": "number", "description": "Annual inflation as a fraction, e.g. 0.03."},
    "expenditure_growth_beyond_inflation": {"type": "number", "description": "Annual lifestyle creep as a fraction."},
    "simulate_years": {"type": "integer"},
    "num_simulations": {"type": "integer"},
    "add_milestones": {"type": "array", "description": (
        "Future events. Each needs an ISO 'date' and exactly one flag set true: "
        "buy_a_house (house_price, down_payment, mortgage_rate as fraction, mortgage_term_years, property_tax_rate as fraction), "
        "major_expense (item_name, total_cost, purchase_type 'cash' or 'finance'; finance also needs down_payment, loan_amount, "
        "interest_rate in percent, loan_term_months), major_windfall (windfall_amount), "
        "change_location (city, moving_cost, expense_adjustment 'Manual adjustment', manual_expense_adjustment multiplier), "
        "family_change (family_change_type: marriage, birth, divorce, death or dependant_adult)."),
        "items": {"type": "object"}},
}

RUN_CHARTS = ["net_worth", "retirement_age_distribution", "budget_breakdown", "investment_allocation"]
SCENARIO_CHARTS = ["net_worth_comparison", "retirement_age_comparison"]

TOOLS = [
    {
        "name": "run_simulation",
        "description": "Run the Monte Carlo FIRE simulation on the user's saved profile. Returns retirement-age and net-worth "
                       "statistics plus first-year income, spending, taxes and savings rate. Optionally show charts to the user.",
        "input_schema": {"type": "object", "properties": {
            "charts": {"type": "array", "items": {"type": "string", "enum": RUN_CHARTS}}}},
    },
    {
        "name": "scenario_analysis",
        "description": "Compare the user's current plan against a modified plan. Both run on the same random markets, so "
                       "differences come from the change. Only include fields that change.",
        "input_schema": {"type": "object", "properties": {
            "changes": {"type": "object", "properties": CHANGE_PROPERTIES, "additionalProperties": False},
            "charts": {"type": "array", "items": {"type": "string", "enum": SCENARIO_CHARTS}}},
            "required": ["changes"]},
    },
]

GUIDELINES = """You are FIRESight GPT, an AI assistant for the FIRESight FIRE (Financial Independence, Retire Early) planning tool. Your role is to provide clear, direct, and extremely concise insights based on the user's financial profile and simulations. Always prioritize brevity and actionable advice.

Guidelines for Interaction:
1. Limit responses to 3-5 short sentences or bullet points and between zero and two charts (typically zero or one).
2. Focus on the most impactful factors affecting the FIRE journey.
3. Provide one clear, actionable recommendation per response.
4. Use percentages and years instead of decimal numbers.
5. Round dollar amounts to the nearest thousand, and convert decimal times in years to months (.5 years -> 6 months).
6. Never quote projected numbers you did not get from run_simulation or scenario_analysis in this conversation.
7. If the user doesn't give enough detail to run a scenario (for example a home purchase with no price), ask for it. When you fill a gap with an assumption (20% down, 30-year term), say so.
8. If the user asks about something the model can't represent, say it can't be adjusted in the current version.
9. When you run a simulation or scenario, say which one and what you changed."""


def system_prompt(profile: dict) -> str:
    return f"{GUIDELINES}\n\nThe user's saved profile (JSON):\n{json.dumps(profile, indent=1, sort_keys=True)}"


def _round(value):
    if isinstance(value, float):
        return round(value, 3) if abs(value) < 10 else round(value)
    if isinstance(value, list):
        return [_round(v) for v in value]
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    return value


def public_summary(summary: dict) -> dict:
    """Summary stats for the model (drops the per-run age list, keeps a few percentiles)."""
    out = {k: v for k, v in summary.items() if k != "retirement_ages"}
    ages = sorted(summary.get("retirement_ages", []))
    if ages:
        out["retirement_age_p10"] = ages[int(0.1 * (len(ages) - 1))]
        out["retirement_age_p90"] = ages[int(0.9 * (len(ages) - 1))]
    return _round(out)


def execute_tool(name: str, tool_input: dict, profile: dict, seed: int | None = None):
    """Run one tool call. Returns (result_text, payload_for_charts, is_error)."""
    try:
        if name == "run_simulation":
            summary, results = scenarios.run(profile, seed=seed)
            return json.dumps(public_summary(summary)), {"kind": "run", "summary": summary, "results": results,
                                                        "charts": tool_input.get("charts", [])}, False
        if name == "scenario_analysis":
            comparison = scenarios.compare(profile, tool_input.get("changes", {}), seed=seed)
            text = json.dumps({"baseline": public_summary(comparison["baseline"]),
                               "scenario": public_summary(comparison["scenario"])})
            return text, {"kind": "scenario", **comparison, "charts": tool_input.get("charts", [])}, False
        return f"Unknown tool: {name}", None, True
    except Exception as e:  # report bad tool input back to the model instead of crashing the chat
        return f"Error: {e}", None, True


def run_turn(create, messages: list, profile: dict, on_tool_result=None, seed: int | None = None) -> str:
    """Drive one user turn to completion.

    ``create(messages=...)`` sends the conversation to Claude and returns the
    response; ``messages`` is extended in place with the assistant turns and
    tool results. ``on_tool_result(payload)`` is called for every successful
    tool run so the UI can draw charts. Returns the final assistant text.
    """
    for _ in range(MAX_TOOL_ROUNDS):
        response = create(messages=messages)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "refusal":
            return "I can't help with that one. Try asking about your plan in a different way."
        if response.stop_reason != "tool_use":
            return "\n".join(b.text for b in response.content if b.type == "text")
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            text, payload, is_error = execute_tool(block.name, block.input, profile, seed=seed)
            if payload is not None and on_tool_result is not None:
                on_tool_result(payload)
            result = {"type": "tool_result", "tool_use_id": block.id, "content": text}
            if is_error:
                result["is_error"] = True
            tool_results.append(result)
        messages.append({"role": "user", "content": tool_results})
    return "That took more steps than expected. Try a narrower question."


def make_create(setting, profile: dict):
    """Build a ``create(messages=...)`` callable for the configured provider."""
    import anthropic

    provider = (setting("FIRESIGHT_LLM_PROVIDER") or "anthropic").lower()
    system = system_prompt(profile)
    if provider == "bedrock":
        client = anthropic.AnthropicBedrockMantle(aws_region=setting("FIRESIGHT_AWS_REGION") or "us-east-1")
        model = setting("FIRESIGHT_MODEL") or DEFAULT_BEDROCK_MODEL

        def create(messages):
            return client.messages.create(model=model, max_tokens=16000, system=system, tools=TOOLS, messages=messages)
        return create

    client = anthropic.Anthropic(api_key=setting("ANTHROPIC_API_KEY"))
    model = setting("FIRESIGHT_MODEL") or DEFAULT_MODEL

    def create(messages):
        # Server-side fallback: if a request is declined, the API retries it on another model.
        return client.beta.messages.create(
            model=model, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
    return create
