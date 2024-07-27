import streamlit as st
import datetime
import os
import uuid
import json
import matplotlib.pyplot as plt

# Set page configuration
st.set_page_config(page_title="FIRE Simulator", page_icon="🔥")

# Attempt to load FIRE.py script
try:
    exec(open(os.path.join(os.getcwd(), "FIRE.py")).read())
except FileNotFoundError as e:
    st.error(f"Error loading FIRE.py: {e}")

def load_user_file():
    st.write("upload file")
    uploaded_file = st.file_uploader("Been here before? Upload your user profile:", type="json")
    if uploaded_file is not None:
        return json.load(uploaded_file)
    return None

global tooltips 
tooltips = st.toggle("Would you like to see tooltips?", value=True)

def tooltip(text, type="caption"):
    if tooltips:
        if type == "caption":
            st.caption(text)
        elif type == "markdown":
            st.markdown(f"🛈 {text}")
        elif type == "latex":
            st.latex(f"🛈 {text}")
        elif type == "title":
            st.title(f"🛈 {text}")

def generate_repeating_field_group(keys, group_id, default_values=None):
    # Initialize the rows if not already in session state
    if f"rows_{group_id}" not in st.session_state or not st.session_state[f"rows_{group_id}"]:
        if default_values:
            # Initialize with indices from the list of default values
            st.session_state[f"rows_{group_id}"] = [str(i) for i in range(len(default_values))]
        else:
            st.session_state[f"rows_{group_id}"] = []

    rows_collection = []

    def add_row():
        # Find the next index based on existing rows
        new_index = str(len(st.session_state[f"rows_{group_id}"]))
        st.session_state[f"rows_{group_id}"].append(new_index)

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

    for row_index in st.session_state[f"rows_{group_id}"]:
        defaults = default_values[int(row_index)] if default_values and int(row_index) < len(default_values) else None
        row_data = generate_row(row_index, defaults)
        rows_collection.append(row_data)

    return rows_collection

