import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import datetime
import json
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px
from st_repeating_field_group import generate_repeating_field_group
import numpy as np

# ======================
#  DYNAMO CONFIG
# ======================
try: 
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('firesight-users')
except:
    # If secrets are needed
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2',
                              aws_access_key_id=AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    table = dynamodb.Table('firesight-users')


# ======================
#  LOAD FIRE.py
# ======================
st.set_page_config(page_title="FIRESight - Scenario Analysis", page_icon="🔍", layout="wide")

try:
    # Execute the new FIRE.py code without modifying it
    exec(open(os.path.join(os.getcwd(), "FIRE.py")).read(), globals())
except FileNotFoundError as e:
    st.error(f"Error loading FIRE.py: {e}")


# ======================
#  HELPER FUNCTIONS
# ======================
def fetch_user_profile(user_id):
    """Loads user's JSON profile from DynamoDB."""
    response = table.get_item(Key={'userid': user_id})
    return response.get('Item', {}).get('profile', None)

def load_user_profile(user_id):
    """Parses JSON into Python dict."""
    profile_json = fetch_user_profile(user_id)
    if profile_json:
        return json.loads(profile_json)
    return None

def format_currency(value):
    """Format numeric as USD."""
    try:
        return f"${value:,.0f}"
    except:
        return str(value)

def format_percentage(value):
    """Format numeric as percentage."""
    try:
        return f"{value:.1%}"
    except:
        return str(value)

def format_time_difference(years, months, days):
    """
    Nicely format a difference in years, months, days (used for
    'accelerate your retirement by...' banner).
    """
    parts = []
    if years > 0:
        parts.append(f":orange[{years}] {'year' if years == 1 else 'years'}")
    if months > 0 or (years > 0 and days > 0):
        parts.append(f":orange[{months}] {'month' if months == 1 else 'months'}")
    if days > 0:
        parts.append(f":orange[{days}] {'day' if days == 1 else 'days'}")

    if len(parts) > 1:
        return f"{', '.join(parts[:-1])} and {parts[-1]}"
    elif len(parts) == 1:
        return parts[0]
    else:
        return "0 days"

def calculate_annual_expenses(user):
    """Helper to approximate annual expenses from final month state."""
    # The new FIRE.py user has calculate_monthly_expenses()
    return user.calculate_monthly_expenses() * 12

def calculate_annual_income(user):
    """
    Helper to approximate annual income from the final month state.
    If the user has retired mid-simulation, it could be lower.
    We'll just do final month's 'monthly_income' * 12.
    """
    return user.calculate_monthly_income() * 12

def attach_user_extras(user, data):
    """
    Attach attributes that scenario-analysis code references, but
    do not natively exist in the new FIRE.py's User class.
    """
    # "income" -> treat as final monthly income * 12
    user.income = calculate_annual_income(user)

    # "risk_tolerance"
    user.risk_tolerance = data.get('risk_tolerance', 0.5)

    # "retirement_income_ratio" -> the scenario code calls it "Safe Withdrawal Rate"
    # We'll map it to user.withdrawal_rate if that was set.
    # If the user used "Safe Withdrawal Rate", user.withdrawal_rate is likely set
    # inside the new code. We'll just read that or fallback to user_data.
    user.retirement_income_ratio = getattr(user, 'withdrawal_rate', data.get('withdrawal_rate', 0.04))

    return user


# ======================
#  LOCAL SIMULATION
# ======================
def run_simulation_local(user_data):
    """
    Re-implements logic similar to run_monte_carlo_simulation from the new FIRE.py,
    but returns additional items the scenario code expects:
      - The average monthly timeseries (avg_ts)
      - average_retirement_age, stdev_retirement_age
      - the full list of results (list of monthly DF)
      - the list of retirement_ages
      - the final user object from the last simulation
    """
    simulations = user_data.get('num_simulations', 100)
    results = []
    retirement_ages = []

    for _ in range(simulations):
        # Create a fresh user for each sim
        user = User(user_data)
        # Attach extra fields like 'income', 'risk_tolerance', 'retirement_income_ratio'
        attach_user_extras(user, user_data)
        user.run_simulation()

        # Collect the monthly time series
        results.append(user.time_series)

        # Collect retirement age if it was set
        if user.retirement_age:
            retirement_ages.append(user.retirement_age)

    # Calculate average/stdev retirement age
    average_retirement_age = np.mean(retirement_ages) if retirement_ages else None
    stdev_retirement_age   = np.std(retirement_ages) if retirement_ages else None

    # Combine all runs into one big DF, then compute average by month
    combined = pd.concat(results, ignore_index=True)
    numeric_cols = combined.select_dtypes(include=[np.number]).columns
    avg_ts = combined.groupby('month', as_index=False)[numeric_cols].mean()

    # "final_user" from the last simulation
    final_user = user

    return avg_ts, average_retirement_age, stdev_retirement_age, results, retirement_ages, final_user


