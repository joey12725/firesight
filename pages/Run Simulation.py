import streamlit as st
import datetime
import os
import json
import boto3
from boto3.dynamodb.conditions import Key
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

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

def display_results(user_data):
    ts_df, average_retirement_age, stdev_retirement_age, all_time_series, retirement_ages, user = run_simulation_local(user_data)

    num_simulations = len(all_time_series)
    simulate_years = user_data['simulate_years']

    if average_retirement_age is None or stdev_retirement_age is None:
        st.error("The simulation couldn't determine valid retirement ages. Please adjust your parameters and try again.")
        return

    bottom_range = round(average_retirement_age - stdev_retirement_age, 1)
    top_range = round(average_retirement_age + stdev_retirement_age, 1)
    fire_number = int(round((user_data["post_retirement_expenses"] - user_data["average_post_retirement_income"])/user.retirement_income_ratio, -4))
    st.title(f"Your Estimated Age To Reach Your FIRE Number of {fire_number} is between :orange[{round(bottom_range)}] and :orange[{round(top_range)}] years old")
    st.title(f"We ran {num_simulations} simulations of {simulate_years} years. Here are the results:")

    # Retirement age distribution
    valid_retirement_ages = [age for age in retirement_ages if age is not None]
    
    if valid_retirement_ages:
        percentiles = [0, 10, 25, 50, 75, 90, 100]
        retirement_age_percentiles = np.percentile(valid_retirement_ages, percentiles)

        st.subheader("Retirement Age Distribution")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Key retirement age percentiles:")
            for p in [25, 50, 75]:
                age = np.percentile(valid_retirement_ages, p)
                st.metric(f"{p}th percentile", f"{age:.1f} years")

        # Graph for retirement age by percentile
        with col2:
            fig = go.Figure(data=[go.Scatter(x=percentiles, y=retirement_age_percentiles, mode='lines+markers')])
            fig.update_layout(title='Retirement Age by Percentile',
                              xaxis_title='Percentile',
                              yaxis_title='Retirement Age')
            st.plotly_chart(fig)
    else:
        st.warning("No valid retirement ages were found in the simulations.")

    # Visualize all simulations
    st.subheader(f"Net Worth Projections")
    fig = go.Figure()
    for ts in all_time_series:
        fig.add_trace(go.Scatter(x=ts['month'], y=ts['net_worth'], mode='lines', opacity=0.1, line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=ts_df['month'], y=ts_df['net_worth'], mode='lines', name='Average', line=dict(color='red', width=2)))
    fig.update_layout(title='Net Worth Projections',
                      xaxis_title='Months',
                      yaxis_title='Net Worth')
    st.plotly_chart(fig)

    # Visualize best and worst case scenarios
    st.subheader("Best and Worst Case Scenarios")
    best_case = max(all_time_series, key=lambda x: x['net_worth'].iloc[-1])
    worst_case = min(all_time_series, key=lambda x: x['net_worth'].iloc[-1])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=best_case['month'], y=best_case['net_worth'], mode='lines', name='Best Case', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=worst_case['month'], y=worst_case['net_worth'], mode='lines', name='Worst Case', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=ts_df['month'], y=ts_df['net_worth'], mode='lines', name='Average', line=dict(color='blue')))
    fig.update_layout(title='Best, Worst, and Average Cases',
                      xaxis_title='Months',
                      yaxis_title='Net Worth')
    st.plotly_chart(fig)

    st.write(f"Best case final net worth: ${best_case['net_worth'].iloc[-1]:,.2f}")
    st.write(f"Worst case final net worth: ${worst_case['net_worth'].iloc[-1]:,.2f}")

    def create_stacked_net_worth_chart(ts_df, user):
        # Prepare data for stacking
        data = {
            'Year': ts_df['month'] // 12,
            'Home Equity': ts_df['home_equity'],
            'Emergency Fund': ts_df['emergency_fund'],
        }
        
        # Add individual investment vehicles
        for vehicle in user.investment_vehicles:
            data[f'Investment: {vehicle.name}'] = ts_df['investments'] * vehicle.ratio
        
        # Add major purchases
        for purchase in user.major_purchases:
            if purchase.consider_in_net_worth:
                data[f'Major Purchase: {purchase.item_name}'] = ts_df[f'major_purchase_{purchase.item_name}_value']
        
        # Create DataFrame
        df = pd.DataFrame(data)
        df = df.groupby('Year').last().reset_index()  # Get last value for each year
        
        # Create stacked bar chart
        fig = go.Figure()
        
        for column in df.columns:
            if column != 'Year':
                fig.add_trace(go.Bar(
                    x=df['Year'],
                    y=df[column],
                    name=column,
                    hoverinfo='name+y'
                ))
        
        fig.update_layout(
            title='Net Worth Composition Over Time',
            xaxis_title='Year',
            yaxis_title='Amount ($)',
            barmode='stack',
            legend_title='Components',
            hovermode='x unified'
        )
        
        return fig

    # In the main Streamlit app:
    st.subheader("Net Worth Composition Over Time")
    net_worth_chart = create_stacked_net_worth_chart(ts_df, user)
    st.plotly_chart(net_worth_chart)

    if user.home_purchase_date is not None:
        st.subheader("Your Average Home Equity")
        df_home_equity = ts_df[["home_equity_value_with_growth", "month"]]
        st.line_chart(df_home_equity.set_index("month"))

    # Budget visualization (at the bottom)
    if len(list(user.budget.keys())) > 1:
        st.subheader("Your Monthly Budget Breakdown")
        budget = user.budget
        categories = list(budget.keys())
        values = [budget[category]["value"] if budget[category]["frequency"] == "monthly" else budget[category]["value"]/12 if budget[category]["frequency"] == "annual" else budget[category]["value"]*4.33 for category in categories]
        
        fig = go.Figure(data=[go.Pie(labels=categories, values=values, hole=.3)])
        fig.update_layout(title_text=f"Total Monthly Budget: ${sum(values):,.2f}")
        st.plotly_chart(fig)

    st.subheader("Here is the raw data for your average simulation:")
    st.write(ts_df)


if __name__ == "__main__":
    # Assume user_id is stored in session state after logging in
    user_id = st.session_state.get('user_id')
    if user_id:
        user_data = load_user_profile(user_id)
        if user_data:
            if st.button("Run Updated Simulation"):
                display_results(user_data)
        else:
            st.error("Failed to load user profile.")
    else:
        st.error("User not logged in.")
