import streamlit as st
import datetime
import os
import uuid
import json
import matplotlib.pyplot as plt

cwd = os.getcwd()

st.set_page_config(page_title="FIRE Simulator", page_icon="🔥")

# Adjust the path to your FIRE.py file
exec(open(os.path.join(cwd, "FIRE.py")).read())

def load_user_file():
    uploaded_file = st.file_uploader("Upload User Configuration", type="json")
    if uploaded_file is not None:
        return json.load(uploaded_file)
    return None

def generate_repeating_field_group(keys, group_id, default_values=None):
    if f"rows_{group_id}" not in st.session_state:
        st.session_state[f"rows_{group_id}"] = []

    rows_collection = []

    def add_row():
        element_id = uuid.uuid4()
        st.session_state[f"rows_{group_id}"].append(str(element_id))

    def remove_row(row_id):
        st.session_state[f"rows_{group_id}"].remove(str(row_id))

    def generate_row(row_id, defaults=None):
        row_container = st.container()
        row_columns = row_container.columns((3, 1))
        field_group = {}

        for key, value in keys.items():
            field_type = value["type"]
            default_value = defaults[key] if defaults and key in defaults else value["default"]

            if field_type == int:
                field_group[key] = row_columns[0].number_input(key, value=int(default_value), step=1, key=f"{key}_{row_id}_{group_id}")
            elif field_type == float:
                field_group[key] = row_columns[0].number_input(key, value=float(default_value), format="%.2f", key=f"{key}_{row_id}_{group_id}")
            elif field_type == str:
                field_group[key] = row_columns[0].text_input(key, value=str(default_value), key=f"{key}_{row_id}_{group_id}")
            elif field_type == "date":
                field_group[key] = row_columns[0].date_input(key, value=datetime.date.fromisoformat(default_value) if isinstance(default_value, str) else default_value, key=f"{key}_{row_id}_{group_id}")
            elif field_type == "paragraph":
                field_group[key] = row_columns[0].text_area(key, value=str(default_value), key=f"{key}_{row_id}_{group_id}")
            elif field_type == "choice":
                choices = value["choices"]
                field_group[key] = row_columns[0].selectbox(key, options=choices, index=choices.index(default_value), key=f"{key}_{row_id}_{group_id}")
            else:
                raise ValueError(f"Invalid field type: {field_type}")

        row_columns[1].button("🗑️", key=f"del_{row_id}_{group_id}", on_click=remove_row, args=[row_id])
        return field_group

    menu = st.columns(2)
    with menu[0]:
        st.button("Add Item", on_click=add_row, key=f"add_item_{group_id}")

    for row in st.session_state[f"rows_{group_id}"]:
        defaults = None
        if default_values and row in default_values:
            defaults = default_values[row]
        row_data = generate_row(row, defaults)
        rows_collection.append(row_data)

    return rows_collection

