import streamlit as st
import datetime
import os
import uuid
import json
import matplotlib.pyplot as plt

cwd = os.getcwd()

st.set_page_config(page_title="FIRE Simulator", page_icon="🔥")

exec(open(cwd + "/FIRE.py").read())


def generate_repeating_field_group(keys, group_id):
    if f"rows_{group_id}" not in st.session_state:
        st.session_state[f"rows_{group_id}"] = []

    rows_collection = []

    def add_row():
        element_id = uuid.uuid4()
        st.session_state[f"rows_{group_id}"].append(str(element_id))

    def remove_row(row_id):
        st.session_state[f"rows_{group_id}"].remove(str(row_id))

    def generate_row(row_id):
        row_container = st.container()
        row_columns = row_container.columns((3, 1))
        field_group = {}

        for key, value in keys.items():
            field_type = value["type"]
            default_value = value["default"]

            if field_type == int:
                field_group[key] = row_columns[0].number_input(key, value=int(default_value), step=1, key=f"{key}_{row_id}_{group_id}")
            elif field_type == float:
                field_group[key] = row_columns[0].number_input(key, value=float(default_value), format="%.2f", key=f"{key}_{row_id}_{group_id}")
            elif field_type == str:
                field_group[key] = row_columns[0].text_input(key, value=str(default_value), key=f"{key}_{row_id}_{group_id}")
            elif field_type == "date":
                field_group[key] = row_columns[0].date_input(key, value=datetime.date.today(), key=f"{key}_{row_id}_{group_id}")
            elif field_type == "paragraph":
                field_group[key] = row_columns[0].text_area(key, value=str(default_value), key=f"{key}_{row_id}_{group_id}")
            elif field_type == "choice":
                choices = value["choices"]
                field_group[key] = row_columns[0].selectbox(key, options=choices, key=f"{key}_{row_id}_{group_id}")
            else:
                raise ValueError(f"Invalid field type: {field_type}")

        row_columns[1].button("🗑️", key=f"del_{row_id}_{group_id}", on_click=remove_row, args=[row_id])
        return field_group

    menu = st.columns(2)
    with menu[0]:
        st.button("Add Item", on_click=add_row, key=f"add_item_{group_id}")

    for row in st.session_state[f"rows_{group_id}"]:
        row_data = generate_row(row)
        rows_collection.append(row_data)

    return rows_collection

    
    
