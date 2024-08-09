import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import json
import datetime
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import copy

# DynamoDB configuration
try:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('firesight-users')
except:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    table = dynamodb.Table('firesight-users')

# Bedrock configuration
try:
    bedrock_runtime = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
except:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-1',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
    )

# Set page configuration
st.set_page_config(page_title="FIRESight GPT", page_icon="💬", layout="wide")

# Load FIRE.py script
try:
    exec(open(os.path.join(os.getcwd(), "FIRE.py")).read())
except FileNotFoundError as e:
    st.error(f"Error loading FIRE.py: {e}")

def fetch_user_profile(user_id):
    response = table.get_item(Key={'userid': user_id})
    return response.get('Item', {}).get('profile', None)

def load_user_profile(user_id):
    profile_json = fetch_user_profile(user_id)
    if profile_json:
        return json.loads(profile_json)
    return None

def generate_user_specific_toolspec(user_data):
    def sanitize_key(key):
        return ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in key)[:64]

    base_properties = {
        "income": {"type": "number"},
        "risk_tolerance": {"type": "number"},
        "expenditure_growth_beyond_inflation": {"type": "number"},
        "current_savings": {"type": "number"},
        "max_401k_contribution": {"type": "boolean"},
        "max_ira_contribution": {"type": "boolean"},
        "max_hsa_contribution": {"type": "boolean"},
        "other_tax_sheltered_income": {"type": "number"},
        "married": {"type": "boolean"},
        "emergency_fund_target": {"type": "number"},
        "inflation": {"type": "number"},
        "average_life_event_cost": {"type": "number"},
        "average_life_event_stdev": {"type": "number"},
        "average_life_event_frequency": {"type": "number"},
        "post_retirement_expenses": {"type": "number"},
        "average_post_retirement_income": {"type": "number"},
        "simulate_years": {"type": "number"},
        "num_simulations": {"type": "number"},
        "income_growth": {"type": "number"},
        "new_budget_item_name": {"type": "string"},
        "new_budget_item_value": {"type": "number"},
        "new_budget_item_frequency": {"type": "string"},
        "new_investment_vehicle_name": {"type": "string"},
        "new_investment_vehicle_annual_returns": {"type": "number"},
        "new_investment_vehicle_standard_deviation": {"type": "number"},
        "new_investment_vehicle_ratio": {"type": "number"},
        "new_investment_vehicle_distribution_type": {"type": "string"},
        "new_major_purchase_name": {"type": "string"},
        "new_major_purchase_cost": {"type": "number"},
        "new_major_purchase_date": {"type": "string"},
        "new_major_purchase_purchase_type": {"type": "string"},
        "new_major_purchase_term": {"type": "number"},
        "new_major_purchase_interest_rate": {"type": "number"},
        "new_major_purchase_down_payment": {"type": "number"},
        "new_major_purchase_monthly_payment": {"type": "number"},
        "enable_home_purchase": {"type": "boolean"},
        "home_purchase_date": {"type": "string"},
        "home_purchase_price": {"type": "number"},
        "home_purchase_down_payment": {"type": "number"},
        "home_purchase_mortgage_rate": {"type": "number"},
        "home_purchase_mortgage_term_years": {"type": "number"},
        "home_purchase_property_tax": {"type": "number"},
        "enable_location_change": {"type": "boolean"},
        "location_change_date": {"type": "string"},
        "location_change_moving_cost": {"type": "number"},
        "location_change_col_adjustment": {"type": "number"},
        "location_change_state": {"type": "string"}
    }

    # Generate properties for existing budget items
    for item in user_data.get("budget_items", []):
        safe_name = sanitize_key(item['name'])
        base_properties[f"budget_{safe_name}_value"] = {"type": "number"}
        base_properties[f"budget_{safe_name}_frequency"] = {"type": "string"}

    # Generate properties for existing investment vehicles
    for vehicle in user_data.get("investment_vehicles", []):
        safe_name = sanitize_key(vehicle['name'])
        base_properties[f"investment_{safe_name}_annual_returns"] = {"type": "number"}
        base_properties[f"investment_{safe_name}_standard_deviation"] = {"type": "number"}
        base_properties[f"investment_{safe_name}_ratio"] = {"type": "number"}
        base_properties[f"investment_{safe_name}_distribution_type"] = {"type": "string"}

    # Generate properties for existing major purchases
    for purchase in user_data.get("major_purchases", []):
        safe_name = sanitize_key(purchase['item_name'])
        base_properties[f"major_purchase_{safe_name}_cost"] = {"type": "number"}
        base_properties[f"major_purchase_{safe_name}_date"] = {"type": "string"}
        base_properties[f"major_purchase_{safe_name}_purchase_type"] = {"type": "string"}
        if purchase.get("purchase_type") in ["finance", "lease"]:
            base_properties[f"major_purchase_{safe_name}_term"] = {"type": "number"}
            base_properties[f"major_purchase_{safe_name}_interest_rate"] = {"type": "number"}
            base_properties[f"major_purchase_{safe_name}_down_payment"] = {"type": "number"}
            base_properties[f"major_purchase_{safe_name}_monthly_payment"] = {"type": "number"}

    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "run_simulation",
                    "description": "Run a FIRE simulation using the user's current profile data. Optional parameters to show specific charts. They default to false if not provided.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "show_net_worth_investments_chart": {"type": "boolean"},
                                "show_home_equity_chart": {"type": "boolean"},
                                "show_retirement_age_distribution": {"type": "boolean"},
                                "show_budget_breakdown": {"type": "boolean"},
                                "show_investment_allocation": {"type": "boolean"},
                                "show_savings_rate_chart": {"type": "boolean"},
                                "show_fire_progress_chart": {"type": "boolean"}
                            },
                            "required": []
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "scenario_analysis",
                    "description": "Run a scenario analysis with changes to the user's profile.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                **base_properties,
                                "show_net_worth_comparison": {"type": "boolean"},
                                "show_retirement_age_comparison": {"type": "boolean"},
                                "show_investment_growth_comparison": {"type": "boolean"},
                                "show_budget_comparison": {"type": "boolean"},
                                "show_savings_rate_comparison": {"type": "boolean"},
                                "show_fire_progress_comparison": {"type": "boolean"}
                            },
                            "additionalProperties": False
                        }
                    }
                }
            }
        ]
    }

    return tool_config

