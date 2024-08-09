import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import datetime
import json
import pandas as pd
import os
import plotly.graph_objects as go
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
st.set_page_config(page_title="FIRESight - Scenario Analysis", page_icon="🔍")

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

def dict_to_user(user_data):
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
    
    for investment_vehicle in user_data.get("investment_vehicles", []):
        user.add_investment_vehicle(
            investment_vehicle["name"],
            investment_vehicle["annual_returns"],
            investment_vehicle["standard_deviation"],
            investment_vehicle["ratio"],
            investment_vehicle.get("distribution_type", "normal-monthly")
        )
    
    for purchase in user_data.get("major_purchases", []):
        user.add_major_purchase(
            item_name=purchase["item_name"],
            purchase_date=purchase["purchase_date"],
            total_cost=purchase["total_cost"],
            purchase_type=purchase["purchase_type"],
            down_payment=purchase.get("down_payment", 0),
            loan_amount=purchase.get("loan_amount", 0),
            interest_rate=purchase.get("interest_rate", 0),
            loan_term_months=purchase.get("loan_term_months", 0),
            lease_term_months=purchase.get("lease_term_months", 0),
            monthly_lease_payment=purchase.get("monthly_lease_payment", 0),
            buy_residual=purchase.get("buy_residual", False),
            residual_value=purchase.get("residual_value", 0),
            consider_in_net_worth=purchase.get("consider_in_net_worth", False),
            asset_value_change=purchase.get("asset_value_change", 0)
        )
    
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

    return user