def create_user(user_data=None):
    st.title("FIRE Simulator🔥")
    tooltip("FIRE (Financial Independence, Retire Early) is a financial movement that emphasizes achieving financial independence and retiring earlier than the traditional retirement age. The core philosophy revolves around the idea of gaining control over your time by attaining a level of financial security that allows you to choose how you spend your days, free from the constraints of mandatory work.This simulator helps you explore how attainable FIRE is for you.", type="markdown")
    tooltip("Please note: If you have a partner, use either average or combined numbers as makes sense (combined income, average age).")

    # Default values or loaded user data
    if user_data:
        # Extract user data or set default values
        simulate_years = user_data.get("simulate_years", 10)
        num_simulations = user_data.get("num_simulations", 10)
    else:
        simulate_years = 10
        num_simulations = 10

    if user_data:
        # Directly use the lists from the JSON data
        budget_items_data = user_data.get("budget_items", [])
        investment_vehicles_data = user_data.get("investment_vehicles", [])
        major_expenses_data = user_data.get("major_expenses", [])
    else:
        # Default empty lists if no data is loaded
        budget_items_data = []
        investment_vehicles_data = []
        major_expenses_data = []
    if user_data:
        age = user_data.get("age", 22)
        state = user_data.get("state", "California")
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
        location_change_data = user_data.get("location_change", False)
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
        state = "California"

    # Get user input
    age = st.number_input("Age", min_value=0, value=age, step=1)
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Washington D.C.", "Puerto Rico", "None"]
    state = st.selectbox("State", options=states, index=states.index(state))
    married = st.checkbox("Are you married?", value=married)
    income = st.number_input("Income", min_value=0.0, value=income, step=1000.0, help="This is your annual gross income from all sources.")
    tooltip("This should be your gross annual income, combined if you are married, from all sources")
    income_growth = st.slider("Income Growth", min_value=0.0, max_value=0.2, value=income_growth, step=0.01)
    tooltip("This is the percentage that you expect your income to increase each year.")
    risk_tolerance = st.slider("Risk Tolerance", min_value=0.0, max_value=1.0, value=risk_tolerance, step=0.01)
    tooltip(r"A risk tolerance of 0.5 adheres to the 4% rule, which is a theory stating that you can safely withdraw 4% of your retirement portfolio each year without running out. Lower values are more conservative, higher values more aggressive.")
    expenditure_growth_beyond_inflation = st.slider("Expenditure Growth Beyond Inflation", min_value=0.0, max_value=0.1, value=expenditure_growth_beyond_inflation, step=0.01)
    tooltip("This is your lifestyle creep percentage each year beyond inflation.")
    current_savings = st.number_input("Current Savings", min_value=0.0, value=current_savings, step=1000.0)
    max_401k_contribution = st.checkbox("Max 401k Contribution", value=max_401k_contribution)
    max_ira_contribution = st.checkbox("Max IRA Contribution", value=max_ira_contribution)
    max_hsa_contribution = st.checkbox("Max HSA Contribution", value=max_hsa_contribution)
    other_tax_sheltered_income = st.number_input("Other Tax Sheltered Income", min_value=0.0, value=other_tax_sheltered_income, step=1000.0)
    tooltip("This is a portion of your total income, not additional income (e.g., charitable contributions or health savings account contributions below the maximum).")
    emergency_fund_target = st.number_input("Emergency Fund Target", min_value=0.0, value=emergency_fund_target, step=1000.0)
    tooltip("This should represent at least 3-6 months of expenses.")
    inflation = st.slider("Inflation", min_value=0.0, max_value=0.1, value=inflation, step=0.01)
    average_life_event_cost = st.number_input("Average Life Event Cost", min_value=0.0, value=average_life_event_cost, step=1000.0)
    tooltip("It is important to model the unexpected for life events that you can't budget for. These events will come out of your emergency fund.")
    average_life_event_stdev = st.number_input("Life Event Standard Deviation", min_value=0.0, value=average_life_event_stdev, step=1000.0)
    average_life_event_frequency = st.slider("Average Life Events per year", min_value=0, max_value=10, value=average_life_event_frequency, step=1)
    
    budget_item_keys = {
        "name": {"type": str, "default": ""},
        "value": {"type": int, "default": 2000},
        "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]}
    }
    
    investment_vehicle_keys = {
        "name": {"type": str, "default": "S&P 500"},
        "annual_returns": {"type": float, "default": 0.1026},
        "standard_deviation": {"type": float, "default": 0.1532},
        "ratio": {"type": float, "default": 1.0}
    }

    major_expense_keys = {
        "name": {"type": str, "default": ""},
        "cost": {"type": int, "default": 0.0},
        "date": {"type": "date", "default": datetime.date.today()}
    }

    st.subheader("Budget Items")
    tooltip("This budget should represent your actual monthly expenses, including things like healthcare premiums that are deducted from your paycheck, but not things like 401k contributions. Do not include savings in this budget, this is only for your expendatures, all of you income not used in the budget will be invested in your investment portfolio.")
    tooltip(r"A typical FIRE strategy includes high savings rates, often between 50-70% of income allowing your nest egg to be built as quickly as possible.")
    tooltip("If rent is a budget category and you plan to purchase a home, it will automatically be removed at your planned home purchase date and replaced with a mortgage payment.")
    budget_items = generate_repeating_field_group(budget_item_keys, "budget", budget_items_data)

    st.subheader("Investment Vehicles")
    tooltip("""
Investment vehicles are essential tools for those pursuing Financial Independence, Retire Early (FIRE). These vehicles help grow wealth effectively, enabling individuals to achieve financial independence sooner. Key investment vehicles for FIRE include:

1. **Stocks and Bonds**: A diversified portfolio of stocks and bonds can provide steady growth and income. Stocks offer higher returns with higher risk, while bonds provide stability and regular interest payments.

2. **Index Funds and ETFs**: These funds track market indices, offering diversification and lower fees. They are ideal for passive investors seeking consistent market returns over time.

3. **Real Estate**: Investing in rental properties or REITs (Real Estate Investment Trusts) can provide passive income and capital appreciation. Real estate is a tangible asset that often appreciates over the long term.

4. **Retirement Accounts**: 401(k), IRA, and Roth IRA accounts offer tax advantages that can significantly boost savings. Contributions to these accounts grow tax-deferred or tax-free, depending on the account type.

5. **High-Yield Savings Accounts and CDs**: For those seeking low-risk options, high-yield savings accounts and certificates of deposit (CDs) offer better returns than traditional savings accounts while ensuring capital preservation.

6. **Peer-to-Peer Lending**: Platforms like LendingClub and Prosper allow individuals to lend money to others in exchange for interest payments, providing an alternative income stream.

By strategically using these investment vehicles, individuals can accelerate their journey toward financial independence and early retirement. Diversification, consistent contributions, and understanding each vehicle's risk and return profile are crucial for achieving FIRE goals.
""", type="markdown"
                )
    investment_vehicles = generate_repeating_field_group(investment_vehicle_keys, "investment", investment_vehicles_data)

    st.subheader("Major Expenses")
    tooltip("Major expenses are one-time or infrequent expenses that you anticipate in the future. These could include things like a wedding, a new car, or a vacation. These expenses will be deducted from your savings when they occur.")
    major_expenses = generate_repeating_field_group(major_expense_keys, "major_expense", major_expenses_data)

    
    home_purchase = st.checkbox("Plan to Purchase a Home", value= True if home_purchase_data.get("price", 0) != 0 else False)
    if home_purchase:
        st.subheader("Home Purchase Details")
        home_purchase_date_default = "2025-01-01"
        home_purchase_date_str = str(home_purchase_data.get("date", home_purchase_date_default))  # Ensure it's a string
        if home_purchase_date_str:
            try:
                home_purchase_date_value = datetime.date.fromisoformat(home_purchase_date_str)
            except ValueError:
                home_purchase_date_value = datetime.date.fromisoformat(home_purchase_date_default)  # Fallback to default if conversion fails
        else:
            home_purchase_date_value = datetime.date(2025, 1, 1)  # Fallback if string is empty or null

        home_purchase_date = st.date_input("Home Purchase Date", value=home_purchase_date_value, min_value=datetime.date.today())
        home_purchase_price = st.number_input("Home Purchase Price", min_value=0.0, value=home_purchase_data.get("price", 300000.0), step=10000.0)
        down_payment = st.number_input("Down Payment", min_value=0.0, value=home_purchase_data.get("down_payment", 60000.0), step=1000.0)
        property_tax = st.number_input("Local Property Tax", min_value=0.0, max_value=0.5, value=home_purchase_data.get("property_tax", 0.02), step=0.005)
        tooltip("This is the annual property tax rate for your area. It does not include your state's property tax.")
        mortgage_rate = st.slider("Mortgage Rate", min_value=0.0, max_value=0.1, value=home_purchase_data.get("mortgage_rate", 0.04), step=0.001)
        mortgage_term_years = st.slider("Mortgage Term (Years)", min_value=10, max_value=30, value=home_purchase_data.get("mortgage_term_years", 30), step=1)
        pay_off_mortgage_before_retirement = st.checkbox("Pay Off Mortgage Before Retirement", value=home_purchase_data.get("pay_off_before_retirement", False))
    
    location_change = st.checkbox("Plan to Change Location (domestic only)", value=False)
    if location_change:
        st.subheader("Location Change Details")
        location_change_date_default = "2025-01-01"
        location_change_date_str = str(location_change_data.get("date", location_change_date_default))  # Convert to string to be safe

        # Attempt to parse the date string; fallback to default if it fails
        try:
            location_change_date_value = datetime.date.fromisoformat(location_change_date_str)
        except ValueError:
            location_change_date_value = datetime.date.fromisoformat(location_change_date_default)  # Fallback to default if the format is incorrect

        location_change_date = st.date_input("Location Change Date", value=location_change_date_value, min_value=datetime.date.today())
        location_change_moving_cost = st.number_input("Moving Cost", min_value=0.0, value=location_change_data.get("moving_cost", 5000.0), step=1000.0)
        tooltip("This is the cost of moving to a new location. It is a one-time expense.")
        location_change_col_adjustment = st.slider("Cost of Living Adjustment", min_value=0.0, max_value=2.0, value=location_change_data.get("col_adjustment", 1.0), step=0.01)
        tooltip("The ratio between your costs where you are and where you want to move. [Learn more](https://www.nerdwallet.com/cost-of-living-calculator).", type="markdown")
        location_change_state = st.selectbox("State", options=states, index=states.index(location_change_data.get("state", "None")))

    
    post_retirement_expenses = st.number_input("Post Retirement Expenses", min_value=0.0, value=post_retirement_expenses, step=1000.0, help="What you want to live off of in your early retirement. It will grow with inflation.")
    tooltip("This is the amount you expect to spend each year in retirement. It should be adjusted for inflation.")
    average_post_retirement_income = st.number_input("Average Post Retirement Income (not including investments)", min_value=0.0, value=average_post_retirement_income, step=1000.0)
    tooltip("This is the amount you expect to earn each year in retirement outside of your investment. It should be adjusted for inflation.")
    simulate_years = st.slider("Simulation Years", min_value=1, max_value=50, value=simulate_years, step=1, key="simulate_years_slider")
    tooltip("This is the number of years you want to simulate to see if you can retire early. It should be a few years longer than your expected retirement age.")
    num_simulations = st.slider("Number of Simulations", min_value=1, max_value=50, value=num_simulations, step=1, format="Count: %d", key="num_simulations_slider")
    tooltip("This is the number of simulations you want to run to see if you can retire early. More simulations will give you a more accurate result, but a longer time to compute.")
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
            user.add_investment_vehicle(investment_vehicle["name"], investment_vehicle["annual_returns"], investment_vehicle["standard_deviation"], investment_vehicle["ratio"])
        
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
            user.location_change_state = location_change_state
            
        
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
                "state": location_change_state if location_change else None
            },
            "post_retirement_expenses": post_retirement_expenses,
            "average_post_retirement_income": average_post_retirement_income,
            "simulate_years": simulate_years,
            "num_simulations": num_simulations,
            "investment_vehicles":investment_vehicles,
            #convert dates to iso format strings for json serialization
            "major_expenses": [{"name": expense["name"], "cost": expense["cost"], "date": expense["date"].isoformat()} for expense in major_expenses],
            "budget_items": budget_items,
            "state": state
        }
        
        user_json = json.dumps(user_data, indent=4)
        st.download_button('Download User Configuration', user_json, file_name='user.json', mime='application/json')
        ts_df, average_retirement_age, stdev_retirement_age = monte_carlo_simulation(years=simulate_years, simulations=num_simulations, user=user)
        #calculate 2 standard deviations from the mean up and down to get a range. Should be rounded to ints
        colors = ['#FFAC66', '#FF9E4D', '#FF8F33']
     
        bottom_range = round(average_retirement_age - stdev_retirement_age)
        top_range = round(average_retirement_age + stdev_retirement_age)
        st.title(f"Your Estimated Retirement Age is between :orange[{bottom_range}] and :orange[{top_range}] years old")
        #title for the data visualization
        st.title(f"We ran {num_simulations} simulations of {simulate_years} years. Here are the results:")
       
        st.subheader(f"Here is Your Projected Net Worth and Investments Over The Next {simulate_years} Years:")
        df_net_worth = ts_df[["net_worth", "investments", "month"]]
        df_net_worth = df_net_worth.set_index("month")  # Set the index on the original DataFrame
        df_net_worth_styled = df_net_worth.style.set_properties(**{'color': colors[0]}, subset=['net_worth']).set_properties(**{'color': colors[1]}, subset=['investments'])
        st.line_chart(df_net_worth_styled)
        #Line chart with home equity value with and without value growth
        if user.home_purchase_date is not None:
            st.subheader("Your Home Equity")
            df_home_equity = ts_df[["home_equity_value_with_growth", "month"]]
            st.line_chart(df_home_equity.set_index("month"))
        #budget breakdown as a pie chart
        if len(list(user.budget.keys())) > 1:
            budget = user.budget
            #formatted category_name: {value: int, frequency: str (monthly/annual)}
            categories = list(budget.keys())
            values = [budget[category]["value"] if budget[category]["frequency"] == "monthly" else budget[category]["value"]/12 for category in categories]
            st.subheader("Here is a breakdown of your proposed budget:")
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
        st.subheader("Here is the raw data for your simulation:")
        df_styled = ts_df.style.set_properties(**{'background-color': colors[1]}, subset=['net_worth']).set_properties(**{'background-color': colors[0]}, subset=['investments'])
        st.write(df_styled)
        return user
    
    
    return None

if __name__ == "__main__":
    user_data = load_user_file()
    create_user(user_data)
