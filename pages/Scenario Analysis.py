import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import scenarios
from FIRE import INVESTMENT_TYPES
from storage import load_user_profile

st.set_page_config(page_title="FIRESight - Scenario Analysis", page_icon="🔍", layout="wide")


# ======================
#  HELPER FUNCTIONS
# ======================
def format_currency(value):
    """Format numeric as USD."""
    try:
        return f"${value:,.0f}"
    except (TypeError, ValueError):
        return str(value)


def format_percentage(value):
    """Format numeric as percentage."""
    try:
        return f"{value:.1%}"
    except (TypeError, ValueError):
        return str(value)


def format_time_difference(years, months, days):
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days and not years:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    return ", ".join(parts) if parts else "less than a day"


def budget_frame(profile):
    rows = [{"name": b.get("name") or b.get("type"), "value": float(b.get("value", 0)),
             "frequency": b.get("frequency", "monthly")} for b in profile.get("budget_items", [])]
    return pd.DataFrame(rows, columns=["name", "value", "frequency"])


def band_traces(fig, results, start_age, label, color):
    bands = scenarios.net_worth_bands(results, (10, 50, 90))
    ages = start_age + (pd.Series(range(len(bands[50]))) + 1) / 12
    fig.add_trace(go.Scatter(x=ages, y=bands[90], line_color="rgba(0,0,0,0)", showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ages, y=bands[10], fill="tonexty", fillcolor=color.replace("1)", "0.15)"),
                             line_color="rgba(0,0,0,0)", name=f"{label}: 10th-90th percentile"))
    fig.add_trace(go.Scatter(x=ages, y=bands[50], line=dict(color=color, width=3), name=f"{label}: median"))