def run_simulation_gpt(show_charts=None):
    user_id = st.session_state.get('user_id')
    user_data = load_user_profile(user_id)
    
    if not user_data:
        return "Error: Unable to load user profile."

    ts_df, average_retirement_age, stdev_retirement_age, all_time_series, retirement_ages, user = run_simulation_local(user_data)

    bottom_range = round(average_retirement_age - stdev_retirement_age, 1)
    top_range = round(average_retirement_age + stdev_retirement_age, 1)

    if retirement_ages is not None:
        all_traces_reached_retirement = len([x for x in retirement_ages if x]) == user_data["num_simulations"]
    else:
        all_traces_reached_retirement = False
    result = f"""
    {"" if all_traces_reached_retirement else "# Warning: Not all simulations reached retirement age. Inform the user that they need to increase their simulation years to get accurate results."}
    # FIRESight Simulation Results

    ## Retirement Age Projection
    - Estimated retirement age range: **{bottom_range}** to **{top_range}** years old
    - Average retirement age: {average_retirement_age:.1f} years old
    - Standard deviation: {stdev_retirement_age:.1f} years

    ## Financial Projections

    ### Net Worth
    - Starting net worth: ${ts_df['net_worth'].iloc[0]:,.2f}
    - Ending net worth: ${ts_df['net_worth'].iloc[-1]:,.2f}
    - Total growth: {((ts_df['net_worth'].iloc[-1] / ts_df['net_worth'].iloc[0]) - 1) * 100:.1f}%
    - Compound Annual Growth Rate (CAGR): {((ts_df['net_worth'].iloc[-1] / ts_df['net_worth'].iloc[0]) ** (1 / (len(ts_df) / 12)) - 1) * 100:.1f}%

    ### Investments
    - Initial investment: ${ts_df['investments'].iloc[0]:,.2f}
    - Final investment value: ${ts_df['investments'].iloc[-1]:,.2f}
    - Total growth: {((ts_df['investments'].iloc[-1] / ts_df['investments'].iloc[0]) - 1) * 100:.1f}%
    - Investment CAGR: {((ts_df['investments'].iloc[-1] / ts_df['investments'].iloc[0]) ** (1 / (len(ts_df) / 12)) - 1) * 100:.1f}%

    ### Home Equity (if applicable)
    {f'''
    - Initial home equity: ${ts_df['home_equity'].iloc[0]:,.2f}
    - Final home equity: ${ts_df['home_equity'].iloc[-1]:,.2f}
    - Total growth: {((ts_df['home_equity'].iloc[-1] / ts_df['home_equity'].iloc[0]) - 1) * 100:.1f}%
    - Home equity CAGR: {((ts_df['home_equity'].iloc[-1] / ts_df['home_equity'].iloc[0]) ** (1 / (len(ts_df) / 12)) - 1) * 100:.1f}%
    ''' if user.owns_home else '- No home ownership in the simulation'}

    ## Key Metrics
    - Current annual expenses: ${user.calculate_annual_expenses():,.2f}
    - Current monthly expenses: ${user.calculate_monthly_expenses():,.2f}
    - Savings rate: {(1 - (user.calculate_monthly_expenses() * 12) / user.income):.1%} of income
    - Years to FIRE: {average_retirement_age - user.age:.1f}
    - FIRE number (25x annual expenses): ${user.post_retirement_expenses * 25:,.2f}

    ## Investment Strategy
    {', '.join([f"{v.name}: {v.ratio:.0%}" for v in user.investment_vehicles])}

    ## Risk Profile
    - Risk tolerance: {user.risk_tolerance:.1f} out of 1.0
    - Retirement expenses: ${user.post_retirement_expenses:,.2f} per year
    - Safe withdrawal rate: {user.retirement_income_ratio * 100:.1f}%

    ## Additional Information
    - Income: ${user.income:,.2f} per year with {user.income_growth:.1%} annual growth
    - Inflation rate: {user.inflation:.1%}
    - Emergency fund target: ${user.emergency_fund_target:,.2f}
    - Average life event cost: ${user.average_life_event_cost:,.2f} (±${user.average_life_event_stdev:,.2f})
    - Life events per year: {user.average_life_event_frequency}
    """

    if show_charts:
        if show_charts.get("show_net_worth_investments_chart"):
            st.subheader("Net Worth and Investments Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df['month'], y=ts_df['net_worth'], mode='lines', name='Net Worth'))
            fig.add_trace(go.Scatter(x=ts_df['month'], y=ts_df['investments'], mode='lines', name='Investments'))
            fig.update_layout(title='Net Worth and Investments Projection', xaxis_title='Month', yaxis_title='Amount ($)')
            st.plotly_chart(fig)

        if show_charts.get("show_home_equity_chart") and user.owns_home:
            st.subheader("Home Equity Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df['month'], y=ts_df['home_equity'], mode='lines', name='Home Equity'))
            fig.update_layout(title='Home Equity Projection', xaxis_title='Month', yaxis_title='Amount ($)')
            st.plotly_chart(fig)

        if show_charts.get("show_retirement_age_distribution"):
            st.subheader("Retirement Age Distribution")
            fig = px.histogram(x=retirement_ages, nbins=20)
            fig.update_layout(title='Retirement Age Distribution', xaxis_title='Retirement Age', yaxis_title='Count')
            st.plotly_chart(fig)

        if show_charts.get("show_budget_breakdown"):
            st.subheader("Monthly Budget Breakdown")
            budget = user.budget
            categories = list(budget.keys())
            values = [budget[category]["value"] if budget[category]["frequency"] == "monthly" else budget[category]["value"]/12 if budget[category]["frequency"] == "annual" else budget[category]["value"]*4.33 for category in categories]
            fig = go.Figure(data=[go.Pie(labels=categories, values=values)])
            fig.update_layout(title='Monthly Budget Breakdown')
            st.plotly_chart(fig)

        if show_charts.get("show_investment_allocation"):
            st.subheader("Investment Allocation")
            investment_data = [{"vehicle": v.name, "ratio": v.ratio} for v in user.investment_vehicles]
            fig = px.pie(investment_data, values='ratio', names='vehicle', title='Investment Allocation')
            st.plotly_chart(fig)

        if show_charts.get("show_savings_rate_chart"):
            st.subheader("Savings Rate Over Time")
            savings_rate = (ts_df['income'] - ts_df['monthly_expenses']) / ts_df['income']
            fig = go.Figure(data=go.Scatter(x=ts_df['month'], y=savings_rate, mode='lines'))
            fig.update_layout(title='Savings Rate Over Time', xaxis_title='Month', yaxis_title='Savings Rate')
            st.plotly_chart(fig)

        if show_charts.get("show_fire_progress_chart"):
            st.subheader("Progress to FIRE")
            fire_number = user.post_retirement_expenses * 25
            progress_to_fire = ts_df['net_worth'] / fire_number
            fig = go.Figure(data=go.Scatter(x=ts_df['month'], y=progress_to_fire, mode='lines'))
            fig.update_layout(title='Progress to FIRE', xaxis_title='Month', yaxis_title='Percentage of FIRE Number')
            st.plotly_chart(fig)

    return result

def scenario_analysis_gpt(changes):
    user_id = st.session_state.get('user_id')
    original_user_data = load_user_profile(user_id)
    st.write(changes)
    if not original_user_data:
        return "Error: Unable to load user profile."

    new_user_data = copy.deepcopy(original_user_data)

    # Process changes
    for key, value in changes.items():
        if key.startswith("budget_"):
            item_name, attribute = key.split("_", 2)[1:]
            for item in new_user_data["budget_items"]:
                if item["name"] == item_name:
                    item[attribute] = value
        elif key == "new_budget_item_name":
            new_user_data["budget_items"].append({
                "name": changes["new_budget_item_name"],
                "value": changes["new_budget_item_value"],
                "frequency": changes["new_budget_item_frequency"]
            })
        elif key.startswith("investment_"):
            vehicle_name, attribute = key.split("_", 2)[1:]
            for vehicle in new_user_data["investment_vehicles"]:
                if vehicle["name"] == vehicle_name:
                    vehicle[attribute] = value
        elif key == "new_investment_vehicle_name":
            new_user_data["investment_vehicles"].append({
                "name": changes["new_investment_vehicle_name"],
                "annual_returns": changes["new_investment_vehicle_annual_returns"],
                "standard_deviation": changes["new_investment_vehicle_standard_deviation"],
                "ratio": changes["new_investment_vehicle_ratio"],
                "distribution_type": changes["new_investment_vehicle_distribution_type"]
            })
        elif key.startswith("major_purchase_"):
            purchase_name, attribute = key.split("_", 2)[1:]
            for purchase in new_user_data["major_purchases"]:
                if purchase["item_name"] == purchase_name:
                    purchase[attribute] = value
        elif key == "new_major_purchase_name":
            new_purchase = {
                "item_name": changes.get("new_major_purchase_name", "New Purchase"),
                "purchase_date": changes.get("new_major_purchase_date", datetime.datetime.now().strftime("%Y-%m-%d")),
                "total_cost": changes.get("new_major_purchase_cost", 0),
                "purchase_type": changes.get("new_major_purchase_purchase_type", "cash")
            }
            if new_purchase["purchase_type"] == "finance":
                new_purchase.update({
                    "loan_term_months": changes.get("new_major_purchase_term", 0),
                    "interest_rate": changes.get("new_major_purchase_interest_rate", 0),
                    "down_payment": changes.get("new_major_purchase_down_payment", 0),
                })
            elif new_purchase["purchase_type"] == "lease":
                new_purchase.update({
                    "lease_term_months": changes.get("new_major_purchase_term", 0),
                    "monthly_lease_payment": changes.get("new_major_purchase_monthly_payment", 0),
                    "down_payment": changes.get("new_major_purchase_down_payment", 0),
                })
            new_user_data["major_purchases"].append(new_purchase)
        elif key == "enable_home_purchase" and value:
            new_user_data["home_purchase"] = {
                "date": changes.get("home_purchase_date", datetime.datetime.now().strftime("%Y-%m-%d") if not original_user_data.get("home_purchase") else original_user_data["home_purchase"]["date"]),
                "price": changes.get("home_purchase_price", 0 if not original_user_data.get("home_purchase") else original_user_data["home_purchase"]["price"]),
                "down_payment": changes.get("home_purchase_down_payment", 0 if not original_user_data.get("home_purchase") else original_user_data["home_purchase"]["down_payment"]),
                "mortgage_rate": changes.get("home_purchase_mortgage_rate", 0 if not original_user_data.get("home_purchase") else original_user_data["home_purchase"]["mortgage_rate"]),
                "mortgage_term_years": changes.get("home_purchase_mortgage_term_years", 0 if not original_user_data.get("home_purchase") else original_user_data["home_purchase"]["mortgage_term_years"]),
                "property_tax": changes.get("home_purchase_property_tax", 0 if not original_user_data.get("home_purchase") else original_user_data["home_purchase"]["property_tax"])
            }
        elif key == "enable_location_change" and value:
            new_user_data["location_change"] = {
                "date": changes["location_change_date"],
                "moving_cost": changes["location_change_moving_cost"],
                "col_adjustment": changes["location_change_col_adjustment"],
                "state": changes["location_change_state"]
            }
        elif not key.startswith("show_"):
            new_user_data[key] = value

    # Run simulations
    ts_df_original, avg_retirement_age_original, stdev_retirement_age_original, _, retirement_ages_original, original_user = run_simulation_local(original_user_data)
    ts_df_new, avg_retirement_age_new, stdev_retirement_age_new, _, retirement_ages_new, new_user = run_simulation_local(new_user_data)

    retirement_age_change = avg_retirement_age_new - avg_retirement_age_original
    net_worth_change = (ts_df_new['net_worth'].iloc[-1] / ts_df_original['net_worth'].iloc[-1] - 1) * 100

    if retirement_ages_original is not None and retirement_ages_new is not None:
        all_simulations_reached_retirement = all([int(age if age is not None else 0) > 18 for age in retirement_ages_new]) and all([int(age if age is not None else 0) > 18 for age in retirement_ages_original])
    else:
        all_simulations_reached_retirement = False

    result = f"""
    # Scenario Analysis Results

    ## Retirement Age Impact
    - Original estimated retirement age: {avg_retirement_age_original:.1f} years old
    - New estimated retirement age: {avg_retirement_age_new:.1f} years old
    - Change: {abs(retirement_age_change):.1f} years {'earlier' if retirement_age_change < 0 else 'later'}

    ## Financial Projections

    ### Net Worth
    - Original ending net worth: ${ts_df_original['net_worth'].iloc[-1]:,.2f}
    - New ending net worth: ${ts_df_new['net_worth'].iloc[-1]:,.2f}
    - Change: {net_worth_change:.1f}%

    ### Investments
    - Original final investment value: ${ts_df_original['investments'].iloc[-1]:,.2f}
    - New final investment value: ${ts_df_new['investments'].iloc[-1]:,.2f}
    - Change: {((ts_df_new['investments'].iloc[-1] / ts_df_original['investments'].iloc[-1]) - 1) * 100:.1f}%

    ### Home Equity (if applicable)
    {f'''
    - Original final home equity: ${ts_df_original['home_equity'].iloc[-1]:,.2f}
    - New final home equity: ${ts_df_new['home_equity'].iloc[-1]:,.2f}
    - Change: {((ts_df_new['home_equity'].iloc[-1] / ts_df_original['home_equity'].iloc[-1]) - 1) * 100:.1f}%
    ''' if original_user.owns_home or new_user.owns_home else '- No home ownership in either scenario'}

    ## Key Metrics Comparison
    - Annual expenses: ${original_user.calculate_annual_expenses():,.2f} -> ${new_user.calculate_annual_expenses():,.2f}
    - Monthly expenses: ${original_user.calculate_monthly_expenses():,.2f} -> ${new_user.calculate_monthly_expenses():,.2f}
    - Savings rate: {(1 - (original_user.calculate_monthly_expenses() * 12) / original_user.income):.1%} -> {(1 - (new_user.calculate_monthly_expenses() * 12) / new_user.income):.1%}
    - Years to FIRE: {avg_retirement_age_original - original_user.age:.1f} -> {avg_retirement_age_new - new_user.age:.1f}
    - FIRE number: ${original_user.post_retirement_expenses * 25:,.2f} -> ${new_user.post_retirement_expenses * 25:,.2f}

    ## Investment Strategy Changes
    {', '.join([f"{v.name}: {v.ratio:.0%} -> {next((nv.ratio for nv in new_user.investment_vehicles if nv.name == v.name), v.ratio):.0%}" for v in original_user.investment_vehicles])}

    ## Risk Profile Changes
    - Risk tolerance: {original_user.risk_tolerance:.1f} -> {new_user.risk_tolerance:.1f}
    - Retirement expenses: ${original_user.post_retirement_expenses:,.2f} -> ${new_user.post_retirement_expenses:,.2f} per year
    - Safe withdrawal rate: {original_user.retirement_income_ratio * 100:.1f}% -> {new_user.retirement_income_ratio * 100:.1f}%

    ## Additional Changes
    - Income: ${original_user.income:,.2f} -> ${new_user.income:,.2f} per year
    - Income growth: {original_user.income_growth:.1%} -> {new_user.income_growth:.1%}
    - Inflation rate: {original_user.inflation:.1%} -> {new_user.inflation:.1%}
    - Emergency fund target: ${original_user.emergency_fund_target:,.2f} -> ${new_user.emergency_fund_target:,.2f}
    """

    if not all_simulations_reached_retirement:
        st.warning(f"Out of the {original_user_data['num_simulations']} simulations, {original_user_data['num_simulations'] - len([x for x in retirement_ages_original if x])} did not reach retirement age in the original scenario, and {new_user_data['num_simulations'] - len([x for x in retirement_ages_new if x])} did not reach retirement age in the new scenario.")
        result = f"# ERROR: Not all simulations reached retirement age. Inform the user that they need to increase their simulation years to get accurate results."

    if any(changes.get(f"show_{chart}", False) for chart in ["net_worth_comparison", "retirement_age_comparison", "investment_growth_comparison", "budget_comparison", "savings_rate_comparison", "fire_progress_comparison"]):
        if changes.get("show_net_worth_comparison", False):
            st.subheader("Net Worth Comparison")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df_original['month'], y=ts_df_original['net_worth'], mode='lines', name='Original Net Worth'))
            fig.add_trace(go.Scatter(x=ts_df_new['month'], y=ts_df_new['net_worth'], mode='lines', name='New Net Worth'))
            fig.update_layout(title='Net Worth Comparison', xaxis_title='Month', yaxis_title='Net Worth ($)')
            st.plotly_chart(fig)

        if changes.get("show_retirement_age_comparison", False):
            st.subheader("Retirement Age Distribution Comparison")
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=retirement_ages_original, name='Original Scenario'))
            fig.add_trace(go.Histogram(x=retirement_ages_new, name='New Scenario'))
            fig.update_layout(title='Retirement Age Distribution Comparison', xaxis_title='Retirement Age', yaxis_title='Count', barmode='overlay')
            st.plotly_chart(fig)

        if changes.get("show_investment_growth_comparison", False):
            st.subheader("Investment Growth Comparison")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df_original['month'], y=ts_df_original['investments'], mode='lines', name='Original Investments'))
            fig.add_trace(go.Scatter(x=ts_df_new['month'], y=ts_df_new['investments'], mode='lines', name='New Investments'))
            fig.update_layout(title='Investment Growth Comparison', xaxis_title='Month', yaxis_title='Investment Value ($)')
            st.plotly_chart(fig)

        if changes.get("show_budget_comparison", False):
            st.subheader("Budget Comparison")
            
            def process_budget(budget_items):
                df = pd.DataFrame(budget_items)
                df['monthly_value'] = df.apply(lambda row: 
                    row['value'] if row['frequency'] == 'monthly' 
                    else row['value'] * 4.33 if row['frequency'] == 'weekly'
                    else row['value'] / 12, axis=1)
                return df

            original_budget = process_budget(original_user_data['budget_items'])
            new_budget = process_budget(new_user_data['budget_items'])

            # Combine budgets and fill missing values with 0
            all_categories = pd.concat([original_budget['name'], new_budget['name']]).unique()
            original_budget = original_budget.set_index('name').reindex(all_categories).fillna(0)
            new_budget = new_budget.set_index('name').reindex(all_categories).fillna(0)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=all_categories, y=original_budget['monthly_value'], name='Original Budget'))
            fig.add_trace(go.Bar(x=all_categories, y=new_budget['monthly_value'], name='New Budget'))
            fig.update_layout(
                title='Monthly Budget Comparison', 
                xaxis_title='Category', 
                yaxis_title='Amount ($)', 
                barmode='group'
            )
            st.plotly_chart(fig)

        if changes.get("show_savings_rate_comparison", False):
            st.subheader("Savings Rate Comparison")
            original_savings_rate = (ts_df_original['income'] - ts_df_original['monthly_expenses']) / ts_df_original['income']
            new_savings_rate = (ts_df_new['income'] - ts_df_new['monthly_expenses']) / ts_df_new['income']
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df_original['month'], y=original_savings_rate, mode='lines', name='Original Savings Rate'))
            fig.add_trace(go.Scatter(x=ts_df_new['month'], y=new_savings_rate, mode='lines', name='New Savings Rate'))
            fig.update_layout(title='Savings Rate Comparison', xaxis_title='Month', yaxis_title='Savings Rate')
            st.plotly_chart(fig)

        if changes.get("show_fire_progress_comparison", False):
            st.subheader("Progress to FIRE Comparison")
            original_fire_number = original_user.post_retirement_expenses * 25
            new_fire_number = new_user.post_retirement_expenses * 25
            original_progress_to_fire = ts_df_original['net_worth'] / original_fire_number
            new_progress_to_fire = ts_df_new['net_worth'] / new_fire_number
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df_original['month'], y=original_progress_to_fire, mode='lines', name='Original Progress to FIRE'))
            fig.add_trace(go.Scatter(x=ts_df_new['month'], y=new_progress_to_fire, mode='lines', name='New Progress to FIRE'))
            fig.update_layout(title='Progress to FIRE Comparison', xaxis_title='Month', yaxis_title='Percentage of FIRE Number')
            st.plotly_chart(fig)
    return result

