import streamlit as st
import datetime
import os
import json
import boto3
from boto3.dynamodb.conditions import Key
import matplotlib.pyplot as plt

# DynamoDB configuration
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table('firesight-users')

# Set page configuration
st.set_page_config(page_title="FIRE Simulator", page_icon="🔥")

# Attempt to load FIRE.py script
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


def run_simulation_local(user_data):
    user = User()
    user.age = user_data.get("age", 22)
    user.income = user_data.get("income", 95000.0)
    user.risk_tolerance = user_data.get("risk_tolerance", 0.5)
    user.expenditure_growth_beyond_inflation = user_data.get("expenditure_growth_beyond_inflation", 0.03)
    user.current_savings = user_data.get("current_savings", 25000.0)
    user.max_401k_contribution = user_data.get("max_401k_contribution", True)
    user.max_ira_contribution = user_data.get("max_ira_contribution", True)
    user.max_hsa_contribution = user_data.get("max_hsa_contribution", False)
    user.other_tax_sheltered_income = user_data.get("other_tax_sheltered_income", 0.0)
    user.married = user_data.get("married", True)
    user.emergency_fund_target = user_data.get("emergency_fund_target", 10000.0)
    user.inflation = user_data.get("inflation", 0.03)
    user.average_life_event_cost = user_data.get("average_life_event_cost", 1000.0)
    user.average_life_event_stdev = user_data.get("average_life_event_stdev", 500.0)
    user.average_life_event_frequency = user_data.get("average_life_event_frequency", 1)
    user.post_retirement_expenses = user_data.get("post_retirement_expenses", 0.0)
    user.average_post_retirement_income = user_data.get("average_post_retirement_income", 0.0)
    user.income_growth = user_data.get("income_growth", 0.03)

    for budget_item in user_data.get("budget_items", []):
        formatted_budget_item = {
            "name": budget_item["name"],
            "value": budget_item["value"],
            "frequency": budget_item["frequency"]
        }
        user.add_budget_item(formatted_budget_item)
    
    ratio_sum = sum([investment_vehicle["ratio"] for investment_vehicle in user_data.get("investment_vehicles", [])])
    if ratio_sum != 1:
        st.error("The ratios of investment vehicles must add up to 1.")
    
    for investment_vehicle in user_data.get("investment_vehicles", []):
        user.add_investment_vehicle(investment_vehicle["name"], investment_vehicle["annual_returns"], investment_vehicle["standard_deviation"], investment_vehicle["ratio"])
    
    for major_expense in user_data.get("major_expenses", []):
        user.add_major_expense(major_expense["name"], major_expense["cost"], major_expense["date"])
    
    if user_data.get("home_purchase", {}).get("price", 0) != 0:
        user.home_purchase_date = user_data["home_purchase"]["date"]
        user.home_purchase_price = user_data["home_purchase"]["price"]
        user.down_payment = user_data["home_purchase"]["down_payment"]
        user.mortgage_rate = user_data["home_purchase"]["mortgage_rate"]
        user.mortgage_term_years = user_data["home_purchase"]["mortgage_term_years"]
        user.pay_off_mortgage_before_retirement = user_data["home_purchase"]["pay_off_before_retirement"]
        user.property_tax = user_data["home_purchase"]["property_tax"]
    
    if user_data.get("location_change", {}).get("date", None):
        user.location_change = True
        user.location_change_date = user_data["location_change"]["date"]
        user.location_change_moving_costs = user_data["location_change"]["moving_cost"]
        user.location_col_adjustment = user_data["location_change"]["col_adjustment"]
        user.location_change_state = user_data["location_change"]["state"]
        
    st.success("Running Simulation...")
    simulate_years = user_data.get("simulate_years", 10)
    num_simulations = user_data.get("num_simulations", 10)

    ts_df, average_retirement_age, stdev_retirement_age = monte_carlo_simulation(years=simulate_years, simulations=num_simulations, user=user)

    bottom_range = round(average_retirement_age - stdev_retirement_age)
    top_range = round(average_retirement_age + stdev_retirement_age)
    st.title(f"Your Estimated Retirement Age is between :orange[{bottom_range}] and :orange[{top_range}] years old")
    st.title(f"We ran {num_simulations} simulations of {simulate_years} years. Here are the results:")

    st.subheader(f"Here is Your Projected Net Worth and Investments Over The Next {simulate_years} Years:")
    df_net_worth = ts_df[["net_worth", "investments", "month"]]
    df_net_worth = df_net_worth.set_index("month")
    st.line_chart(df_net_worth)

    if user.home_purchase_date is not None:
        st.subheader("Your Home Equity")
        df_home_equity = ts_df[["home_equity_value_with_growth", "month"]]
        st.line_chart(df_home_equity.set_index("month"))

    if len(list(user.budget.keys())) > 1:
        budget = user.budget
        categories = list(budget.keys())
        values = [budget[category]["value"] if budget[category]["frequency"] == "monthly" else budget[category]["value"]/12 for category in categories]
        st.subheader("Here is a breakdown of your proposed budget:")
        fig1, ax1 = plt.subplots()
        plt.pie(values, labels=categories, autopct='%1.1f%%')
        ax1.axis('equal')
        st.pyplot(fig1)
        st.subheader(f"Average Monthly Budget: ${round(sum(values), 2)}")

    st.subheader("Here is the raw data for your simulation:")
    st.write(ts_df)

if __name__ == "__main__":
    # Assume user_id is stored in session state after logging in
    user_id = st.session_state.get('user_id')
    if user_id:
        user_data = load_user_profile(user_id)
        if user_data:
            if st.button("Run Updated Simulation"):
                run_simulation_local(user_data)
        else:
            st.error("Failed to load user profile.")
    else:
        st.error("User not logged in.")