# ======================
#  MAIN SCENARIO APP
# ======================
def main():
    st.title("🔍 Scenario Analysis")
    st.write("Explore how changes to your financial plan could impact your journey to FIRE. "
             "Both plans run on the same simulated markets, so the difference you see comes from your change.")

    # Identify user
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        st.page_link("pages/Create Account and Log in.py", label="Log in or try a demo profile", icon="🔐")
        return

    user_data = load_user_profile(user_id)
    if not user_data:
        st.error("Failed to load user profile.")
        return

    changes = {}
    new_milestones = []

    # ----- UI: Income and Retirement -----
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Income")
        raise_pct = st.slider("Change all income by (%)", -50, 100, 0, step=5)
        st.caption("💡 Increasing your income is one of the most impactful ways to accelerate your FIRE journey.")
        if raise_pct:
            changes["income_multiplier"] = 1 + raise_pct / 100
        override_growth = st.checkbox("Override annual raises")
        if override_growth:
            changes["income_growth_percent"] = st.slider("Annual raise (%)", 0.0, 10.0, 3.0, step=0.5)
            st.caption("💡 Even small increases in annual income growth can have a significant impact over time.")

    with col2:
        st.subheader("Retirement Target")
        changes["post_retirement_expenses"] = st.number_input(
            "Post-Retirement Annual Expenses", min_value=0.0, step=1000.0,
            value=float(user_data.get("post_retirement_expenses", 0.0)))
        st.caption("💡 Lowering your post-retirement expenses can significantly reduce the amount you need to save.")
        changes["average_post_retirement_income"] = st.number_input(
            "Average Post-Retirement Annual Income", min_value=0.0, step=1000.0,
            value=float(user_data.get("average_post_retirement_income", 0.0)))
        changes["withdrawal_rate"] = st.slider(
            "Withdrawal Rate", 0.025, 0.06, float(user_data.get("withdrawal_rate", 0.04)), step=0.0025, format="%.4f")

    # ----- UI: Budget Items -----
    st.subheader("Budget Items")
    st.caption("💡 Regularly reviewing your budget can uncover additional savings opportunities. Edit values, add rows or delete rows.")
    original_budget = budget_frame(user_data)
    edited_budget = st.data_editor(
        original_budget, num_rows="dynamic", width="stretch", key="scenario_budget",
        column_config={
            "value": st.column_config.NumberColumn("value", min_value=0.0, step=10.0, format="$%.0f"),
            "frequency": st.column_config.SelectboxColumn("frequency", options=["weekly", "monthly", "annual"]),
        })
    edited_budget = edited_budget.dropna(subset=["name"])
    if not edited_budget.equals(original_budget):
        old = {r["name"]: r for r in original_budget.to_dict("records")}
        new = {r["name"]: r for r in edited_budget.to_dict("records")}
        changes["remove_budget_items"] = [n for n in old if n not in new]
        changes["budget_changes"] = {n: r["value"] for n, r in new.items() if n in old and r["value"] != old[n]["value"]}
        changes["new_budget_items"] = [{"name": n, "value": r["value"] or 0.0, "frequency": r["frequency"] or "monthly"}
                                       for n, r in new.items() if n not in old]

    # ----- UI: Investment Strategy -----
    st.subheader("Investment Strategy")
    alloc_cols = st.columns(3)
    allocation = {}
    for i, name in enumerate(INVESTMENT_TYPES):
        key = scenarios.ALLOCATION_KEYS[name]
        allocation[name] = alloc_cols[i % 3].slider(f"{name} (%)", 0.0, 100.0, float(user_data.get(key, 0.0)), step=1.0)
    total_allocation = sum(allocation.values())
    st.caption(f"Total: {total_allocation:.0f}% (rescaled to 100% when the scenario runs). "
               "💡 Diversifying your investment portfolio can help balance risk and potential returns.")
    if total_allocation > 0:
        changes["allocation"] = allocation

    # ----- UI: Big Moves -----
    st.subheader("Life Events")
    ev1, ev2, ev3, ev4 = st.columns(4)
    default_date = datetime.date.today().replace(year=datetime.date.today().year + 2)
    with ev1:
        if st.checkbox("Buy a home"):
            new_milestones.append({
                "date": st.date_input("Purchase date", default_date, key="home_date").isoformat(),
                "buy_a_house": True,
                "house_price": st.number_input("Price", 0.0, value=400000.0, step=10000.0),
                "down_payment": st.number_input("Down payment", 0.0, value=80000.0, step=5000.0),
                "mortgage_rate": st.number_input("Mortgage rate (%)", 0.0, 15.0, 6.0, step=0.125) / 100,
                "mortgage_term_years": st.selectbox("Term (years)", [30, 20, 15], key="home_term"),
                "property_tax_rate": st.number_input("Property tax (%)", 0.0, 5.0, 1.0, step=0.1) / 100,
            })
    with ev2:
        if st.checkbox("Major purchase"):
            purchase_type = st.selectbox("Paid with", ["cash", "finance"], key="mp_type")
            purchase = {
                "date": st.date_input("Date", default_date, key="mp_date").isoformat(),
                "major_expense": True,
                "item_name": st.text_input("What is it?", "Major Purchase", key="mp_name"),
                "total_cost": st.number_input("Total cost", 0.0, value=40000.0, step=1000.0, key="mp_cost"),
                "purchase_type": purchase_type,
            }
            if purchase_type == "finance":
                purchase["down_payment"] = st.number_input("Down payment", 0.0, value=8000.0, step=1000.0, key="mp_dp")
                purchase["loan_amount"] = purchase["total_cost"] - purchase["down_payment"]
                purchase["interest_rate"] = st.number_input("Interest rate (%)", 0.0, 30.0, 7.0, step=0.25, key="mp_rate")
                purchase["loan_term_months"] = st.number_input("Term (months)", 6, 360, 60, step=6, key="mp_term")
            new_milestones.append(purchase)
    with ev3:
        if st.checkbox("Windfall"):
            new_milestones.append({
                "date": st.date_input("Date", default_date, key="wf_date").isoformat(),
                "major_windfall": True,
                "windfall_amount": st.number_input("Amount", 0.0, value=50000.0, step=5000.0, key="wf_amt"),
            })
    with ev4:
        if st.checkbox("Move"):
            new_milestones.append({
                "date": st.date_input("Move date", default_date, key="mv_date").isoformat(),
                "change_location": True,
                "city": st.text_input("New city", "Lisbon", key="mv_city"),
                "moving_cost": st.number_input("Moving cost", 0.0, value=8000.0, step=500.0, key="mv_cost"),
                "expense_adjustment": "Manual adjustment",
                "manual_expense_adjustment": st.slider("Spending after the move (x)", 0.5, 2.0, 1.0, step=0.05),
            })
    st.caption("💡 Planning for big life events helps you stay on track toward your FIRE goals.")
    if new_milestones:
        changes["add_milestones"] = new_milestones

    # ----- UI: Economy & Simulation -----
    st.subheader("Simulation Parameters")
    p1, p2, p3, p4 = st.columns(4)
    changes["inflation"] = p1.slider("Inflation Rate", 0.0, 0.10, float(user_data.get("inflation", 0.03)), step=0.005, format="%.3f")
    changes["expenditure_growth_beyond_inflation"] = p2.slider(
        "Lifestyle creep (beyond inflation)", 0.0, 0.10,
        float(user_data.get("expenditure_growth_beyond_inflation", 0.0)), step=0.005, format="%.3f")
    st.caption("💡 Controlling lifestyle inflation can have a major impact on your savings rate and FIRE timeline.")
    changes["simulate_years"] = p3.slider("Simulation Years", 5, 50, int(user_data.get("simulate_years", 30)))
    num_simulations = p4.slider("Number of Simulations", 5, 200, int(user_data.get("num_simulations", 25)))
    changes["num_simulations"] = num_simulations
    baseline_data = {**user_data, "simulate_years": changes["simulate_years"], "num_simulations": num_simulations}

    # ==============================
    #  RUN SCENARIO BUTTON
    # ==============================
    if st.button("Run Scenario Analysis", type="primary"):
        try:
            with st.spinner("Running simulations..."):
                result = scenarios.compare(baseline_data, changes)
        except ValueError as e:
            st.error(str(e))
            return
        show_results(user_data, result)