def create_user():
    st.title("FIRE Simulator🔥")
    #set page title and favicon
    # Get user input
    age = st.number_input("Age", min_value=0, value=22, step=1)
    income = st.number_input("Income", min_value=0.0, value=95000.0, step=1000.0)
    risk_tolerance = st.slider("Risk Tolerance", min_value=0.0, max_value=1.0, value=0.5, step=0.01)
    expenditure_growth_beyond_inflation = st.slider("Expenditure Growth Beyond Inflation", min_value=0.0, max_value=0.1, value=0.03, step=0.01)
    current_savings = st.number_input("Current Savings", min_value=0.0, value=25000.0, step=1000.0)
    max_401k_contribution = st.checkbox("Max 401k Contribution", value=True)
    max_ira_contribution = st.checkbox("Max IRA Contribution", value=True)
    max_hsa_contribution = st.checkbox("Max HSA Contribution", value=False)
    other_tax_sheltered_income = st.number_input("Other Tax Sheltered Income", min_value=0.0, value=0.0, step=1000.0)
    married = st.checkbox("Married", value=True)
    emergency_fund_target = st.number_input("Emergency Fund Target", min_value=0.0, value=10000.0, step=1000.0)
    inflation = st.slider("Inflation", min_value=0.0, max_value=0.1, value=0.03, step=0.01)
    average_life_event_cost = st.number_input("Average Life Event Cost", min_value=0.0, value=1000.0, step=1000.0)
    average_life_event_stdev = st.number_input("Life Event Standard Deviation", min_value=0.0, value=500.0, step=1000.0)
    average_life_event_frequency = st.slider("Average Life Events per year", min_value=0, max_value=10, value=1, step=1)
    st.subheader("Budget Items")
    # Budget items have a name, value, and frequency
    budget_item_keys = {
        "name": {"type": str, "default": ""},
        "value": {"type": int, "default": 2000},
        "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]}
    }

    budget_items = generate_repeating_field_group(budget_item_keys, "budget")
    # Investment vehicles have a name, average annual return, standard deviation, and ratio
    st.subheader("Investment Vehicles")
    investment_vehicle_keys = {
        "name": {"type": str, "default": "S&P 500"},
        "annual_returns": {"type": float, "default": 0.1026},
        "standard_deviation": {"type": float, "default": 0.1532},
        "ratio": {"type": float, "default": 1.0}
    }
    investment_vehicles = generate_repeating_field_group(investment_vehicle_keys, "investment")
    st.write("Note: The ratios of all investment vehicles must add up to 1.")

    # Major expenses have a name, cost, and date
    st.subheader("Major Expenses")
    major_expense_keys = {
        "name": {"type": str, "default": ""},
        "cost": {"type": int, "default": 0.0},
        "date": {"type": "date", "default": datetime.date.today()}
    }

    major_expenses = generate_repeating_field_group(major_expense_keys, "major_expense")

    # Home purchase details
    home_purchase = st.checkbox("Plan to Purchase a Home", value=False)
    if home_purchase:
        st.subheader("Home Purchase Details")
        home_purchase_date = st.date_input("Home Purchase Date", value=datetime.date(2025, 1, 1), min_value=datetime.date.today())
        home_purchase_price = st.number_input("Home Purchase Price", min_value=0.0, value=300000.0, step=10000.0)
        down_payment = st.number_input("Down Payment", min_value=0.0, value=60000.0, step=1000.0)
        property_tax = st.number_input("Property Tax", min_value=0.0, max_value=0.5, value=.02, step=0.005)
        mortgage_rate = st.slider("Mortgage Rate", min_value=0.0, max_value=0.1, value=0.04, step=0.001)
        mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=30, step=1)
        pay_off_mortgage_before_retirement = st.checkbox("Pay Off Mortgage Before Retirement", value=False)
    location_change = st.checkbox("Plan to Change Location (domestic only)", value=False)
    if location_change:
        st.subheader("Location Change Details")
        location_change_date = st.date_input("Location Change Date", value=datetime.date(2025, 1, 1), min_value=datetime.date.today())
        location_change_moving_cost = st.number_input("Moving Cost", min_value=0.0, value=5000.0, step=1000.0)
        location_change_col_adjustment = st.slider("Cost of Living Adjustment", min_value=0.0, max_value=2.0, value=1.0, step=0.01)
        location_change_state_income_tax = st.number_input("State Income Tax", min_value=0.0, value=0.0, step=0.01)
        location_change_property_tax = st.number_input("Property Tax", min_value=0.0, value=0.0, step=0.01)

    post_retirement_expenses = st.number_input("Post Retirement Expenses", min_value=0.0, value=0.0, step=1000.0)
    average_post_retirement_income = st.number_input("Average Post Retirement Income (not including investments)", min_value=0.0, value=0.0, step=1000.0)
    simulate_years = st.slider("Simulation Years", min_value=1, max_value=50, value=10, step=1)

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
        #create a simulation years slider
        st.success("Running Simulation...")
        user.save_user_as_file()
        ts_df, average_retirement_age, stdev_retirement_age = monte_carlo_simulation(years=simulate_years, simulations=8)
        #DATA VISUALIZATION TIME
        #title for the estimated retirement age
        #calculate 2 standard deviations from the mean up and down to get a range. Should be rounded to ints
        colors = ['#FFAC66', '#FF9E4D', '#FF8F33']
     
        bottom_range = round(average_retirement_age - stdev_retirement_age)
        top_range = round(average_retirement_age + stdev_retirement_age)
        st.title(f"Your Estimated Retirement Age is between :orange[{bottom_range}] and :orange[{top_range}] years old")
        #title for the data visualization
        st.title(f"We ran 8 simulations of {simulate_years} years. Here are the results:")
       
        df_net_worth = ts_df[["net_worth", "investments", "month"]]
        df_net_worth = df_net_worth.set_index("month")  # Set the index on the original DataFrame
        df_net_worth_styled = df_net_worth.style.set_properties(**{'color': colors[0]}, subset=['net_worth']).set_properties(**{'color': colors[1]}, subset=['investments'])
        st.line_chart(df_net_worth_styled)
        #Line chart with home equity value with and without value growth
        if user.home_purchase_date is not None:
            df_home_equity = ts_df[["home_equity_value_with_growth", "month"]]
            st.line_chart(df_home_equity.set_index("month"))
        #budget breakdown as a pie chart
        if len(list(user.budget.keys())) > 1:
            budget = user.budget
            #formatted category_name: {value: int, frequency: str (monthly/annual)}
            categories = list(budget.keys())
            values = [budget[category]["value"] if budget[category]["frequency"] == "monthly" else budget[category]["value"]/12 for category in categories]
            st.title("Here is a breakdown of your proposed budget:")
            orange_blue_palette = [
                '#FFF5EB',  # Very light orange
                '#FFE6CC',  # Light orange
                '#FFD8B2',  # Soft orange
                '#FFCA99',  # Moderate orange
                '#FFBB80',  # Medium orange
                '#FFAC66',  # Bright orange
                '#FF9E4D',  # Strong orange
                '#FF8F33',  # Deep orange
                '#FF801A',  # Very deep orange
                '#FF7000',  # Dark orange, next is dard red then very deep red and so on
                '#FF5F00', # Very dark orange
                '#FF4E00',  # Very dark red
                '#FF3D00',  # Very deep red, next is deep red
                '#FF2C00',  # Deep red
                '#FF1B00',  # Strong red
                '#FF0A00',  # Bright red
                '#F50000',  # Moderate red
                '#E60000',  # Soft red
            ]
            # Create a pie chart
            fig1, ax1 = plt.subplots()
            plt.pie(values, labels=categories, autopct='%1.1f%%', colors=orange_blue_palette)
            ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            st.pyplot(fig1)
            st.subheader(f"Average Monthly Budget: ${round(sum(values), 2)}")
            #raw data table
            #! use some colors for the top row
        st.title("Raw Data")
        df_styled = ts_df.style.set_properties(**{'background-color': colors[1]}, subset=['net_worth']).set_properties(**{'background-color': colors[0]}, subset=['investments'])
        st.write(df_styled)
        return user
    
    
    return None

# Run the Streamlit app
if __name__ == "__main__":
    user = create_user()