if __name__ == "__main__":
    user_id = st.session_state.get('user_id')
    if user_id:
        user_data = load_user_profile(user_id)
        if user_data:
            st.header("Scenario Analysis")
            st.subheader("Compare your profile with a version that has hypothetical changes and see how it could impact your financial independence goals:")

            # Load existing settings but allow modifications for scenario analysis
            income = st.number_input("Income", value=user_data.get("income", 95000.0))
            risk_tolerance = st.slider("Risk Tolerance", 0.0, 1.0, value=user_data.get("risk_tolerance", 0.5))
            income_growth = st.slider("Income Growth", min_value=0.0, max_value=0.2, value=user_data.get("income_growth",0.03), step=0.01)
            expenditure_growth = st.number_input("Expenditure Growth Beyond Inflation", value=user_data.get("expenditure_growth_beyond_inflation", 0.03))
            current_savings = st.number_input("Current Savings", value=user_data.get("current_savings", 25000.0))
            max_401k_contribution = st.checkbox("Max 401k Contribution", value=user_data.get("max_401k_contribution", True))
            max_ira_contribution = st.checkbox("Max IRA Contribution", value=user_data.get("max_ira_contribution", True))
            max_hsa_contribution = st.checkbox("Max HSA Contribution", value=user_data.get("max_hsa_contribution", False))
            other_tax_sheltered_income = st.number_input("Other Tax Sheltered Income", value=user_data.get("other_tax_sheltered_income", 0.0))
            married = st.checkbox("Married", value=user_data.get("married", True))
            emergency_fund_target = st.number_input("Emergency Fund Target", value=user_data.get("emergency_fund_target", 10000.0))
            inflation = st.number_input("Inflation", value=user_data.get("inflation", 0.03))
            average_life_event_cost = st.number_input("Average Life Event Cost", value=user_data.get("average_life_event_cost", 1000.0))
            average_life_event_stdev = st.number_input("Average Life Event Standard Deviation", value=user_data.get("average_life_event_stdev", 500.0))
            average_life_event_frequency = st.number_input("Average Life Event Frequency (per year)", value=user_data.get("average_life_event_frequency", 1))
            post_retirement_expenses = st.number_input("Post Retirement Expenses", value=user_data.get("post_retirement_expenses", 0.0))
            average_post_retirement_income = st.number_input("Average Post Retirement Income", value=user_data.get("average_post_retirement_income", 0.0))

            budget_item_keys = {
                "name": {"type": str, "default": ""},
                "value": {"type": int, "default": 2000},
                "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]}
            }

            investment_vehicle_keys = {
                "name": {"type": str, "default": "S&P 500"},
                "annual_returns": {"type": float, "default": 0.1026},
                "standard_deviation": {"type": float, "default": 0.1532},
                "ratio": {"type": float, "default": 1.0},
                "distribution_type": {"type": "choice", "default": "normal-monthly", "choices": ["normal-monthly", "normal-yearly-gradient", "historic-stocks", "historic-real-estate"]}
            }

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

            st.subheader("Budget Items")
            budget_items = generate_repeating_field_group(budget_item_keys, "budget", user_data.get("budget_items", []))

            st.subheader("Investment Vehicles")
            investment_vehicles = generate_repeating_field_group(investment_vehicle_keys, "investment", user_data.get("investment_vehicles", []))

            st.subheader("Major Expenses")
            major_purchases = generate_repeating_field_group(major_purchase_keys, "major_purchase", user_data.get("major_purchases", []))
            home_purchase_enabled = "home_purchase_enabled" in st.session_state or user_data.get("home_purchase", {}).get("price", 0) != 0
            home_purchase = st.checkbox("Plan to Purchase a Home", value=home_purchase_enabled, key="home_purchase_enabled")
            if home_purchase:
                st.subheader("Home Purchase Details")
                home_purchase_data = user_data.get("home_purchase", {})
                home_purchase_date_default = "2025-01-01"
                home_purchase_date_str = str(home_purchase_data.get("date", home_purchase_date_default))
                if home_purchase_date_str:
                    try:
                        home_purchase_date_value = datetime.date.fromisoformat(home_purchase_date_str)
                    except ValueError:
                        home_purchase_date_value = datetime.date.fromisoformat(home_purchase_date_default)
                else:
                    home_purchase_date_value = datetime.date(2025, 1, 1)

                home_purchase_date = st.date_input("Home Purchase Date", value=home_purchase_date_value, min_value=datetime.date.today())
                home_purchase_price = st.number_input("Home Purchase Price", min_value=0.0, value=home_purchase_data.get("price", 300000.0), step=10000.0)
                down_payment = st.number_input("Down Payment", min_value=0.0, value=home_purchase_data.get("down_payment", 60000.0), step=1000.0)
                property_tax = st.number_input("Local Property Tax", min_value=0.0, max_value=0.5, value=home_purchase_data.get("property_tax", 0.02), step=0.005)
                mortgage_rate = st.slider("Mortgage Rate", min_value=0.0, max_value=0.1, value=home_purchase_data.get("mortgage_rate", 0.04), step=0.001)
                mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=home_purchase_data.get("mortgage_term_years", 30), step=1)
                pay_off_mortgage_before_retirement = st.checkbox("Pay Off Mortgage Before Retirement", value=home_purchase_data.get("pay_off_before_retirement", False))
            
            location_change_enabled = "location_change_enabled" in st.session_state or user_data.get("location_change", {}).get("date", None) is not None
            location_change = st.checkbox("Plan to Change Location (domestic only)", value=location_change_enabled, key="location_change_enabled")
            if location_change:
                st.subheader("Location Change Details")
                location_change_data = user_data.get("location_change", {})
                location_change_date_default = "2025-01-01"
                location_change_date_str = str(location_change_data.get("date", location_change_date_default))

                try:
                    location_change_date_value = datetime.date.fromisoformat(location_change_date_str)
                except ValueError:
                    location_change_date_value = datetime.date.fromisoformat(location_change_date_default)

                location_change_date = st.date_input("Location Change Date", value=location_change_date_value, min_value=datetime.date.today())
                location_change_moving_cost = st.number_input("Moving Cost", min_value=0.0, value=location_change_data.get("moving_cost", 5000.0), step=1000.0)
                location_change_col_adjustment = st.slider("Cost of Living Adjustment", min_value=0.0, max_value=2.0, value=location_change_data.get("col_adjustment", 1.0), step=0.01)
                states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Washington D.C.", "Puerto Rico", "None"]
                location_change_state = st.selectbox("State", options=states, index=states.index(location_change_data.get("state", "None") if location_change_data.get("state", "None") in states else "None"))

            if st.button("Run Comparison"):
                original_user_data = user_data.copy()
                new_user_data = {
                    "age": user_data.get("age", 22),
                    "income": income,
                    "risk_tolerance": risk_tolerance,
                    "expenditure_growth_beyond_inflation": expenditure_growth,
                    "current_savings": current_savings,
                    "max_401k_contribution": max_401k_contribution,
                    "max_ira_contribution": max_ira_contribution,
                    "max_hsa_contribution": max_hsa_contribution,
                    "other_tax_sheltered_income": other_tax_sheltered_income,
                    "married": married,
                    "emergency_fund_target": emergency_fund_target,
                    "inflation": inflation,
                    "average_life_event_cost": average_life_event_cost,
                    "average_life_event_stdev": average_life_event_stdev,
                    "average_life_event_frequency": average_life_event_frequency,
                    "post_retirement_expenses": post_retirement_expenses,
                    "average_post_retirement_income": average_post_retirement_income,
                    "budget_items": [{"name": item["name"], "value": item["value"], "frequency": item["frequency"]} for item in budget_items],
                    "investment_vehicles": [
                        {
                            "name": vehicle["name"],
                            "annual_returns": vehicle["annual_returns"],
                            "standard_deviation": vehicle["standard_deviation"],
                            "ratio": vehicle["ratio"],
                            "distribution_type": vehicle["distribution_type"]
                        } for vehicle in investment_vehicles
                    ],                   
                    "major_purchases": [
                        {
                            "item_name": purchase["item_name"],
                            "purchase_date": str(purchase["purchase_date"]),
                            "total_cost": purchase["total_cost"],
                            "purchase_type": purchase["purchase_type"],
                            "down_payment": purchase.get("down_payment", 0),
                            "loan_amount": purchase.get("loan_amount", 0),
                            "interest_rate": purchase.get("interest_rate", 0),
                            "loan_term_months": purchase.get("loan_term_months", 0),
                            "lease_term_months": purchase.get("lease_term_months", 0),
                            "monthly_lease_payment": purchase.get("monthly_lease_payment", 0),
                            "buy_residual": purchase.get("buy_residual", False),
                            "residual_value": purchase.get("residual_value", 0),
                            "consider_in_net_worth": purchase.get("consider_in_net_worth", False),
                            "asset_value_change": purchase.get("asset_value_change", 0)
                        } for purchase in major_purchases
                    ],
                    "home_purchase": {
                        "date": str(home_purchase_date) if home_purchase else None,
                        "price": home_purchase_price if home_purchase else None,
                        "down_payment": down_payment if home_purchase else None,
                        "mortgage_rate": mortgage_rate if home_purchase else None,
                        "mortgage_term_years": mortgage_term_years if home_purchase else None,
                        "pay_off_before_retirement": pay_off_mortgage_before_retirement if home_purchase else None,
                        "property_tax": property_tax if home_purchase else None,
                    },
                    "location_change": {
                        "date": str(location_change_date) if location_change else None,
                        "moving_cost": location_change_moving_cost if location_change else None,
                        "col_adjustment": location_change_col_adjustment if location_change else None,
                        "state": location_change_state if location_change else None
                    },
                    "simulate_years": user_data.get("simulate_years", 10),
                    "num_simulations": user_data.get("num_simulations", 10),
                    "income_growth": income_growth
                }

                # Run original simulation
                ts_df_original, average_retirement_age_original, stdev_retirement_age_original, all_time_series_original, retirement_ages_original, original_user = run_simulation_local(original_user_data)

                # Run new simulation
                ts_df_new, average_retirement_age_new, stdev_retirement_age_new, all_time_series_new, retirement_ages_new, new_user = run_simulation_local(new_user_data)

                # Calculate change in retirement age
                retirement_age_change_years = average_retirement_age_new - average_retirement_age_original
                retirement_age_change_months = (retirement_age_change_years - int(retirement_age_change_years)) * 12
                retirement_age_change_days = (retirement_age_change_months - int(retirement_age_change_months)) * 30

                st.title(f"In this new scenario, you would be able to retire {int(abs(retirement_age_change_years))} years, {int(abs(retirement_age_change_months))} months, {int(abs(retirement_age_change_days))} days {'earlier' if retirement_age_change_years < 0 else 'later'}.")

                def create_scenario_comparison_net_worth_chart(ts_df_original, ts_df_new, original_user, new_user):
                    def prepare_data(ts_df, user, scenario):
                        data = {
                            'Year': ts_df['month'] // 12,
                            f'{scenario} Home Equity': ts_df['home_equity'],
                            f'{scenario} Emergency Fund': ts_df['emergency_fund'],
                        }
                        
                        for vehicle in user.investment_vehicles:
                            data[f'{scenario} Investment: {vehicle.name}'] = ts_df['investments'] * vehicle.ratio
                        
                        for purchase in user.major_purchases:
                            if purchase.consider_in_net_worth:
                                data[f'{scenario} Major Purchase: {purchase.item_name}'] = ts_df[f'major_purchase_{purchase.item_name}_value']
                        
                        return pd.DataFrame(data)

                    df_original = prepare_data(ts_df_original, original_user, 'Original')
                    df_new = prepare_data(ts_df_new, new_user, 'New')

                    # Merge dataframes
                    df = pd.merge(df_original, df_new, on='Year', suffixes=('_original', '_new'))
                    
                    # Create stacked bar chart
                    fig = go.Figure()
                    
                    bar_width = 0.35
                    
                    for column in df.columns:
                        if column != 'Year':
                            if column.startswith('Original'):
                                fig.add_trace(go.Bar(
                                    x=df['Year'] - bar_width/2,
                                    y=df[column],
                                    name=column,
                                    hoverinfo='name+y',
                                    width=bar_width,
                                    hovertemplate='%{y:,.0f}'
                                ))
                            elif column.startswith('New'):
                                fig.add_trace(go.Bar(
                                    x=df['Year'] + bar_width/2,
                                    y=df[column],
                                    name=column,
                                    hoverinfo='name+y',
                                    width=bar_width,
                                    hovertemplate='%{y:,.0f}'
                                ))
                    
                    fig.update_layout(
                        title='Net Worth Composition Comparison: Original vs New Scenario',
                        xaxis_title='Year',
                        yaxis_title='Amount (in $100s)',
                        barmode='stack',
                        legend_title='Components',
                        hovermode='x unified'
                    )
                    
                    # Update y-axis with scaled tickformat
                    fig.update_yaxes(
                        tickformat=',.0f',
                        tickprefix='$',
                        ticksuffix='',
                        title_text='Amount ($)',
                    )
                    max_y = 0
                    for column in df.columns:
                        if column != 'Year':
                            max_y = max(max_y, df[column].sum())
                    tick_vals = np.linspace(0, max_y)  # Create 6 evenly spaced tick values
                    fig.update_yaxes(
                    tickformat=',d',
                    tickvals=tick_vals,
                    ticktext=[f'{x/100:,.0f}' for x in tick_vals],
)
                    return fig
                # In the scenario analysis part of your Streamlit app:
                st.subheader("Net Worth Composition Comparison")
                scenario_comparison_chart = create_scenario_comparison_net_worth_chart(ts_df_original, ts_df_new, original_user, new_user)
                st.plotly_chart(scenario_comparison_chart)
                
                if original_user.owns_home or new_user.owns_home:
                    st.subheader("Comparison of Home Equity")
                    fig = go.Figure()
                    if original_user.owns_home:
                        fig.add_trace(go.Scatter(x=ts_df_original["month"], y=ts_df_original["home_equity"], mode='lines', name='Original Home Equity'))
                    if new_user.owns_home:
                        fig.add_trace(go.Scatter(x=ts_df_new["month"], y=ts_df_new["home_equity"], mode='lines', name='New Home Equity'))
                    fig.update_layout(title='Comparison of Home Equity', xaxis_title='Month', yaxis_title='Home Equity ($)')
                    st.plotly_chart(fig)

                # Display retirement age distribution
                st.subheader("Retirement Age Distribution")
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=retirement_ages_original, name='Original Scenario', opacity=0.7))
                fig.add_trace(go.Histogram(x=retirement_ages_new, name='New Scenario', opacity=0.7))
                fig.update_layout(title='Retirement Age Distribution', xaxis_title='Retirement Age', yaxis_title='Count', barmode='overlay')
                st.plotly_chart(fig)

                # Display raw data in expandable sections
                with st.expander("Raw Data for Original Scenario"):
                    st.write(ts_df_original)

                with st.expander("Raw Data for New Scenario"):
                    st.write(ts_df_new)

        else:
            st.error("Failed to load user profile.")
    else:
        st.error("User not logged in.")