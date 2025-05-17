import streamlit as st
import datetime
import json
import copy
import re
import base64
import io
import requests
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------
#  1. DYNAMODB AND HELPER: LOAD USER PROFILE
# ------------------------------------------------------------------
import boto3
from boto3.dynamodb.conditions import Key

def initialize_dynamodb():
    """Initialize the DynamoDB resource and table."""
    # Adjust credentials as needed for your environment:
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        table = dynamodb.Table('firesight-users')
    except:
        AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
        AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
        dynamodb = boto3.resource(
            'dynamodb',
            region_name='us-east-2',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        table = dynamodb.Table('firesight-users')
    return table

table = initialize_dynamodb()

def fetch_user_profile(user_id):
    """Fetch the user's JSON profile from DynamoDB."""
    try:
        response = table.get_item(Key={'userid': user_id})
        return response.get('Item', {}).get('profile', None)
    except Exception as e:
        return None

def load_user_profile(user_id):
    """Return user profile as Python dict, or None if not found/parse error."""
    raw_json = fetch_user_profile(user_id)
    if raw_json:
        try:
            return json.loads(raw_json)
        except:
            return None
    return None

# Optional: to update user profile in DB
def save_user_profile(user_id, profile_dict):
    try:
        table.update_item(
            Key={'userid': user_id},
            UpdateExpression="SET #p = :val",
            ExpressionAttributeNames={"#p": "profile"},
            ExpressionAttributeValues={":val": json.dumps(profile_dict)}
        )
    except:
        pass

# ------------------------------------------------------------------
#  2. DESCRIBE THE FULL USER OBJECT AND SUB-CLASSES
# ------------------------------------------------------------------
"""
==================================================================
FULL DOCUMENTATION: FIRE.py CLASSES
==================================================================
The 'User' object in FIRE.py has many fields and methods. Here is
the comprehensive breakdown. This is precisely what we want to give
DeepSeek so it can manipulate everything or write about it knowledgeably.

Classes:

1. User:
   - Fields:
     > age (int or float): The user's current age in years, can be fractional
     > state (str): The user's home state, e.g. 'California'
     > married (bool): Whether the user is married
     > spouse_age (float): If married, spouse's age
     > dependents (int): Number of dependents
     > simulate_years (int): How many years the simulation should run
     > num_simulations (int): How many Monte Carlo runs to do
     > inflation (float): The base inflation rate, e.g. 0.03
     > expenditure_growth_beyond_inflation (float): Additional real growth
                                                    in expenses
     > income_sources (List[IncomeSource]): Various incomes
     > budget_items (List[BudgetItem]): Recurring expenses
     > assets_and_debts (List[AssetOrDebt]): Checking, savings, credit, loans
     > cash (float): The user's immediate liquid cash
     > investment_balance (float): The total in investments (stocks, etc.)
     > investment_allocations (dict): { 'Index Funds': 20, 'Bonds': 10, ...}
     > investment_vehicles (List[InvestmentVehicle]): The sub-objects that
                                                      handle monthly returns
     > vehicle_balances (dict): The actual amounts allocated to each vehicle
     > milestones (List[Milestone]): Future events (buy house, job change, etc.)
     > retirement_goal_method (str): 'Safe Withdrawal Rate', 'Simulate Additional Years with Reduced Income', or 'Fixed Value'
     > post_retirement_expenses (float): Expected annual expenses after retirement
     > average_post_retirement_income (float): Some fixed expected income post retirement
     > withdrawal_rate (float): If using 'Safe Withdrawal Rate', e.g. 0.04
     > fixed_retirement_goal (float): If using 'Fixed Value', e.g. 3_000_000
     > remove_income_sources (dict): For the scenario of 'Simulate Additional Years with Reduced Income', which incomes to remove or zero
     > additional_retirement_income (float): If that scenario is used
     > additional_simulation_years (int): If that scenario is used
     > emergency_fund_target (float): The user wants some buffer
     > location (dict): { 'city': '', 'country': '' }
     > home (Home): If user purchased a home
     > func (str): Arbitrary code snippet. If set, each month the
                   simulation tries something like `try: exec(self.func)`

   - Methods:
     * load_user_data(self, data: dict):
         ~ Populates the user from data
     * calculate_monthly_income(), calculate_monthly_expenses()
     * calculate_federal_tax(), calculate_state_tax()
     * calculate_taxes(income)
     * handle_milestones()
       ...
     * step_month(): The main monthly update loop. If self.func is set,
       it does: try: exec(self.func)
     * run_simulation(): Repeatedly calls step_month()

2. IncomeSource:
   - Fields: 'income_type' (e.g. 'salary/hourly', 'bonus', 'stock_options', etc.),
     'amount', 'frequency', 'overtime_eligible', 'stock_options_type', etc.
   - Method: get_monthly_income(current_date, user_age) -> float
   - ... plus many scenario-specific fields.

3. BudgetItem:
   - Fields: 'type' (like 'rent', 'utilities'), 'name', 'value', 'frequency',
     'changes_if_not_working' (bool), 'value_if_not_working'
   - Method: get_monthly_expense(working=True)

4. AssetOrDebt:
   - Fields: 'type' (like 'Checking Account', 'Credit Card Debt'),
     'name', 'value', 'remaining_term', 'interest_rate', 'monthly_payment'
   - Method: update() -> how it changes monthly

5. Home:
   - Fields: purchase_date, purchase_price, down_payment, mortgage_rate,
             mortgage_term_years, property_tax_rate, hoa, loan_balance,
             home_value, etc.
   - Method: make_payment(date), etc.

6. InvestmentVehicle:
   - Wraps a ReturnGenerator that seeds monthly returns for e.g. 'Index Funds'.
   - Fields: name ('Index Funds'), ratio (the allocation ratio), real_estate_investment_type,
             total_months, current_month_idx, return_gen
   - Method: get_monthly_return()

7. Milestone:
   - Fields: date, buy_a_house, change_location, major_expense, change_income,
             major_windfall, family_change, data (dict w/ details)

8. ReturnGenerator:
   - Manages generating monthly returns, block bootstrap from CSV data, or Markov
   - We skip repeating all detail here, but it yields monthly returns for the
     relevant asset.

In short, the 'User' object has many sub-objects. The simulation runs for
`simulate_years * 12` months. Each month, the user calls `step_month()`,
which:

1) handle_milestones() if it's the correct date
2) calculate monthly income, expenses
3) pay them, update net worth
4) if `func` is set, do `exec(self.func)`

Hence, we can inject custom scenario logic in 'func' if needed.

==================================================================
"""


# ------------------------------------------------------------------
#  3. RUN SIMULATIONS & GENERATE PLOTS (Without placeholders!)
# ------------------------------------------------------------------
from FIRE import run_monte_carlo_simulation

def generate_networth_chart(avg_ts: pd.DataFrame) -> str:
    """
    Create an interactive net-worth line chart (Plotly),
    then encode as base64 PNG for embedding in final JSON.
    Returns a data URI or the raw base64 string.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=avg_ts["month"], y=avg_ts["net_worth"],
        mode='lines', name='Average Net Worth'
    ))
    fig.update_layout(
        title="Net Worth Over Time",
        xaxis_title="Month",
        yaxis_title="Net Worth"
    )
    # Convert to image
    png_bytes = fig.to_image(format="png")
    b64_str = base64.b64encode(png_bytes).decode("utf-8")
    return b64_str

def generate_final_networth_hist(final_values: list) -> str:
    """
    Create a histogram of final net worth from the multiple runs,
    then base64-encode as PNG.
    """
    fig = px.histogram(final_values, nbins=25, labels={'value': 'Final Net Worth'})
    fig.update_layout(
        title="Distribution of Final Net Worth"
    )
    png_bytes = fig.to_image(format="png")
    b64_str = base64.b64encode(png_bytes).decode("utf-8")
    return b64_str

# ------------------------------------------------------------------
#  4. PERPLEXITY & DEEPSEEK FUNCTION-CALLING (RAW, NO LANGCHAIN)
# ------------------------------------------------------------------
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"
DEEPSEEK_API_BASE = "https://api.deepseek.com"
PERPLEXITY_API_KEY = "YOUR_PERPLEXITY_API_KEY"

def call_deepseek_function(function_name: str, args_obj: dict, system_prompt: str, user_prompt: str) -> dict:
    """
    Demonstration of a raw function calling approach with DeepSeek.
    We specify a single function in 'tools' or we do a larger message specifying the function schema.
    Because the user wants enforced JSON function calling, we do:
      messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
      ]
      'tools' = [
         {
           'type': 'function',
           'function': {
               'name': function_name,
               'parameters': {... Pydantic schema ...},
               'description': ...
           }
         }
      ]
    Then we parse the model's tool_calls -> function_name + arguments.
    This is a skeleton. In production you'd handle edge cases, loop, etc.
    """
    # Pseudocode. The real call depends on your environment.
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",  # or "deepseek-reasoner"
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": function_name,
                    "description": "enforced JSON function call for scenario usage",
                    "parameters": {
                        "type": "object",
                        "properties": args_obj,  # define your schema
                        "required": list(args_obj.keys())
                    }
                }
            }
        ]
    }
    url = f"{DEEPSEEK_API_BASE}/chat/completions"
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 200:
        return {"error": resp.text}

    # The model is expected to produce a function call in JSON
    out = resp.json()
    # The function call is typically in out['choices'][0]['message']['tool_calls'] or so
    # We'll do a naive parse:
    if "choices" not in out:
        return {"error": "no choices in response", "raw": out}
    choice = out["choices"][0]
    msg = choice.get("message", {})
    tool_calls = msg.get("tool_calls", [])
    if not tool_calls:
        return {"error": "no function calls made", "raw": out}
    # We'll assume it only made one call
    fc = tool_calls[0]
    # fc["arguments"] is presumably a dict
    return fc.get("arguments", {})

def call_perplexity_subquestions(questions: list[str]) -> list[str]:
    """
    We do not show these responses to the user. 
    Return them for the final report generation step.
    """
    answers = []
    for q in questions:
        if not q.strip():
            answers.append("")
            continue
        data = {
            "model": "sonar-reasoning",
            "messages": [{"role": "user", "content": q}],
            "stream": False
        }
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        url = "https://api.perplexity.ai/chat/completions"
        r = requests.post(url, headers=headers, json=data)
        if r.status_code == 200:
            js = r.json()
            ans = js["choices"][0]["message"]["content"]
            answers.append(ans)
        else:
            answers.append(f"Error {r.status_code}")
    return answers

# ------------------------------------------------------------------
#  5. MAIN STREAMLIT PAGE
# ------------------------------------------------------------------
st.set_page_config(page_title="What If Analysis", page_icon="🔍")

def main():
    st.title("What If Analysis - Comprehensive Example")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User not logged in.")
        return

    user_profile = load_user_profile(user_id)
    if not user_profile:
        st.error("Could not load user profile.")
        return

    user_prompt = st.text_area("Describe your scenario or question:", height=180)

    # We also let the user optionally specify 3 sub-questions for Perplexity:
    sub1 = st.text_input("Subquestion #1", "")
    sub2 = st.text_input("Subquestion #2", "")
    sub3 = st.text_input("Subquestion #3", "")

    if st.button("Run 'What If'"):
        if not user_prompt.strip():
            st.warning("Please enter a scenario or question.")
            return

        st.info("1) Determining analysis type with DeepSeek function calling...")

        # First function call: classification
        classification_schema = {
            "analysis_type": {
                "type": "string",
                "description": "Either SCENARIO_ANALYSIS, BASELINE_SIMULATION, or UNSURE"
            }
        }
        system_msg = (
            "You are a strict JSON function. The user will describe a scenario or question. "
            "You must classify it as SCENARIO_ANALYSIS, BASELINE_SIMULATION, or UNSURE. "
            "Return { 'analysis_type': '...' } only."
        )
        classify_args = call_deepseek_function(
            function_name="analysis_type_classifier",
            args_obj=classification_schema,
            system_prompt=system_msg,
            user_prompt=user_prompt
        )
        analysis_type = classify_args.get("analysis_type", "UNSURE")

        st.write(f"Analysis type: {analysis_type}")

        # 2) If scenario, we do the parameter setting
        scenario_mode = (analysis_type == "SCENARIO_ANALYSIS")

        if scenario_mode:
            st.info("2) Generating scenario param changes (DeepSeek) ...")
            # We do a second function call that returns:
            #   { "code_needed": "true/false", "param_changes": [ ... ] }
            scenario_schema = {
                "code_needed": {
                    "type": "boolean",
                    "description": "Indicate whether custom monthly code injection is needed"
                },
                "param_changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "param_path": {"type": "string"},
                            "new_value": {"type": "string"}
                        },
                        "required": ["param_path", "new_value"]
                    },
                    "description": "List of param path updates"
                }
            }
            system_scenario_prompt = (
                "You are a JSON-only function that sets scenario parameters. "
                "The user object fields are extensively documented in the system context. "
                "Output must be: { 'code_needed': true/false, 'param_changes': [ {param_path, new_value}, ... ] }."
                "param_path is dot/bracket notation, e.g. budget_items[0].value. new_value is a JSONable string."
            )
            scenario_args = call_deepseek_function(
                function_name="scenario_param_setter",
                args_obj=scenario_schema,
                system_prompt=system_scenario_prompt,
                user_prompt=user_prompt
            )

            code_needed = scenario_args.get("code_needed", False)
            param_changes = scenario_args.get("param_changes", [])

            # 3) If code_needed == true, do a third function call to retrieve the code
            code_injection = ""
            if code_needed:
                st.info("3) Generating custom monthly code snippet (DeepSeek) ...")
                code_schema = {
                    "injected_code": {
                        "type": "string",
                        "description": "A Python snippet that will be exec'd each month in user.step_month()."
                    }
                }
                system_code_prompt = (
                    "You are a JSON-only function returning one field { 'injected_code': '...' }, "
                    "the code that modifies the user object each month. Use the documented fields as needed. "
                    "For example, you can do if user.cash < 1000: user.cash+= 500. Etc."
                )
                code_args = call_deepseek_function(
                    function_name="scenario_code_injection",
                    args_obj=code_schema,
                    system_prompt=system_code_prompt,
                    user_prompt=user_prompt
                )
                code_injection = code_args.get("injected_code", "")

            # Now we have param_changes and optional code_injection
            # We'll apply them to a copy of user_profile
            scenario_data = copy.deepcopy(user_profile)

            for pc in param_changes:
                path = pc.get("param_path", "")
                val_str = pc.get("new_value", "")
                # parse
                try:
                    val_obj = json.loads(val_str)
                except:
                    val_obj = val_str
                path_elems = re.split(r'\.|\[|\]', path)
                path_elems = [p for p in path_elems if p]
                target = scenario_data
                for pe in path_elems[:-1]:
                    if re.match(r'^\d+$', pe):
                        idx = int(pe)
                        if isinstance(target, list) and 0 <= idx < len(target):
                            target = target[idx]
                    else:
                        target = target.get(pe, {})
                last = path_elems[-1]
                if re.match(r'^\d+$', last):
                    idx = int(last)
                    if isinstance(target, list) and 0 <= idx < len(target):
                        target[idx] = val_obj
                else:
                    if isinstance(target, dict):
                        target[last] = val_obj

            if code_injection:
                scenario_data["func"] = code_injection

            # 4) Possibly gather subquestions for Perplexity
            questions = [sub1, sub2, sub3]
            perplexity_answers = call_perplexity_subquestions(questions)
            # We'll keep them hidden from UI, but pass them to the final report builder

            # 5) Run scenario simulation
            st.info("4) Running scenario simulation ...")
            avg_ts, avg_ret_age, std_ret_age, runs = run_monte_carlo_simulation(scenario_data)

            # Build final net worth distribution
            final_nws = []
            for df in runs:
                sorted_df = df.sort_values("month")
                last_m = sorted_df["month"].max()
                val = sorted_df.loc[sorted_df["month"] == last_m, "net_worth"].iloc[-1]
                final_nws.append(val)

            # Generate base64 chart images
            networth_line_b64 = generate_networth_chart(avg_ts)
            dist_b64 = generate_final_networth_hist(final_nws)

            # 6) Build final JSON to pass to DeepSeek for a fully rendered markdown report
            # We'll embed the Perplexity answers as well.
            final_report_data = {
                "analysis_type": "SCENARIO_ANALYSIS",
                "user_prompt": user_prompt,
                "subquestions": questions,
                "perplexity_answers": perplexity_answers,  # not shown to user but used by DeepSeek
                "param_changes": param_changes,
                "code_injection": code_injection,
                "simulation_results": {
                    "average_retirement_age": avg_ret_age,
                    "std_dev_retirement_age": std_ret_age,
                    "final_net_worth_distribution": final_nws
                },
                "networth_time_series_image_b64": networth_line_b64,
                "final_networth_hist_image_b64": dist_b64,
                "scenario_data_used": scenario_data  # so DeepSeek sees the final user config
            }

            # 7) The final UI only shows the final textual output from DeepSeek in Markdown
            # We'll do a final function call to DeepSeek with all this data, asking it
            # to produce a fancy markdown report. We do not show code or subquestion answers
            st.info("5) Generating final report (DeepSeek) ...")
            # We'll define a final "report_generator" function schema:
            final_report_schema = {
                "markdown_report": {
                    "type": "string",
                    "description": "A fully formatted markdown report summarizing the scenario."
                }
            }
            # We'll craft a big system prompt with chain-of-thought instructions, referencing the final_report_data
            # Then we do function calling again
            final_report_system = f"""