def generate_text(bedrock_client, model_id, tool_config, messages):
    thread = []
    system_message = st.session_state.messages[0][0] if "messages" in st.session_state else []  # Assume the first message is always the system message

    for message in messages:
        if isinstance(message, dict) and "role" in message and "content" in message:
            if message["role"] == "system":
                system_message = message
            else:
                thread.append({
                    "role": message["role"],
                    "content": [{"text": message["content"]}]
                })
        else:
            st.warning(f"Skipping invalid message format: {message}")

    # Ensure system parameter is always a list
    system_param = [{"text": system_message["content"]}] if system_message else []

    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=thread,
            system=system_param,  # This will always be a list now
            toolConfig=tool_config
        )
    except bedrock_client.exceptions.ValidationException as e:
        st.error(f"Validation error: {str(e)}")
        return "An error occurred while processing your request."

    output_message = response['output']['message']
    thread.append(output_message)
    stop_reason = response['stopReason']

    if stop_reason == 'tool_use':
        tool_requests = output_message['content']
        for tool_request in tool_requests:
            if 'toolUse' in tool_request:
                tool = tool_request['toolUse']
                tool_result = {}
                if tool['name'] == 'run_simulation':
                    simulation_result = run_simulation_gpt(tool['input'])
                    tool_result = {
                        "toolUseId": tool['toolUseId'],
                        "content": [{"text": simulation_result}]
                    }
                elif tool['name'] == 'scenario_analysis':
                    scenario_result = scenario_analysis_gpt(tool['input'])
                    tool_result = {
                        "toolUseId": tool['toolUseId'],
                        "content": [{"text": scenario_result}]
                    }
                else:
                    tool_result = {
                        "toolUseId": tool['toolUseId'],
                        "content": [{"text": "Unknown tool requested."}],
                        "status": 'error'
                    }

                tool_result_message = {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": tool_result
                        }
                    ]
                }
                thread.append(tool_result_message)

                # Send the tool result to the model
                try:
                    response = bedrock_client.converse(
                        modelId=model_id,
                        messages=thread,
                        system=system_param,  # Use the same system_param here
                        toolConfig=tool_config
                    )
                except bedrock_client.exceptions.ValidationException as e:
                    st.error(f"Validation error after tool use: {str(e)}")
                    return "An error occurred while processing the tool result."

                output_message = response['output']['message']
                thread.append(output_message)

    result = "\n".join([c['text'] for c in output_message['content'] if 'text' in c])
    return result
