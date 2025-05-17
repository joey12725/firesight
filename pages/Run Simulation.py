import streamlit as st
import datetime
import os
import json
import boto3
from boto3.dynamodb.conditions import Key
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd

# DynamoDB configuration (as in your original code)
try:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('firesight-users')
except:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2',
                              aws_access_key_id=AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
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
    """
    Runs the Monte Carlo simulation, then shows enhanced charts & analytics
    of net worth, retirement age, distribution percentiles, etc.
    """
    # Run the simulation
    avg_ts, average_retirement_age, stdev_retirement_age, results = run_monte_carlo_simulation(user_data)
    num_sims = len(results)
    months = user_data.get("simulate_years", 10) * 12

    st.title("Simulation Results")

    # 1) Retirement Age Analysis
    st.header("Retirement Age Analysis")

    if average_retirement_age is not None:
        st.markdown(f"**Average Retirement Age**: {average_retirement_age:.2f}")
        st.markdown(f"**Retirement Age Std Dev**: {stdev_retirement_age:.2f}")
    else:
        st.warning("No retirement ages were determined in the simulations (possibly never reached retirement).")

    # (Optional) If you'd collected raw retirement ages in run_monte_carlo_simulation, you could plot them here.
    retirement_ages = []  # Currently no raw distribution provided in the original code
    if len(retirement_ages) > 0:
        fig = px.histogram(retirement_ages, nbins=20, labels={'value': 'Retirement Age'}, title="Retirement Age Distribution")
        st.plotly_chart(fig, use_container_width=True)
        for percentile in [10, 25, 50, 75, 90]:
            val = np.percentile(retirement_ages, percentile)
            st.write(f"{percentile}th percentile retirement age: {val:.2f}")
    else:
        st.info("No detailed retirement age distribution data to plot.")

    # 2) Net Worth Over Time
    st.header("Net Worth Over Time")

    # Convert 'results' (list of DataFrames) to a NumPy array for fan chart
    networth_matrix = []
    for df in results:
        df_sorted = df.sort_values(by='month')
        networth_vals = df_sorted['net_worth'].values

        # If the simulation's DataFrame is shorter than 'months', pad it with the last value.
        if len(networth_vals) < months:
            networth_vals = np.concatenate([
                networth_vals,
                np.full(months - len(networth_vals), networth_vals[-1])
            ])
        networth_matrix.append(networth_vals[:months])

    if len(networth_matrix) == 0:
        st.warning("No simulation results to display.")
        return

    networth_matrix = np.array(networth_matrix)  # shape => (num_sims, months)

    # Compute percentile lines: 5, 25, 50, 75, 95
    p5 = np.percentile(networth_matrix, 5, axis=0)
    p25 = np.percentile(networth_matrix, 25, axis=0)
    p50 = np.percentile(networth_matrix, 50, axis=0)
    p75 = np.percentile(networth_matrix, 75, axis=0)
    p95 = np.percentile(networth_matrix, 95, axis=0)

    # Create an interactive Plotly fan chart
    fig_fan = go.Figure()
    months_axis = np.arange(months)

    # Add fill for 5-95 percentile band
    fig_fan.add_trace(go.Scatter(
        x=months_axis,
        y=p95,
        line_color='rgba(0,0,0,0)',
        showlegend=False,
        name='95th Percentile'
    ))
    fig_fan.add_trace(go.Scatter(
        x=months_axis,
        y=p5,
        fill='tonexty',
        fillcolor='rgba(0, 100, 200, 0.2)',
        line_color='rgba(0,0,0,0)',
        showlegend=True,
        name='5th - 95th Percentile'
    ))

    # Add fill for 25-75 percentile band
    fig_fan.add_trace(go.Scatter(
        x=months_axis,
        y=p75,
        line_color='rgba(0,0,0,0)',
        showlegend=False,
        name='75th Percentile'
    ))
    fig_fan.add_trace(go.Scatter(
        x=months_axis,
        y=p25,
        fill='tonexty',
        fillcolor='rgba(0, 200, 100, 0.2)',
        line_color='rgba(0,0,0,0)',
        showlegend=True,
        name='25th - 75th Percentile'
    ))

    # Add the median line
    fig_fan.add_trace(go.Scatter(
        x=months_axis,
        y=p50,
        line_color='blue',
        name='Median (50th Percentile)'
    ))

    fig_fan.update_layout(
        title="Net Worth Over Time (Fan Chart)",
        xaxis_title="Month",
        yaxis_title="Net Worth",
        hovermode="x unified"
    )

    st.plotly_chart(fig_fan, use_container_width=True)

    # 3) Compare "Average" to "Best" and "Worst" single simulations
    final_nw = [df['net_worth'].iloc[-1] for df in results]
    best_idx = np.argmax(final_nw)
    worst_idx = np.argmin(final_nw)
    df_best = results[best_idx].sort_values(by='month')
    df_worst = results[worst_idx].sort_values(by='month')
    df_avg = avg_ts.sort_values(by='month')

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(
        x=df_best['month'], y=df_best['net_worth'],
        mode='lines', name='Best Case',
        line=dict(color='green')
    ))
    fig_comp.add_trace(go.Scatter(
        x=df_worst['month'], y=df_worst['net_worth'],
        mode='lines', name='Worst Case',
        line=dict(color='red')
    ))
    fig_comp.add_trace(go.Scatter(
        x=df_avg['month'], y=df_avg['net_worth'],
        mode='lines', name='Average',
        line=dict(color='blue', width=3)
    ))
    fig_comp.update_layout(
        title="Best, Worst, and Average Simulation",
        xaxis_title="Month",
        yaxis_title="Net Worth",
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    # 4) Final Net Worth Distribution (Histogram)
    st.header("Final Net Worth Distribution")
    fig_hist = px.histogram(final_nw, nbins=20,
                            labels={'value': 'Final Net Worth'},
                            title="Histogram: Final Net Worth After Simulation")
    st.plotly_chart(fig_hist, use_container_width=True)

    # Show percentile stats for final net worth
    for p in [10, 25, 50, 75, 90]:
        val = np.percentile(final_nw, p)
        st.write(f"{p}th percentile: ${val:,.2f}")

    # 5) Show raw average time series data
    st.header("Average Simulation Time Series")
    st.write("Below is the *average* across all simulations, by month:")
    st.dataframe(avg_ts)

    # 6) Show one random simulation’s data
    st.header("Sample Single Simulation")
    random_index = np.random.randint(0, num_sims)
    st.markdown(f"Showing simulation number **{random_index}** out of {num_sims} runs.")
    st.dataframe(results[random_index])

    st.success("Analysis complete! Scroll up to review the charts and stats.")

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