You are a specialized function that produces a comprehensive, visually appealing Markdown report.
You have the following data from the user's scenario:

- 'analysis_type': {final_report_data["analysis_type"]}
- 'user_prompt': The scenario question from the user
- 'param_changes': The changes you made to the user object
- 'code_injection': Potential custom monthly code
- 'simulation_results': Stats from the Monte Carlo runs
- 'networth_time_series_image_b64': A base64 PNG of net worth over time
- 'final_networth_hist_image_b64': A base64 PNG of final NW distribution
- 'perplexity_answers': Additional references from Perplexity to incorporate
- 'scenario_data_used': The final user data object

You also know how the 'User' object, 'IncomeSource', 'BudgetItem', 'AssetOrDebt', 'Home', 'InvestmentVehicle', etc. all work,
from the system documentation above.

Please produce a robust Markdown discussion of the scenario's results. The networth charts are encoded as base64,
so you can embed them as an <img> tag or a standard Markdown image. For example:


In your discussion, you can reference how the param changes might have impacted user incomes or expenses,
the final net worth distribution, how the retirement age changed, etc. Use the perplexity answers to
enrich your explanation. Provide a thorough chain-of-thought but do not literally show the chain-of-thought
to the user, just a polished final explanation.

Output as JSON:
{
  "markdown_report": "Actual MD content"
}
"""
            # We'll convert final_report_data to a string to pass in user_prompt
            final_report_user_str = json.dumps(final_report_data)

            final_report_args = call_deepseek_function(
                function_name="report_generator",
                args_obj=final_report_schema,
                system_prompt=final_report_system,
                user_prompt=final_report_user_str
            )

            # We expect final_report_args to contain {"markdown_report": "..."}
            markdown_report = final_report_args.get("markdown_report", "Error: No report generated.")
            st.markdown(markdown_report, unsafe_allow_html=True)

        elif analysis_type == "BASELINE_SIMULATION":
            st.info("Baseline simulation requested...")

            # Possibly do the subquestions to Perplexity here as well
            questions = [sub1, sub2, sub3]
            perplexity_answers = call_perplexity_subquestions(questions)

            # Run baseline
            avg_ts, avg_ret_age, std_ret_age, runs = run_monte_carlo_simulation(user_profile)
            final_nws = []
            for df in runs:
                sorted_df = df.sort_values("month")
                last_m = sorted_df["month"].max()
                val = sorted_df.loc[sorted_df["month"] == last_m, "net_worth"].iloc[-1]
                final_nws.append(val)

            networth_line_b64 = generate_networth_chart(avg_ts)
            dist_b64 = generate_final_networth_hist(final_nws)

            final_report_data = {
                "analysis_type": "BASELINE_SIMULATION",
                "user_prompt": user_prompt,
                "subquestions": questions,
                "perplexity_answers": perplexity_answers,
                "simulation_results": {
                    "average_retirement_age": avg_ret_age,
                    "std_dev_retirement_age": std_ret_age,
                    "final_net_worth_distribution": final_nws
                },
                "networth_time_series_image_b64": networth_line_b64,
                "final_networth_hist_image_b64": dist_b64,
                "scenario_data_used": user_profile
            }

            # Generate final markdown
            final_report_schema = {
                "markdown_report": {
                    "type": "string",
                    "description": "Fully formatted markdown report summarizing the baseline simulation."
                }
            }
            final_report_system = f"""
You are a specialized function that produces a comprehensive, visually appealing Markdown report.
The user did not want a scenario but a baseline simulation.

We have:
- average_retirement_age: {avg_ret_age}
- std_dev_retirement_age: {std_ret_age}
- final net worth distribution
- base64 images for net worth over time and final distribution
- perplexity answers for references

Output JSON:
{{ "markdown_report": "..." }}
"""
            final_report_user_str = json.dumps(final_report_data)

            final_report_args = call_deepseek_function(
                function_name="report_generator",
                args_obj=final_report_schema,
                system_prompt=final_report_system,
                user_prompt=final_report_user_str
            )
            markdown_report = final_report_args.get("markdown_report", "No report generated.")
            st.markdown(markdown_report, unsafe_allow_html=True)

        else:
            st.warning("Analysis type uncertain (UNSURE). Please try clarifying your prompt.")


if __name__ == "__main__":
    main()