# ======================
#  MAIN SCENARIO APP
# ======================
def main():
    st.title("🔍 Scenario Analysis")
    st.write("Explore how changes to your financial plan could impact your journey to FIRE.")

    # Identify user
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        return

    user_data = load_user_profile(user_id)
    if not user_data:
        st.error("Failed to load user profile.")
        return

    # We make a copy so we can adjust scenario parameters without losing original
    new_user_data = user_data.copy()

    # 1) Safely extract numeric fields, converting list -> float if needed.
    def ensure_float(value, default=0.0):
        """
        Safely convert many possible types (int, float, str, list, dict) to float.
        Returns `default` if conversion fails.
        """
        # 1. Already numeric?
        if isinstance(value, (int, float)):
            return float(value)

        # 2. String -> float
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default

        # 3. List -> take first element and recurse
        if isinstance(value, list):
            if not value:  # empty list
                return default
            return ensure_float(value[0], default=default)

        # 4. Dict -> pick out a known key
        if isinstance(value, dict):
            # Example: if your dict is {"value": 95000.0}, do:
            candidate = value.get("value")
            if candidate is not None:
                return ensure_float(candidate, default=default)
            # or if your dict is {"amount": 95000.0}, switch to .get("amount")
            return default

        # 5. If all else fails
        return default


    # ----- UI: Income and Savings -----
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Income and Savings")
        
        # Fix: ensure float for "income"
        income_val = ensure_float(user_data.get("income", 95000.0), default=95000.0)
        income = st.number_input(
            "Annual Income",
            value=income_val,
            step=1000.0,
            format="%0.2f"
        )
        st.caption("💡 Increasing your income is one of the most impactful ways to accelerate your FIRE journey.")

        # Fix: ensure float for "income_growth"
        income_growth_val = ensure_float(user_data.get("income_growth", 0.03) * 100, default=3.0)
        income_growth = st.slider(
            "Income Growth (%/year)",
            min_value=0.0,
            max_value=10.0,
            value=income_growth_val,
            step=0.1,
            format="%0.1f"
        )
        st.caption("💡 Even small increases in annual income growth can have a significant impact over time.")

        # Fix: ensure float for "current_savings"
        current_savings_val = ensure_float(user_data.get("current_savings", 25000.0), default=25000.0)
        current_savings = st.number_input(
            "Current Savings",
            value=current_savings_val,
            step=1000.0,
            format="%0.2f"
        )

        # Fix: ensure float for "emergency_fund_target"
        eft_val = ensure_float(user_data.get("emergency_fund_target", 10000.0), default=10000.0)
        emergency_fund_target = st.number_input(
            "Emergency Fund Target",
            value=eft_val,
            step=1000.0,
            format="%0.2f"
        )
        st.caption("💡 A robust emergency fund can prevent setbacks in your FIRE journey.")

    with col2:
        st.subheader("Retirement and Risk")

        # Fix: ensure float for "risk_tolerance"
        rt_val = ensure_float(user_data.get("risk_tolerance", 0.5), default=0.5)
        risk_tolerance = st.slider(
            "Risk Tolerance",
            0.0, 1.0,
            value=rt_val,
            step=0.01
        )
        st.caption("💡 Higher risk tolerance allows for more aggressive investment strategies but comes with increased volatility.")

        # Fix: ensure float for "post_retirement_expenses"
        pre_val = ensure_float(user_data.get("post_retirement_expenses", 0.0), default=0.0)
        post_retirement_expenses = st.number_input(
            "Post-Retirement Annual Expenses",
            value=pre_val,
            step=1000.0,
            format="%0.2f"
        )
        st.caption("💡 Lowering your post-retirement expenses can significantly reduce the amount you need to save.")

        # Fix: ensure float for "average_post_retirement_income"
        apri_val = ensure_float(user_data.get("average_post_retirement_income", 0.0), default=0.0)
        average_post_retirement_income = st.number_input(
            "Average Post-Retirement Annual Income",
            value=apri_val,
            step=1000.0,
            format="%0.2f"
        )

        # Fix: ensure float for "inflation"
        inflation_val = ensure_float(user_data.get("inflation", 0.03) * 100, default=3.0)
        inflation = st.slider(
            "Inflation Rate (%/year)",
            min_value=0.0, max_value=10.0,
            value=inflation_val,
            step=0.1,
            format="%0.1f"
        )
        st.caption("💡 Consider how different inflation scenarios might affect your long-term plans.")

    # ----- UI: Tax-Advantaged -----
    st.subheader("Tax-Advantaged Accounts")
    col1, col2, col3 = st.columns(3)
    with col1:
        max_401k_contribution = st.checkbox(
            "Max 401(k) Contribution",
            value=user_data.get("max_401k_contribution", True)
        )
    with col2:
        max_ira_contribution = st.checkbox(
            "Max IRA Contribution",
            value=user_data.get("max_ira_contribution", True)
        )
    with col3:
        max_hsa_contribution = st.checkbox(
            "Max HSA Contribution",
            value=user_data.get("max_hsa_contribution", False)
        )
    st.caption("💡 Maximizing contributions to tax-advantaged accounts can significantly boost your savings rate.")

    # Fix: ensure float for "other_tax_sheltered_income"
    otsi_val = ensure_float(user_data.get("other_tax_sheltered_income", 0.0), default=0.0)
    other_tax_sheltered_income = st.number_input(
        "Other Tax-Sheltered Income",
        value=otsi_val,
        step=1000.0,
        format="%0.2f"
    )

    # ----- UI: Lifestyle -----
    st.subheader("Lifestyle and Expenses")
    col1, col2 = st.columns(2)
    with col1:
        married = st.checkbox(
            "Married",
            value=user_data.get("married", True)
        )
    with col2:
        # Fix: ensure float for "expenditure_growth_beyond_inflation"
        egb_val = ensure_float(user_data.get("expenditure_growth_beyond_inflation", 0.03) * 100, default=3.0)
        expenditure_growth = st.slider(
            "Expense Growth Beyond Inflation (%/year)",
            min_value=0.0, max_value=10.0,
            value=egb_val,
            step=0.1,
            format="%0.1f"
        )
        st.caption("💡 Controlling lifestyle inflation can have a major impact on your savings rate and FIRE timeline.")

    # ----- UI: Life Events -----
    st.subheader("Life Events")
    col1, col2, col3 = st.columns(3)
    with col1:
        alc_val = ensure_float(user_data.get("average_life_event_cost", 1000.0), default=1000.0)
        average_life_event_cost = st.number_input(
            "Average Life Event Cost",
            value=alc_val,
            step=100.0,
            format="%0.2f"
        )
    with col2:
        alcs_val = ensure_float(user_data.get("average_life_event_stdev", 500.0), default=500.0)
        average_life_event_stdev = st.number_input(
            "Life Event Cost Std Dev",
            value=alcs_val,
            step=100.0,
            format="%0.2f"
        )
    with col3:
        alf_val = ensure_float(user_data.get("average_life_event_frequency", 1), default=1.0)
        average_life_event_frequency = st.number_input(
            "Average Life Events per Year",
            value=alf_val,
            step=1.0
        )
    st.caption("💡 Planning for unexpected life events helps you stay on track toward your FIRE goals.")

    # ----- UI: Budget Items -----
    st.subheader("Budget Items")
    budget_item_keys = {
        "name":        {"type": str,   "default": ""},
        "value":       {"type": float, "default": 2000},
        "frequency":   {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]},
    }
    budget_items = generate_repeating_field_group(
        budget_item_keys,
        "budget",
        user_data.get("budget_items", [])
    )
    st.caption("💡 Regularly reviewing your budget can uncover additional savings opportunities.")

    # ----- UI: Investment Strategy -----
    st.subheader("Investment Strategy")
    investment_vehicle_keys = {
        "name":               {"type": str,   "default": "S&P 500"},
        "annual_returns":     {"type": float, "default": 0.1026},
        "standard_deviation": {"type": float, "default": 0.1532},
        "ratio":              {"type": float, "default": 1.0},
        "distribution_type":  {
            "type": "choice",
            "default": "normal-monthly",
            "choices": ["normal-monthly", "normal-yearly-gradient",
                        "historic-stocks", "historic-real-estate"]
        },
    }
    investment_vehicles = generate_repeating_field_group(
        investment_vehicle_keys,
        "investment",
        user_data.get("investment_vehicles", [])
    )
    st.caption("💡 Diversifying your investment portfolio can help balance risk and potential returns.")

    # ----- UI: Major Purchases -----
    st.subheader("Major Purchases")
    major_purchase_keys = {
        "item_name": {"type": str, "default": ""},
        "purchase_date": {"type": "date", "default": datetime.date.today()},
        "total_cost": {"type": float, "default": 0.0},
        "purchase_type": {"type": "choice", "choices": ["cash", "finance", "lease"], "default": "cash"},
        "down_payment": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type in ["finance", "lease"]
            }
        },
        "loan_amount": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "finance"
            }
        },
        "interest_rate": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "finance"
            }
        },
        "loan_term_months": {
            "type": int,
            "default": 36,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "finance"
            }
        },
        "lease_term_months": {
            "type": int,
            "default": 36,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "lease"
            }
        },
        "monthly_lease_payment": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "lease"
            }
        },
        "buy_residual": {
            "type": "checkbox",
            "default": False,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "lease"
            }
        },
        "residual_value": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type", "buy_residual": "buy_residual"},
                "func": lambda purchase_type, buy_residual: purchase_type == "lease" and buy_residual
            }
        },
        "consider_in_net_worth": {
            "type": "checkbox",
            "default": False,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type", "buy_residual": "buy_residual"},
                "func": lambda purchase_type, buy_residual: (
                    purchase_type in ["cash", "finance"] or
                    (purchase_type == "lease" and buy_residual)
                )
            }
        },
        "asset_value_change": {
            "type": "slider",
            "default": 0,
            "min": -20,
            "max": 20,
            "step": 0.5,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type",
                           "buy_residual": "buy_residual",
                           "consider_in_net_worth": "consider_in_net_worth"},
                "func": lambda purchase_type, buy_residual, consider_in_net_worth: (
                    (purchase_type in ["cash", "finance"] and consider_in_net_worth) or
                    (purchase_type == "lease" and buy_residual and consider_in_net_worth)
                )
            }
        }
    }
    major_purchases = generate_repeating_field_group(
        major_purchase_keys,
        "major_purchase",
        user_data.get("major_purchases", [])
    )
    st.caption("💡 Consider the long-term impact of major purchases on your FIRE timeline.")

    # ----- UI: Home Ownership -----
    st.subheader("Home Ownership")
    home_purchase = st.checkbox(
        "Plan to Purchase a Home",
        value=user_data.get("home_purchase", None) is not None
    )
    if home_purchase:
        home_purchase_data = user_data.get("home_purchase", {})
        col1, col2 = st.columns(2)
        with col1:
            default_date_str = home_purchase_data.get("date", "2025-01-01")
            try:
                default_date_dt = datetime.datetime.strptime(default_date_str, "%Y-%m-%d").date()
            except:
                default_date_dt = datetime.date.today()
            home_purchase_date = st.date_input(
                "Home Purchase Date",
                value=default_date_dt,
                min_value=datetime.date.today()
            )
            hp_price = ensure_float(home_purchase_data.get("price", 300000.0), default=300000.0)
            home_purchase_price = st.number_input(
                "Home Purchase Price",
                min_value=0.0,
                value=hp_price,
                step=10000.0,
                format="%0.2f"
            )
            dp = ensure_float(home_purchase_data.get("down_payment", 60000.0), default=60000.0)
            down_payment = st.number_input(
                "Down Payment",
                min_value=0.0,
                value=dp,
                step=1000.0,
                format="%0.2f"
            )
        with col2:
            mr_val = ensure_float(home_purchase_data.get("mortgage_rate", 0.04) * 100, default=4.0)
            mortgage_rate = st.slider(
                "Mortgage Rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=mr_val,
                step=0.1,
                format="%0.1f"
            )
            mty_val = ensure_float(home_purchase_data.get("mortgage_term_years", 30), default=30.0)
            mortgage_term_years = st.slider(
                "Mortgage Term (Years)",
                min_value=10,
                max_value=30,
                value=int(mty_val),
                step=1
            )
            pt_val = ensure_float(home_purchase_data.get("property_tax", 0.02) * 100, default=2.0)
            property_tax = st.slider(
                "Property Tax Rate (%)",
                min_value=0.0,
                max_value=5.0,
                value=pt_val,
                step=0.1,
                format="%0.1f"
            )
        pay_off_mortgage_before_retirement = st.checkbox(
            "Pay Off Mortgage Before Retirement",
            value=home_purchase_data.get("pay_off_before_retirement", False)
        )
        st.caption("💡 Homeownership can be significant. Consider the long-term costs and benefits.")
    else:
        home_purchase_data = None

    # ----- UI: Location Change -----
    st.subheader("Location Change")
    location_change = st.checkbox(
        "Plan to Change Location",
        value=user_data.get("location_change", {}).get("date") is not None
    )
    if location_change:
        location_change_data = user_data.get("location_change", {})
        col1, col2 = st.columns(2)
        with col1:
            try:
                lcd_str = location_change_data.get("date", "2025-01-01")
                lcd_dt = datetime.datetime.strptime(lcd_str, "%Y-%m-%d").date()
            except:
                lcd_dt = datetime.date.today()
            location_change_date = st.date_input(
                "Location Change Date",
                value=lcd_dt,
                min_value=datetime.date.today()
            )
            mc_val = ensure_float(location_change_data.get("moving_cost", 5000.0), default=5000.0)
            location_change_moving_cost = st.number_input(
                "Moving Cost",
                min_value=0.0,
                value=mc_val,
                step=1000.0,
                format="%0.2f"
            )
        with col2:
            col_val = ensure_float(location_change_data.get("col_adjustment", 1.0), default=1.0)
            location_change_col_adjustment = st.slider(
                "Cost of Living Adjustment",
                min_value=0.5,
                max_value=2.0,
                value=col_val,
                step=0.01
            )
            states = [
                "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
                "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
                "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
                "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
                "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
                "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
                "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
                "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
                "Washington D.C.", "Puerto Rico", "None"
            ]
            current_state_choice = location_change_data.get("state", "None")
            if current_state_choice not in states:
                current_state_choice = "None"
            location_change_state = st.selectbox(
                "New State",
                options=states,
                index=states.index(current_state_choice)
            )
        st.caption("💡 A location change can significantly impact cost of living and your FIRE timeline.")
    else:
        location_change_data = None

    # ----- UI: Simulation Params -----
    st.subheader("Simulation Parameters")
    col1, col2 = st.columns(2)
    with col1:
        sy_val = ensure_float(user_data.get("simulate_years", 10), default=10.0)
        simulate_years = st.slider(
            "Simulation Years",
            min_value=1, max_value=50,
            value=int(sy_val),
            step=1
        )
    with col2:
        ns_val = ensure_float(user_data.get("num_simulations", 100), default=100.0)
        num_simulations = st.slider(
            "Number of Simulations",
            min_value=1,
            max_value=1000,
            value=int(ns_val),
            step=10
        )
    st.caption("💡 More simulations and longer timeframes provide more detailed results but may take longer.")

    # ==============================
    #  RUN SCENARIO BUTTON
    # ==============================
    if st.button("Run Scenario Analysis"):
        # Update new_user_data with the modified values
        new_user_data.update({
            "income":                     income,
            "income_growth":              income_growth / 100,
            "risk_tolerance":             risk_tolerance,
            "current_savings":            current_savings,
            "emergency_fund_target":      emergency_fund_target,
            "post_retirement_expenses":   post_retirement_expenses,
            "average_post_retirement_income": average_post_retirement_income,
            "inflation":                  inflation / 100,
            "max_401k_contribution":      max_401k_contribution,
            "max_ira_contribution":       max_ira_contribution,
            "max_hsa_contribution":       max_hsa_contribution,
            "other_tax_sheltered_income": other_tax_sheltered_income,
            "married":                    married,
            "expenditure_growth_beyond_inflation": expenditure_growth / 100,
            "average_life_event_cost":    average_life_event_cost,
            "average_life_event_stdev":   average_life_event_stdev,
            "average_life_event_frequency": average_life_event_frequency,
            "budget_items":               budget_items,
            "investment_vehicles":        investment_vehicles,
            "major_purchases":            major_purchases,
            "simulate_years":             simulate_years,
            "num_simulations":            num_simulations,
        })

        if home_purchase:
            new_user_data["home_purchase"] = {
                "date":                 home_purchase_date.strftime("%Y-%m-%d"),
                "price":                home_purchase_price,
                "down_payment":         down_payment,
                "mortgage_rate":        mortgage_rate / 100,
                "mortgage_term_years":  mortgage_term_years,
                "property_tax":         property_tax / 100,
                "pay_off_before_retirement": pay_off_mortgage_before_retirement
            }
        else:
            new_user_data["home_purchase"] = None

        if location_change:
            new_user_data["location_change"] = {
                "date":          location_change_date.strftime("%Y-%m-%d"),
                "moving_cost":   location_change_moving_cost,
                "col_adjustment":location_change_col_adjustment,
                "state":         location_change_state
            }
        else:
            new_user_data["location_change"] = None

        # -------------
        # Run simulations
        # -------------
        with st.spinner("Running simulations..."):
            # Original scenario
            ts_df_original, avg_retirement_age_original, stdev_retirement_age_original, _, retirement_ages_original, original_user = run_simulation_local(user_data)

            # New scenario
            ts_df_new, avg_retirement_age_new, stdev_retirement_age_new, _, retirement_ages_new, new_user = run_simulation_local(new_user_data)

        # ======================
        #  DISPLAY RESULTS
        # ======================
        st.header("Scenario Analysis Results")

        # ... (The rest of your result-display code stays the same) ...
        # [No changes needed below here except that it's already working as intended.]

        # If no retirement ages found, handle None
        if avg_retirement_age_original is None:
            avg_retirement_age_original = (user_data.get("age", 22) + 65)  # fallback
        if avg_retirement_age_new is None:
            avg_retirement_age_new = (user_data.get("age", 22) + 65)       # fallback

        retirement_age_change = avg_retirement_age_new - avg_retirement_age_original
        total_days = abs(int(retirement_age_change * 365.25))
        years, remaining_days = divmod(total_days, 365)
        months, days = divmod(remaining_days, 30)
        time_diff_str = format_time_difference(years, months, days)

        st.markdown(
            f"# This scenario would {'delay' if retirement_age_change > 0 else 'accelerate'} your retirement by {time_diff_str}."
        )

        colA, colB, colC = st.columns(3)
        colA.metric("Original Retirement Age", f"{avg_retirement_age_original:.1f} years")
        colB.metric("New Retirement Age", f"{avg_retirement_age_new:.1f} years")
        colC.metric("Change",
                    f"{abs(retirement_age_change):.1f} yrs {'later' if retirement_age_change > 0 else 'earlier'}")

        # Net Worth Comparison
        st.subheader("Net Worth Comparison")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts_df_original['month'],
            y=ts_df_original['net_worth'],
            mode='lines',
            name='Original Scenario'
        ))
        fig.add_trace(go.Scatter(
            x=ts_df_new['month'],
            y=ts_df_new['net_worth'],
            mode='lines',
            name='New Scenario'
        ))
        fig.update_layout(
            title='Net Worth Over Time',
            xaxis_title='Month',
            yaxis_title='Net Worth ($)'
        )
        st.plotly_chart(fig)

        # Retirement Age Distribution
        st.subheader("Retirement Age Distribution")
        fig = go.Figure()
        if retirement_ages_original:
            fig.add_trace(go.Histogram(
                x=retirement_ages_original,
                name='Original Scenario',
                opacity=0.7
            ))
        if retirement_ages_new:
            fig.add_trace(go.Histogram(
                x=retirement_ages_new,
                name='New Scenario',
                opacity=0.7
            ))
        fig.update_layout(
            title='Retirement Age Distribution',
            xaxis_title='Retirement Age',
            yaxis_title='Count',
            barmode='overlay'
        )
        st.plotly_chart(fig)

        # Key Metrics Comparison
        st.subheader("Key Metrics Comparison")

        def annual_expenses(u): return calculate_annual_expenses(u)
        def monthly_expenses(u): return u.calculate_monthly_expenses()
        def annual_income(u): return calculate_annual_income(u)
        def savings_rate(u):
            inc = annual_income(u)
            exp = annual_expenses(u)
            if inc <= 0:
                return 0
            return 1 - (exp / inc)

        original_annual_expenses = annual_expenses(original_user)
        new_annual_expenses      = annual_expenses(new_user)
        original_monthly_expenses = monthly_expenses(original_user)
        new_monthly_expenses      = monthly_expenses(new_user)
        original_savings_rate = savings_rate(original_user)
        new_savings_rate      = savings_rate(new_user)

        base_age = user_data.get("age", 22)
        new_age  = new_user_data.get("age", 22)
        original_years_to_FIRE = (avg_retirement_age_original - base_age)
        new_years_to_FIRE      = (avg_retirement_age_new - new_age)

        def fire_number(u):
            return getattr(u, 'post_retirement_expenses', 0) * 25

        original_fire_num = fire_number(original_user)
        new_fire_num      = fire_number(new_user)

        metrics = [
            ("Annual Expenses",           original_annual_expenses, new_annual_expenses),
            ("Monthly Expenses",          original_monthly_expenses, new_monthly_expenses),
            ("Savings Rate",              original_savings_rate, new_savings_rate),
            ("Years to FIRE",             original_years_to_FIRE, new_years_to_FIRE),
            ("FIRE Number",               original_fire_num, new_fire_num)
        ]
        for metric, orig_val, new_val in metrics:
            c1, c2, c3 = st.columns(3)
            c1.metric(
                metric,
                format_currency(orig_val) if "Rate" not in metric and "Years" not in metric else (
                    format_percentage(orig_val) if "Rate" in metric else f"{orig_val:.1f}"
                )
            )
            c2.metric(
                "New " + metric,
                format_currency(new_val) if "Rate" not in metric and "Years" not in metric else (
                    format_percentage(new_val) if "Rate" in metric else f"{new_val:.1f}"
                )
            )
            diff = new_val - orig_val
            if "Rate" in metric:
                diff_str = format_percentage(diff)
            elif "Years" in metric:
                diff_str = f"{diff:.1f}"
            else:
                diff_str = format_currency(diff)
            c3.metric("Change", diff_str, delta_color="normal")

        # Investment Strategy Changes
        st.subheader("Investment Strategy Changes")
        original_investments = user_data.get('investment_vehicles', [])
        new_investments      = new_user_data.get('investment_vehicles', [])
        changes_str = []
        for old_v in original_investments:
            name = old_v.get('name', 'Unnamed')
            old_ratio = old_v.get('ratio', 0)
            match = next((nv for nv in new_investments if nv.get('name','') == name), None)
            new_ratio = match.get('ratio', 0) if match else 0
            changes_str.append(f"{name}: {old_ratio:.0%} → {new_ratio:.0%}")
        if not changes_str and new_investments:
            changes_str = [f"{v.get('name','Unnamed')}: {v.get('ratio',0):.0%}" for v in new_investments]
        st.write(", ".join(changes_str))

        # Risk Profile Changes
        st.subheader("Risk Profile Changes")
        original_swr = original_user.retirement_income_ratio
        new_swr      = new_user.retirement_income_ratio

        risk_metrics = [
            ("Risk Tolerance", original_user.risk_tolerance, new_user.risk_tolerance),
            ("Retirement Expenses", original_user.post_retirement_expenses, new_user.post_retirement_expenses),
            ("Safe Withdrawal Rate", original_swr, new_swr)
        ]
        for metric, orig_val, new_val in risk_metrics:
            c1, c2, c3 = st.columns(3)
            if "Rate" in metric or "Tolerance" in metric:
                orig_fmt = format_percentage(orig_val)
                new_fmt  = format_percentage(new_val)
                diff_val = new_val - orig_val
                diff_fmt = format_percentage(diff_val)
            else:
                orig_fmt = format_currency(orig_val)
                new_fmt  = format_currency(new_val)
                diff_val = new_val - orig_val
                diff_fmt = format_currency(diff_val)
            c1.metric(metric, orig_fmt)
            c2.metric("New " + metric, new_fmt)
            c3.metric("Change", diff_fmt, delta_color="normal")

        # Additional Changes
        st.subheader("Additional Changes")
        original_inf = user_data.get("inflation", 0.03)
        new_inf      = new_user_data.get("inflation", 0.03)

        additional_metrics = [
            ("Annual Income", annual_income(original_user), annual_income(new_user)),
            ("Income Growth", user_data.get("income_growth", 0.03), new_user_data.get("income_growth", 0.03)),
            ("Inflation Rate", original_inf, new_inf),
            ("Emergency Fund Target", original_user.emergency_fund_target, new_user.emergency_fund_target)
        ]
        for metric, orig_val, new_val in additional_metrics:
            c1, c2, c3 = st.columns(3)
            if "Rate" in metric or "Growth" in metric:
                orig_fmt = format_percentage(orig_val)
                new_fmt  = format_percentage(new_val)
                diff_val = new_val - orig_val
                diff_fmt = format_percentage(diff_val)
            elif "Income" in metric:
                orig_fmt = format_currency(orig_val)
                new_fmt  = format_currency(new_val)
                diff_val = new_val - orig_val
                diff_fmt = format_currency(diff_val)
            else:
                orig_fmt = format_currency(orig_val)
                new_fmt  = format_currency(new_val)
                diff_val = new_val - orig_val
                diff_fmt = format_currency(diff_val)

            c1.metric(metric, orig_fmt)
            c2.metric("New " + metric, new_fmt)
            c3.metric("Change", diff_fmt, delta_color="normal")

        final_nw_orig = original_user.calculate_net_worth()
        final_nw_new  = new_user.calculate_net_worth()
        if abs(final_nw_orig) < 0.01:
            net_worth_change_percent = 0
        else:
            net_worth_change_percent = (final_nw_new - final_nw_orig) / final_nw_orig * 100

        # Scenario Summary
        st.subheader("Scenario Summary")
        summary = f"""
**Highlights:**
1. Retirement age is projected to change by **{abs(retirement_age_change):.1f} years** ({'later' if retirement_age_change > 0 else 'earlier'}).
2. Final net worth is expected to {'increase' if net_worth_change_percent > 0 else 'decrease'} by **{abs(net_worth_change_percent):.1f}%**.
3. Savings rate changes from **{format_percentage(original_savings_rate)}** to **{format_percentage(new_savings_rate)}**.
4. Time to reach FIRE changes from **{original_years_to_FIRE:.1f}** years to **{new_years_to_FIRE:.1f}** years.
        """

        # Identify most significant changes
        significant_items = []
        all_items = metrics + risk_metrics + additional_metrics
        for (mname, oval, nval) in all_items:
            if isinstance(oval, (int, float)) and isinstance(nval, (int, float)) and abs(oval) > 1e-9:
                pctchg = (nval - oval) / oval * 100
                if abs(pctchg) > 10:
                    significant_items.append((mname, pctchg))
        significant_items.sort(key=lambda x: abs(x[1]), reverse=True)

        if significant_items:
            summary += "\n\n**Significant changes:**"
            for i, (mname, chg) in enumerate(significant_items[:3], start=1):
                summary += f"\n{i}. {mname} ({'+' if chg>0 else ''}{chg:.1f}%)"
        else:
            summary += "\n\nNo changes over 10% detected in these metrics."

        st.write(summary)
        st.caption("These projections depend on your scenario inputs. Revisit and update them as your situation changes.")


if __name__ == "__main__":
    main()