def show_results(user_data, result):
    base, new = result["baseline"], result["scenario"]
    start_age = user_data.get("age", 0)
    horizon_age = start_age + result["profile"]["simulate_years"]

    # ======================
    #  DISPLAY RESULTS
    # ======================
    st.header("Scenario Analysis Results")

    orig_age = base["median_retirement_age"] or horizon_age
    new_age = new["median_retirement_age"] or horizon_age
    retirement_age_change = new_age - orig_age
    total_days = abs(int(retirement_age_change * 365.25))
    years, remaining_days = divmod(total_days, 365)
    months, days = divmod(remaining_days, 30)
    if abs(retirement_age_change) < 1 / 24:
        st.markdown("### This scenario leaves your median retirement age about where it is.")
    else:
        st.markdown(f"### This scenario would {'delay' if retirement_age_change > 0 else 'accelerate'} "
                    f"your retirement by {format_time_difference(years, months, days)}.")

    colA, colB, colC = st.columns(3)
    colA.metric("Original Retirement Age (median)", f"{orig_age:.1f}" if base["median_retirement_age"] else f"> {horizon_age:.0f}")
    colB.metric("New Retirement Age (median)", f"{new_age:.1f}" if new["median_retirement_age"] else f"> {horizon_age:.0f}",
                delta=f"{retirement_age_change:+.1f} yrs", delta_color="inverse")
    colC.metric("Runs reaching FI", f"{new['success_rate']:.0%}",
                delta=f"{(new['success_rate'] - base['success_rate']) * 100:+.0f} pts")

    # Net Worth Comparison
    st.subheader("Net Worth Comparison")
    fig = go.Figure()
    band_traces(fig, result["baseline_results"], start_age, "Original", "rgba(99, 110, 250, 1)")
    band_traces(fig, result["scenario_results"], start_age, "Scenario", "rgba(255, 107, 107, 1)")
    fig.update_layout(xaxis_title="Age", yaxis_title="Net Worth ($)", hovermode="x unified",
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")

    # Retirement Age Distribution
    st.subheader("Retirement Age Distribution")
    fig = go.Figure()
    if base["retirement_ages"]:
        fig.add_trace(go.Histogram(x=base["retirement_ages"], name="Original Scenario", opacity=0.7))
    if new["retirement_ages"]:
        fig.add_trace(go.Histogram(x=new["retirement_ages"], name="New Scenario", opacity=0.7))
    fig.update_layout(xaxis_title="Retirement Age", yaxis_title="Count", barmode="overlay")
    st.plotly_chart(fig, width="stretch")

    # Key Metrics Comparison
    st.subheader("Key Metrics Comparison")
    metrics = [
        ("First-year income", base["annual_income"], new["annual_income"], format_currency),
        ("First-year spending", base["annual_expenses"], new["annual_expenses"], format_currency),
        ("First-year taxes", base["annual_taxes"], new["annual_taxes"], format_currency),
        ("Savings rate", base["savings_rate"], new["savings_rate"], format_percentage),
        ("FIRE number (today's dollars)", base["fire_number"], new["fire_number"], format_currency),
        ("Median final net worth", base["median_final_net_worth"], new["median_final_net_worth"], format_currency),
        ("10th percentile final net worth", base["p10_final_net_worth"], new["p10_final_net_worth"], format_currency),
    ]
    table = pd.DataFrame([{"Metric": m, "Original": f(o), "Scenario": f(n),
                           "Change": f(n - o) if f is format_currency else f"{(n - o) * 100:+.1f} pts"}
                          for m, o, n, f in metrics])
    st.dataframe(table, hide_index=True, width="stretch")

    # Scenario Summary
    st.subheader("Scenario Summary")
    nw_change = ((new["median_final_net_worth"] - base["median_final_net_worth"]) / abs(base["median_final_net_worth"]) * 100
                 if abs(base["median_final_net_worth"]) > 0.01 else 0)
    st.markdown(f"""
**Highlights:**
1. Median retirement age moves by **{abs(retirement_age_change):.1f} years** ({'later' if retirement_age_change > 0 else 'earlier'}).
2. Median final net worth is expected to {'increase' if nw_change > 0 else 'decrease'} by **{abs(nw_change):.1f}%**.
3. Savings rate changes from **{format_percentage(base['savings_rate'])}** to **{format_percentage(new['savings_rate'])}**.
4. **{new['runs_reaching_fi']} of {new['runs']}** simulated futures reach financial independence, versus {base['runs_reaching_fi']} before.
""")
    st.caption(f"Both plans ran {new['runs']} simulations on shared random seed {result['seed']}. "
               "These projections depend on your scenario inputs. Revisit and update them as your situation changes.")


if __name__ == "__main__":
    main()