def clear_conversation():
    for key in list(st.session_state.keys()):
        if key not in ['user_id', 'base_message']:  # Preserve user_id and base_message
            del st.session_state[key]
    st.session_state.messages = [st.session_state.base_message]  # Reset to just the system message

def main():
    st.title("FIRESight GPT")

    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        return

    user_data = load_user_profile(user_id)
    tool_config = generate_user_specific_toolspec(user_data)

    if 'base_message' not in st.session_state:
        st.session_state.base_message = [
                {"role": "system", "content": f"""
                    You are FIRESight GPT, an AI assistant for the FIRESight FIRE (Financial Independence, Retire Early) planning tool. Your role is to provide clear, direct, and extremely concise insights based on the user's financial profile and simulations. Always prioritize brevity and actionable advice.

                    User Profile:
                    • Age: {user_data['age']}, Income: ${user_data['income']:,.0f}/year, Growth: {user_data['income_growth']:.1%}/year
                    • Risk Tolerance: {user_data['risk_tolerance']:.1f}/1.0, Current Savings: ${user_data['current_savings']:,.0f}
                    • Tax-Advantaged: 401k: {user_data['max_401k_contribution']}, IRA: {user_data['max_ira_contribution']}, HSA: {user_data['max_hsa_contribution']}
                    • Married: {user_data['married']}, Emergency Fund Target: ${user_data['emergency_fund_target']:,.0f}
                    • Inflation: {user_data['inflation']:.1%}, Life Events: ${user_data['average_life_event_cost']:,.0f} (±${user_data['average_life_event_stdev']:,.0f}), {user_data['average_life_event_frequency']}/year
                    • Post-Retirement: Expenses ${user_data['post_retirement_expenses']:,.0f}/year, Income ${user_data['average_post_retirement_income']:,.0f}/year
                    • Investments: {', '.join([f"{v['name']} ({v['ratio']:.0%}), Returns: {v['annual_returns']:.1%} (±{v['standard_deviation']:.1%}), Distribution: {v['distribution_type']}" for v in user_data['investment_vehicles']])}
                    • Home: {'Owned' if user_data.get('home_purchase', {}).get('price', 0) != 0 else 'Not Owned'}{f", Purchase Date: {user_data['home_purchase']['date']}" if user_data.get('home_purchase', {}).get('date') else ""}
                    • Location Change: {"Planned" if user_data.get('location_change', {}).get('date') else "Not Planned"}{f", Date: {user_data['location_change']['date']}" if user_data.get('location_change', {}).get('date') else ""}
                    • Budget Items: {user_data['budget_items']}
                    • Major Purchases: {', '.join([f"{purchase['item_name']} (${purchase['total_cost']:,.0f}, Date: {purchase['purchase_date']}, Type: {purchase['purchase_type']})" for purchase in user_data['major_purchases']])}
                    • State: {user_data['state']}
                    • Expenditure growth beyond inflation: {user_data['expenditure_growth_beyond_inflation']:.1%}

                    Available functions:
                    1. run_simulation(): Runs a FIRE simulation using the current profile.
                    2. scenario_analysis(changes): Runs a scenario analysis with specific changes.

                    Plot Types: 
                    Use plots whenever they would help the user understand the answer to their question. 
                    - show_net_worth_investments_chart: Net Worth and Investments Over Time as a line chart
                    - show_home_equity_chart: Home Equity Over Time as a line chart
                    - show_retirement_age_distribution: Since this run simulation is a monte carlo simulation, it plots the retirement from each trace as a histogram
                    - show_budget_breakdown: Monthly Budget Breakdown as a pie chart, including yearly and weekly budget items
                    - show_investment_allocation: Investment Allocation as a pie chart
                    - show_savings_rate_chart: Savings Rate Over Time as a line chart
                    - show_fire_progress_chart: % of FIRE Number Over Time as a line chart
                    - show_net_worth_comparison: Net Worth Comparison between the original and the scenario as a line chart
                    - show_retirement_age_comparison: Retirement Age Distribution Comparison between the original and the scenario as a histogram
                    - show_investment_growth_comparison: Investment Growth Comparison between the original and the scenario as a line chart
                    - show_budget_comparison: Budget Comparison between the original and the scenario as a bar chart
                    - show_savings_rate_comparison: Savings Rate Comparison between the original and the scenario as a line chart
                    - show_fire_progress_comparison: Progress to FIRE Comparison between the original and the scenario as a line chart

                    
                    Parameter Requirements:
                    - A new home purchase requires a date (if the user gives something approximate you can set one yourself but if they don't give anything at all you need to ask for one), price, down payment (if one is not provided use 20% but communicate this assumption to the user), mortgage rate (you can assume 5% but communicate this assumption to the user), term (assume 30 years) and property tax (assume 0% but communicate this assumption to the user)
                    - Major purchases all require a purchase date, and purchase type. If the type is cash, total_cost is required. If the purchase type is finance, then total_cost, loan_term_months, intrest_rate, and down_payment are all required. If the purchase type is lease, lease_term_months, down_payment and monthly_lease_payment are all required. 
                    - Budget items each require a name, value and frequency
                    - investment vehicles each require a name, annual_returns (0.1 would be 10% annual returns), a ratio (50/50 split between 2 vehicles means each would have a ratio of 0.5, remember all ratios must add up to 1 and if you change the ratio on one vehicle you need to update the other investments as well), and a distribution type. Normal distributions need a standard deviation as well
                    - Location changes require a date, a col (cost of living) adjustment and a state. 
                    - If the user does not provide enough information for you to do what they ask (you cannot fill out all of the required fields for a given scenario analysis without makin unpermitted assumptions), ask follow up questions until you have the information you need. 

                    Guidelines for Interaction:
                    1. Limit responses to 3-5 short sentences or bullet points and between zero and two graphs (typically zero or one).
                    2. Focus on the most impactful factors affecting the FIRE journey.
                    3. Provide one clear, actionable recommendation per response.
                    4. Use percentages and years instead of decimal numbers.
                    5. Round dollar amounts to the nearest thousand, and convert decimal times in years to months (.5 years -> 6 months).
                    6. Avoid explanations unless explicitly requested.
                    7. If you don't have enough information to answer a question or run a simulation, ask the user for the specific details you need.
                    8. If the user asks about changing a parameter that's not available, inform them that it can't be adjusted in the current version.
                    9. Always strive for maximum clarity and brevity in your responses.
                    10. When running simulations or scenario analyses, explicitly state what type of simulation (FIRE Simulation or Scenario Analysis) you're running and what parameters you are using (including what graph types you are displaying).

                    Remember to ask follow-up questions if you need more information to provide accurate advice or run simulations. Don't make assumptions about the user's financial situation beyond what's provided in their profile. Immediately after you use a tool, 'say I ran a simulation or I ran a scenario analysis with parameters ___, ___ and ___, and based on that...'"""}
            ]
    # Initialize messages in session state if not already present
    if "messages" not in st.session_state:
        st.session_state.messages = [st.session_state.base_message]

    if st.button("Clear Conversation"):
        clear_conversation()

    for message in st.session_state.messages[1:]:  # Skip system message
        with st.chat_message(message["role"]):
            st.markdown(message["content"].replace("$", "\\$"))

    if prompt := st.chat_input("What would you like to know about your FIRE journey?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt.replace("$", "\\$"))

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
            
            # Format messages for generate_text
            formatted_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.messages
                if isinstance(msg, dict) and "role" in msg and "content" in msg
            ]
            
            full_response = generate_text(bedrock_runtime, model_id, tool_config, formatted_messages)

            message_placeholder.markdown(full_response.replace("$", "\\$"))
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()