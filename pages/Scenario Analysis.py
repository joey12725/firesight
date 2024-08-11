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
 
# DynamoDB configuration
try: 
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('firesight-users')
except:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    table = dynamodb.Table('firesight-users')

# Set page configuration
st.set_page_config(page_title="FIRESight - Scenario Analysis", page_icon="🔍", layout="wide")

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

def dict_to_user(user_data):
    user = User()
    user.__dict__.update(user_data)
    return user

def format_currency(value):
    return f"${value:,.0f}"

def format_percentage(value):
    return f"{value:.1%}"

def format_time_difference(years, months, days):
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
    
def main():
    st.title("🔍 Scenario Analysis")
    st.write("Explore how changes to your financial plan could impact your journey to FIRE.")

    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        return

    user_data = load_user_profile(user_id)
    if not user_data:
        st.error("Failed to load user profile.")
        return

    original_user = dict_to_user(user_data)
    new_user_data = user_data.copy()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Income and Savings")
        income = st.number_input("Annual Income", value=user_data.get("income", 95000.0), step=1000.0, format="%0.2f")
        st.caption("💡 Increasing your income is one of the most impactful ways to accelerate your FIRE journey.")
        
        income_growth = st.slider("Income Growth (%/year)", min_value=0.0, max_value=10.0, value=user_data.get("income_growth", 3.0)*100, step=0.1, format="%0.1f")
        st.caption("💡 Even small increases in annual income growth can have a significant impact over time.")
        
        current_savings = st.number_input("Current Savings", value=user_data.get("current_savings", 25000.0), step=1000.0, format="%0.2f")
        
        emergency_fund_target = st.number_input("Emergency Fund Target", value=user_data.get("emergency_fund_target", 10000.0), step=1000.0, format="%0.2f")
        st.caption("💡 A robust emergency fund can prevent setbacks in your FIRE journey.")

    with col2:
        st.subheader("Retirement and Risk")
        risk_tolerance = st.slider("Risk Tolerance", 0.0, 1.0, value=user_data.get("risk_tolerance", 0.5), step=0.01)
        st.caption("💡 Higher risk tolerance allows for more aggressive investment strategies but comes with increased volatility.")
        
        post_retirement_expenses = st.number_input("Post-Retirement Annual Expenses", value=user_data.get("post_retirement_expenses", 0.0), step=1000.0, format="%0.2f")
        st.caption("💡 Lowering your post-retirement expenses can significantly reduce the amount you need to save.")
        
        average_post_retirement_income = st.number_input("Average Post-Retirement Annual Income", value=user_data.get("average_post_retirement_income", 0.0), step=1000.0, format="%0.2f")
        
        inflation = st.slider("Inflation Rate (%/year)", min_value=0.0, max_value=10.0, value=user_data.get("inflation", 3.0)*100, step=0.1, format="%0.1f")
        st.caption("💡 Consider how different inflation scenarios might affect your long-term plans.")

    st.subheader("Tax-Advantaged Accounts")
    col1, col2, col3 = st.columns(3)
    with col1:
        max_401k_contribution = st.checkbox("Max 401(k) Contribution", value=user_data.get("max_401k_contribution", True))
    with col2:
        max_ira_contribution = st.checkbox("Max IRA Contribution", value=user_data.get("max_ira_contribution", True))
    with col3:
        max_hsa_contribution = st.checkbox("Max HSA Contribution", value=user_data.get("max_hsa_contribution", False))
    st.caption("💡 Maximizing contributions to tax-advantaged accounts can significantly boost your savings rate.")

    other_tax_sheltered_income = st.number_input("Other Tax-Sheltered Income", value=user_data.get("other_tax_sheltered_income", 0.0), step=1000.0, format="%0.2f")

    st.subheader("Lifestyle and Expenses")
    col1, col2 = st.columns(2)
    with col1:
        married = st.checkbox("Married", value=user_data.get("married", True))
    with col2:
        expenditure_growth = st.slider("Expense Growth Beyond Inflation (%/year)", min_value=0.0, max_value=10.0, value=user_data.get("expenditure_growth_beyond_inflation", 3.0)*100, step=0.1, format="%0.1f")
        st.caption("💡 Controlling lifestyle inflation can have a major impact on your savings rate and FIRE timeline.")

    st.subheader("Life Events")
    col1, col2, col3 = st.columns(3)
    with col1:
        average_life_event_cost = st.number_input("Average Life Event Cost", value=user_data.get("average_life_event_cost", 1000.0), step=100.0, format="%0.2f")
    with col2:
        average_life_event_stdev = st.number_input("Life Event Cost Std Dev", value=user_data.get("average_life_event_stdev", 500.0), step=100.0, format="%0.2f")
    with col3:
        average_life_event_frequency = st.number_input("Average Life Events per Year", value=user_data.get("average_life_event_frequency", 1), step=1)
    st.caption("💡 Planning for unexpected life events can help you stay on track towards your FIRE goals.")

    st.subheader("Budget Items")
    budget_item_keys = {
        "name": {"type": str, "default": ""},
        "value": {"type": float, "default": 2000},
        "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]}
    }
    budget_items = generate_repeating_field_group(budget_item_keys, "budget", user_data.get("budget_items", []))
    st.caption("💡 Regularly reviewing and optimizing your budget can uncover additional savings opportunities.")

    st.subheader("Investment Strategy")
    investment_vehicle_keys = {
        "name": {"type": str, "default": "S&P 500"},
        "annual_returns": {"type": float, "default": 0.1026},
        "standard_deviation": {"type": float, "default": 0.1532},
        "ratio": {"type": float, "default": 1.0},
        "distribution_type": {"type": "choice", "default": "normal-monthly", "choices": ["normal-monthly", "normal-yearly-gradient", "historic-stocks", "historic-real-estate"]}
    }
    investment_vehicles = generate_repeating_field_group(investment_vehicle_keys, "investment", user_data.get("investment_vehicles", []))
    st.caption("💡 Diversifying your investment portfolio can help balance risk and potential returns.")

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
                "func": lambda purchase_type, buy_residual: purchase_type in ["cash", "finance"] or (purchase_type == "lease" and buy_residual)
            }
        },
        "asset_value_change": {
            "type": "slider",
            "default": 0,
            "min": -20,
            "max": 20,
            "step": 0.5,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type", "buy_residual": "buy_residual", "consider_in_net_worth": "consider_in_net_worth"},
                "func": lambda purchase_type, buy_residual, consider_in_net_worth: 
                    (purchase_type in ["cash", "finance"] and consider_in_net_worth) or 
                    (purchase_type == "lease" and buy_residual and consider_in_net_worth)
            }
        }
    }
    major_purchases = generate_repeating_field_group(major_purchase_keys, "major_purchase", user_data.get("major_purchases", []))
    st.caption("💡 Consider the long-term impact of major purchases on your FIRE timeline.")

    st.subheader("Home Ownership")
    home_purchase = st.checkbox("Plan to Purchase a Home", value=user_data.get("home_purchase", None) is not None)
    if home_purchase:
        home_purchase_data = user_data.get("home_purchase", {})
        col1, col2 = st.columns(2)
        with col1:
            default_date = home_purchase_data.get("date") or "2025-01-01"
            home_purchase_date = st.date_input(
                "Home Purchase Date",
                value=datetime.datetime.strptime(default_date, "%Y-%m-%d").date(),
                min_value=datetime.date.today()
            )
            home_purchase_price = st.number_input("Home Purchase Price", min_value=0.0, value=home_purchase_data.get("price", 300000.0), step=10000.0, format="%0.2f")
            down_payment = st.number_input("Down Payment", min_value=0.0, value=home_purchase_data.get("down_payment", 60000.0), step=1000.0, format="%0.2f")
        with col2:
            if home_purchase_data is not None:
                if home_purchase_data.get("mortgage_rate"):
                    mortgage_rate = st.slider("Mortgage Rate (%)", min_value=0.0, max_value=10.0, value=home_purchase_data.get("mortgage_rate", 4.0)*100, step=0.1, format="%0.1f")
                else:
                    mortgage_rate = st.slider("Mortgage Rate (%)", min_value=0.0, max_value=10.0, value=4.0, step=0.1, format="%0.1f")
                if home_purchase_data.get("mortgage_term_years"):
                    mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=home_purchase_data.get("mortgage_term_years", 30), step=1)
                else:
                    mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=30, step=1)
                if home_purchase_data.get("property_tax"):
                    property_tax = st.slider("Property Tax Rate (%)", min_value=0.0, max_value=5.0, value=home_purchase_data.get("property_tax", 2.0)*100, step=0.1, format="%0.1f")
                else:
                    property_tax = st.slider("Property Tax Rate (%)", min_value=0.0, max_value=5.0, value=2.0, step=0.1, format="%0.1f")
            else:
                mortgage_rate = st.slider("Mortgage Rate (%)", min_value=0.0, max_value=10.0, value=4.0, step=0.1, format="%0.1f")
                mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=30, step=1)
                property_tax = st.slider("Property Tax Rate (%)", min_value=0.0, max_value=5.0, value=2.0, step=0.1, format="%0.1f")
        pay_off_mortgage_before_retirement = st.checkbox("Pay Off Mortgage Before Retirement", value=home_purchase_data.get("pay_off_before_retirement", False))
        st.caption("💡 Homeownership can be a significant factor in your FIRE journey. Consider the long-term costs and benefits.")
    st.subheader("Location Change")
    location_change = st.checkbox("Plan to Change Location", value=user_data.get("location_change", {}).get("date") is not None)
    if location_change:
        location_change_data = user_data.get("location_change", {})
        col1, col2 = st.columns(2)
        with col1:
            location_change_date = st.date_input("Location Change Date", value=datetime.datetime.strptime(location_change_data.get("date", "2025-01-01"), "%Y-%m-%d").date(), min_value=datetime.date.today())
            location_change_moving_cost = st.number_input("Moving Cost", min_value=0.0, value=location_change_data.get("moving_cost", 5000.0), step=1000.0, format="%0.2f")
        with col2:
            location_change_col_adjustment = st.slider("Cost of Living Adjustment", min_value=0.5, max_value=2.0, value=location_change_data.get("col_adjustment", 1.0), step=0.01)
            states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Washington D.C.", "Puerto Rico", "None"]
            location_change_state = st.selectbox("New State", options=states, index=states.index(location_change_data.get("state", "None")))
        st.caption("💡 A location change can significantly impact your cost of living and potentially your FIRE timeline.")

    st.subheader("Simulation Parameters")
    col1, col2 = st.columns(2)
    with col1:
        simulate_years = st.slider("Simulation Years", min_value=1, max_value=50, value=user_data.get("simulate_years", 10), step=1)
    with col2:
        num_simulations = st.slider("Number of Simulations", min_value=1, max_value=1000, value=user_data.get("num_simulations", 100), step=10)
    st.caption("💡 More simulations and longer timeframes provide more accurate results but take longer to compute.")

    if st.button("Run Scenario Analysis"):
        # Update new_user_data with the modified values
        new_user_data.update({
            "age": user_data.get("age", 22),
            "income": income,
            "income_growth": income_growth / 100,
            "risk_tolerance": risk_tolerance,
            "expenditure_growth_beyond_inflation": expenditure_growth / 100,
            "current_savings": current_savings,
            "max_401k_contribution": max_401k_contribution,
            "max_ira_contribution": max_ira_contribution,
            "max_hsa_contribution": max_hsa_contribution,
            "other_tax_sheltered_income": other_tax_sheltered_income,
            "married": married,
            "emergency_fund_target": emergency_fund_target,
            "inflation": inflation / 100,
            "average_life_event_cost": average_life_event_cost,
            "average_life_event_stdev": average_life_event_stdev,
            "average_life_event_frequency": average_life_event_frequency,
            "post_retirement_expenses": post_retirement_expenses,
            "average_post_retirement_income": average_post_retirement_income,
            "budget_items": budget_items,
            "investment_vehicles": investment_vehicles,
            "major_purchases": major_purchases,
            "simulate_years": simulate_years,
            "num_simulations": num_simulations,
        })

        if home_purchase:
            new_user_data["home_purchase"] = {
                "date": home_purchase_date.strftime("%Y-%m-%d"),
                "price": home_purchase_price,
                "down_payment": down_payment,
                "mortgage_rate": mortgage_rate / 100,
                "mortgage_term_years": mortgage_term_years,
                "property_tax": property_tax / 100,
                "pay_off_before_retirement": pay_off_mortgage_before_retirement
            }
        else:
            new_user_data["home_purchase"] = None

        if location_change:
            new_user_data["location_change"] = {
                "date": location_change_date.strftime("%Y-%m-%d"),
                "moving_cost": location_change_moving_cost,
                "col_adjustment": location_change_col_adjustment,
                "state": location_change_state
            }
        else:
            new_user_data["location_change"] = None

        # Run simulations
        with st.spinner("Running simulations..."):
            ts_df_original, avg_retirement_age_original, stdev_retirement_age_original, _, retirement_ages_original, original_user = run_simulation_local(user_data)
            ts_df_new, avg_retirement_age_new, stdev_retirement_age_new, _, retirement_ages_new, new_user = run_simulation_local(new_user_data)

        # Display results
        st.header("Scenario Analysis Results")

        # After calculating retirement_age_change
        retirement_age_change = avg_retirement_age_new - avg_retirement_age_original
        
        # Calculate years, months, and days
        total_days = abs(int(retirement_age_change * 365.25))  # Using 365.25 to account for leap years
        years, remaining_days = divmod(total_days, 365)
        months, days = divmod(remaining_days, 30)
        
        # Format the time difference
        time_diff_str = format_time_difference(years, months, days)
        
        # Display the banner
        st.markdown(f"# This scenario would {'delay' if retirement_age_change > 0 else 'accelerate'} your retirement by {time_diff_str}.")

        # Continue with the rest of your results display
        col1, col2, col3 = st.columns(3)
        col1.metric("Original Retirement Age", f"{avg_retirement_age_original:.1f} years")
        col2.metric("New Retirement Age", f"{avg_retirement_age_new:.1f} years")
        col3.metric("Change", f"{abs(retirement_age_change):.1f} years {'later' if retirement_age_change > 0 else 'earlier'}")

        # Visualizations
        st.subheader("Net Worth Comparison")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ts_df_original['month'], y=ts_df_original['net_worth'], mode='lines', name='Original Scenario'))
        fig.add_trace(go.Scatter(x=ts_df_new['month'], y=ts_df_new['net_worth'], mode='lines', name='New Scenario'))
        fig.update_layout(title='Net Worth Over Time', xaxis_title='Month', yaxis_title='Net Worth ($)')
        st.plotly_chart(fig)

        st.subheader("Retirement Age Distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=retirement_ages_original, name='Original Scenario', opacity=0.7))
        fig.add_trace(go.Histogram(x=retirement_ages_new, name='New Scenario', opacity=0.7))
        fig.update_layout(title='Retirement Age Distribution', xaxis_title='Retirement Age', yaxis_title='Count', barmode='overlay')
        st.plotly_chart(fig)

        # Key Metrics Comparison
        st.subheader("Key Metrics Comparison")
        metrics = [
            ("Annual Expenses", original_user.calculate_annual_expenses(), new_user.calculate_annual_expenses()),
            ("Monthly Expenses", original_user.calculate_monthly_expenses(), new_user.calculate_monthly_expenses()),
            ("Savings Rate", 1 - (original_user.calculate_monthly_expenses() * 12) / original_user.income, 1 - (new_user.calculate_monthly_expenses() * 12) / new_user.income),
            ("Years to FIRE", avg_retirement_age_original - original_user.age, avg_retirement_age_new - new_user.age),
            ("FIRE Number", original_user.post_retirement_expenses * 25, new_user.post_retirement_expenses * 25)
        ]

        for metric, original, new in metrics:
            col1, col2, col3 = st.columns(3)
            col1.metric(metric, format_currency(original) if "Rate" not in metric else format_percentage(original))
            col2.metric("New " + metric, format_currency(new) if "Rate" not in metric else format_percentage(new))
            change = new - original
            col3.metric("Change", format_currency(change) if "Rate" not in metric else format_percentage(change), delta_color="normal")

        # Investment Strategy Changes
        st.subheader("Investment Strategy Changes")
        investment_changes = []
        for v in original_user.investment_vehicles:
            new_ratio = next((nv.ratio for nv in new_user.investment_vehicles if nv.name == v.name), v.ratio)
            investment_changes.append(f"{v.name}: {v.ratio:.0%} -> {new_ratio:.0%}")
        st.write(", ".join(investment_changes))

        # Risk Profile Changes
        st.subheader("Risk Profile Changes")
        risk_metrics = [
            ("Risk Tolerance", original_user.risk_tolerance, new_user.risk_tolerance),
            ("Retirement Expenses", original_user.post_retirement_expenses, new_user.post_retirement_expenses),
            ("Safe Withdrawal Rate", original_user.retirement_income_ratio, new_user.retirement_income_ratio)
        ]

        for metric, original, new in risk_metrics:
            col1, col2, col3 = st.columns(3)
            col1.metric(metric, format_percentage(original) if "Rate" in metric else format_currency(original))
            col2.metric("New " + metric, format_percentage(new) if "Rate" in metric else format_currency(new))
            change = new - original
            col3.metric("Change", format_percentage(change) if "Rate" in metric else format_currency(change), delta_color="normal")

        # Additional Changes
        st.subheader("Additional Changes")
        additional_metrics = [
            ("Income", original_user.income, new_user.income),
            ("Income Growth", original_user.income_growth, new_user.income_growth),
            ("Inflation Rate", original_user.inflation, new_user.inflation),
            ("Emergency Fund Target", original_user.emergency_fund_target, new_user.emergency_fund_target)
        ]

        for metric, original, new in additional_metrics:
            col1, col2, col3 = st.columns(3)
            col1.metric(metric, format_currency(original) if "Rate" not in metric else format_percentage(original))
            col2.metric("New " + metric, format_currency(new) if "Rate" not in metric else format_percentage(new))
            change = new - original
            col3.metric("Change", format_currency(change) if "Rate" not in metric else format_percentage(change), delta_color="normal")
        
        net_worth_change = (new_user.calculate_net_worth() - original_user.calculate_net_worth()) / max(original_user.calculate_net_worth(), 0.01) * 100
        # Scenario Summary
        st.subheader("Scenario Summary")
        summary = f"""
        Based on the changes in this scenario:
        
        1. Your retirement age is projected to change by {abs(retirement_age_change):.1f} years ({'earlier' if retirement_age_change < 0 else 'later'}).
        2. Your final net worth is expected to {'increase' if net_worth_change > 0 else 'decrease'} by {abs(net_worth_change):.1f}%.
        3. Your savings rate would change from {format_percentage(1 - (original_user.calculate_monthly_expenses() * 12) / original_user.income)} to {format_percentage(1 - (new_user.calculate_monthly_expenses() * 12) / new_user.income)}.
        4. Your time to reach FIRE would change from {avg_retirement_age_original - original_user.age:.1f} years to {avg_retirement_age_new - new_user.age:.1f} years.
        
        The most significant changes in this scenario are:
        """
        significant_changes = []
        for metric, original, new in metrics + risk_metrics + additional_metrics:
            if isinstance(original, (int, float)) and isinstance(new, (int, float)):
                percent_change = abs((new - original) / original) * 100 if original != 0 else 0
                if percent_change > 10:  # Consider changes over 10% as significant
                    significant_changes.append((metric, percent_change))
        
        significant_changes.sort(key=lambda x: x[1], reverse=True)
        for i, (metric, change) in enumerate(significant_changes[:3], 1):
            summary += f"\n{i}. {metric} ({'increase' if change > 0 else 'decrease'} of {abs(change):.1f}%)"
        
        st.write(summary)

        st.caption("Remember, these projections are based on the assumptions in your scenario. Regular reviews and adjustments to your FIRE plan are essential as your circumstances change.")

if __name__ == "__main__":
    main()