def create_user(user_data=None):
    st.title("FIRE Simulator🔥")
    
    if user_data:
        age = user_data.get("age", 22)
        income = user_data.get("income", 95000.0)
        income_growth = user_data.get("income_growth", 0.03)
        risk_tolerance = user_data.get("risk_tolerance", 0.5)
        expenditure_growth_beyond_inflation = user_data.get("expenditure_growth_beyond_inflation", 0.03)
        current_savings = user_data.get("current_savings", 25000.0)
        max_401k_contribution = user_data.get("max_401k_contribution", True)
        max_ira_contribution = user_data.get("max_ira_contribution", True)
        max_hsa_contribution = user_data.get("max_hsa_contribution", False)
        other_tax_sheltered_income = user_data.get("other_tax_sheltered_income", 0.0)
        married = user_data.get("married", True)
        emergency_fund_target = user_data.get("emergency_fund_target", 10000.0)
        inflation = user_data.get("inflation", 0.03)
        average_life_event_cost = user_data.get("average_life_event_cost", 1000.0)
        average_life_event_stdev = user_data.get("average_life_event_stdev", 500.0)
        average_life_event_frequency = user_data.get("average_life_event_frequency", 1)
        budget_items_data = user_data.get("budget_items", {})
        investment_vehicles_data = user_data.get("investment_vehicles", {})
        major_expenses_data = user_data.get("major_expenses", {})
        home_purchase_data = user_data.get("home_purchase", {})
        location_change_data = user_data.get("location_change", {})
        post_retirement_expenses = user_data.get("post_retirement_expenses", 0.0)
        average_post_retirement_income = user_data.get("average_post_retirement_income", 0.0)
        simulate_years = user_data.get("simulate_years", 10)
    else:
        age = 22
        income = 95000.0
        income_growth = 0.03
        risk_tolerance = 0.5
        expenditure_growth_beyond_inflation = 0.03
        current_savings = 25000.0
        max_401k_contribution = True
        max_ira_contribution = True
        max_hsa_contribution = False
        other_tax_sheltered_income = 0.0
        married = True
        emergency_fund_target = 10000.0
        inflation = 0.03
        average_life_event_cost = 1000.0
        average_life_event_stdev = 500.0
        average_life_event_frequency = 1
        budget_items_data = {}
        investment_vehicles_data = {}
        major_expenses_data = {}
        home_purchase_data = {}
        location_change_data = {}
        post_retirement_expenses = 0.0
        average_post_retirement_income = 0.0
        simulate_years = 10

    # Get user input
    age = st.number_input("Age", min_value=0, value=age, step=1)
    income = st.number_input("Income", min_value=0.0, value=income, step=1000.0)
    income_growth = st.slider("Income Growth", min_value=0.0, max_value=0.2, value=income_growth, step=0.01)
    risk_tolerance = st.slider("Risk Tolerance", min_value=0.0, max_value=1.0, value=risk_tolerance, step=0.01)
    expenditure_growth_beyond_inflation = st.slider("Expenditure Growth Beyond Inflation", min_value=0.0, max_value=0.1, value=expenditure_growth_beyond_inflation, step=0.01)
    current_savings = st.number_input("Current Savings", min_value=0.0, value=current_savings, step=1000.0)
    max_401k_contribution = st.checkbox("Max 401k Contribution", value=max_401k_contribution)
    max_ira_contribution = st.checkbox("Max IRA Contribution", value=max_ira_contribution)
    max_hsa_contribution = st.checkbox("Max HSA Contribution", value=max_hsa_contribution)
    other_tax_sheltered_income = st.number_input("Other Tax Sheltered Income", min_value=0.0, value=other_tax_sheltered_income, step=1000.0)
    married = st.checkbox("Married", value=married)
    emergency_fund_target = st.number_input("Emergency Fund Target", min_value=0.0, value=emergency_fund_target, step=1000.0)
    inflation = st.slider("Inflation", min_value=0.0, max_value=0.1, value=inflation, step=0.01)
    average_life_event_cost = st.number_input("Average Life Event Cost", min_value=0.0, value=average_life_event_cost, step=1000.0)
    average_life_event_stdev = st.number_input("Life Event Standard Deviation", min_value=0.0, value=average_life_event_stdev, step=1000.0)
    average_life_event_frequency = st.slider("Average Life Events per year", min_value=0, max_value=10, value=average_life_event_frequency, step=1)
    
    st.subheader("Budget Items")
    budget_item_keys = {
        "name": {"type": str, "default": ""},
        "value": {"type": int, "default": 2000},
        "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]}
    }
    budget_items = generate_repeating_field_group(budget_item_keys, "budget", budget_items_data)
    
    st.subheader("Investment Vehicles")
    investment_vehicle_keys = {
        "name": {"type": str, "default": "S&P 500"},
        "annual_returns": {"type": float, "default": 0.1026},
        "standard_deviation": {"type": float, "default": 0.1532},
        "ratio": {"type": float, "default": 1.0}
    }
    investment_vehicles = generate_repeating_field_group(investment_vehicle_keys, "investment", investment_vehicles_data)
    st.write("Note: The ratios of all investment vehicles must add up to 1.")
    
    st.subheader("Major Expenses")
    major_expense_keys = {
        "name": {"type": str, "default": ""},
        "cost": {"type": int, "default": 0.0},
        "date": {"type": "date", "default": datetime.date.today()}
    }
    major_expenses = generate_repeating_field_group(major_expense_keys, "major_expense", major_expenses_data)
    
    home_purchase = st.checkbox("Plan to Purchase a Home", value=bool(home_purchase_data))
    if home_purchase:
        st.subheader("Home Purchase Details")
        home_purchase_date = st.date_input("Home Purchase Date", value=datetime.date.fromisoformat(home_purchase_data.get("date", "2025-01-01")) if "date" in home_purchase_data else datetime.date(2025, 1, 1), min_value=datetime.date.today())
        home_purchase_price = st.number_input("Home Purchase Price", min_value=0.0, value=home_purchase_data.get("price", 300000.0), step=10000.0)
        down_payment = st.number_input("Down Payment", min_value=0.0, value=home_purchase_data.get("down_payment", 60000.0), step=1000.0)
        property_tax = st.number_input("Property Tax", min_value=0.0, max_value=0.5, value=home_purchase_data.get("property_tax", 0.02), step=0.005)
        mortgage_rate = st.slider("Mortgage Rate", min_value=0.0, max_value=0.1, value=home_purchase_data.get("mortgage_rate", 0.04), step=0.001)
        mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=home_purchase_data.get("mortgage_term_years", 30), step=1)
        pay_off_mortgage_before_retirement = st.checkbox("Pay Off Mortgage Before Retirement", value=home_purchase_data.get("pay_off_before_retirement", False))
    
    location_change = st.checkbox("Plan to Change Location (domestic only)", value=bool(location_change_data))
    if location_change:
        st.subheader("Location Change Details")
        location_change_date = st.date_input("Location Change Date", value=datetime.date.fromisoformat(location_change_data.get("date", "2025-01-01")) if "date" in location_change_data else datetime.date(2025, 1, 1), min_value=datetime.date.today())
        location_change_moving_cost = st.number_input("Moving Cost", min_value=0.0, value=location_change_data.get("moving_cost", 5000.0), step=1000.0)
        location_change_col_adjustment = st.slider("Cost of Living Adjustment", min_value=0.0, max_value=2.0, value=location_change_data.get("col_adjustment", 1.0), step=0.01)
        location_change_state_income_tax = st.number_input("State Income Tax", min_value=0.0, value=location_change_data.get("state_income_tax", 0.0), step=0.01)
        location_change_property_tax = st.number_input("Property Tax", min_value=0.0, value=location_change_data.get("property_tax", 0.0), step=0.01)
    
    post_retirement_expenses = st.number_input("Post Retirement Expenses", min_value=0.0, value=post_retirement_expenses, step=1000.0)
    average_post_retirement_income = st.number_input("Average Post Retirement Income (not including investments)", min_value=0.0, value=average_post_retirement_income, step=1000.0)
    simulate_years = st.slider("Simulation Years", min_value=1, max_value=50, value=simulate_years, step=1)
    
    if st.button("Run Simulation"):
        user = User()
        user.age = age
        user.income = income
        user.risk_tolerance = risk_tolerance
        user.expenditure_growth_beyond_inflation = expenditure_growth_beyond_inflation
        user.current_savings = current_savings
        user.max_401k_contribution = max_401k_contribution
        user.max_ira_contribution = max_ira_contribution
        user.max_hsa_contribution = max_hsa_contribution
        user.other_tax_sheltered_income = other_tax_sheltered_income
        user.married = married
        user.emergency_fund_target = emergency_fund_target
        user.inflation = inflation
        user.average_life_event_cost = average_life_event_cost
        user.average_life_event_stdev = average_life_event_stdev
        user.average_life_event_frequency = average_life_event_frequency
        user.post_retirement_expenses = post_retirement_expenses
        user.average_post_retirement_income = average_post_retirement_income
        user.income_growth = income_growth
        
        for budget_item in budget_items:
            formatted_budget_item = {
                "name": budget_item["name"],
                "value": budget_item["value"],
                "frequency": budget_item["frequency"]
            }
            user.add_budget_item(formatted_budget_item)
        
        ratio_sum = sum([investment_vehicle["ratio"] for investment_vehicle in investment_vehicles])
        if ratio_sum != 1:
            st.error("The ratios of investment vehicles must add up to 1.")
        
        for investment_vehicle in investment_vehicles:
            user.add_invstment_vehicle(investment_vehicle["name"], investment_vehicle["annual_returns"], investment_vehicle["standard_deviation"], investment_vehicle["ratio"])
        
        for major_expense in major_expenses:
            user.add_major_expense(major_expense["name"], major_expense["cost"], major_expense["date"])
        
        if home_purchase:
            user.home_purchase_date = home_purchase_date
            user.home_purchase_price = home_purchase_price
            user.down_payment = down_payment
            user.mortgage_rate = mortgage_rate
            user.mortgage_term_years = mortgage_term_years
            user.pay_off_mortgage_before_retirement = pay_off_mortgage_before_retirement
            user.property_tax = property_tax
        
        if location_change:
            user.location_change = True
            user.location_change_date = location_change_date
            user.location_change_moving_costs = location_change_moving_cost
            user.location_col_adjustment = location_change_col_adjustment
            user.location_property_tax_adjustment = location_change_property_tax
            user.location_state_income_tax_adjustment = location_change_state_income_tax
        
        st.success("Running Simulation...")
        user_data = {
            "age": user.age,
            "income": user.income,
            "income_growth": user.income_growth,
            "risk_tolerance": user.risk_tolerance,
            "expenditure_growth_beyond_inflation": user.expenditure_growth_beyond_inflation,
            "current_savings": user.current_savings,
            "max_401k_contribution": user.max_401k_contribution,
            "max_ira_contribution": user.max_ira_contribution,
            "max_hsa_contribution": user.max_hsa_contribution,
            "other_tax_sheltered_income": user.other_tax_sheltered_income,
            "married": user.married,
            "emergency_fund_target": user.emergency_fund_target,
            "inflation": user.inflation,
            "average_life_event_cost": user.average_life_event_cost,
            "average_life_event_stdev": user.average_life_event_stdev,
            "average_life_event_frequency": user.average_life_event_frequency,
            "budget_items": [{"name": item["name"], "value": item["value"], "frequency": item["frequency"]} for item in budget_items],
            "investment_vehicles": [{"name": vehicle["name"], "annual_returns": vehicle["annual_returns"], "standard_deviation": vehicle["standard_deviation"], "ratio": vehicle["ratio"]} for vehicle in investment_vehicles],
            "major_expenses": [{"name": expense["name"], "cost": expense["cost"], "date": str(expense["date"])} for expense in major_expenses],
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
                "state_income_tax": location_change_state_income_tax if location_change else None,
                "property_tax": location_change_property_tax if location_change else None,
            },
            "post_retirement_expenses": post_retirement_expenses,
            "average_post_retirement_income": average_post_retirement_income,
            "simulate_years": simulate_years
        }
        
        user_json = json.dumps(user_data, indent=4)
        st.download_button('Download User Configuration', user_json, file_name='user.json', mime='application/json')
