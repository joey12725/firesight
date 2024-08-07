import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import random
import math
import datetime
from datetime import timedelta
import json
import pickle
import concurrent.futures
import threading
import queue

# Helper function to ensure all dates are datetime.date
def ensure_date(date):
    if isinstance(date, str):
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()
    elif isinstance(date, datetime.datetime):
        return date.date()
    elif isinstance(date, datetime.date):
        return date
    #none type
    elif date is None:
        return datetime.datetime.today().date()
    else:
        raise ValueError("Unsupported date format")

# Load state taxes data
with open('statetaxes.json', 'r') as file:
    state_taxes = json.load(file)['states']

# Find state tax data
def get_state_tax_data(state_name):
    for state in state_taxes:
        if state['name'] == state_name:
            return state
    return None

class Home:
    def __init__(self, purchase_date, purchase_price, down_payment, mortgage_rate, mortgage_term_years,
                 home_equity=0, home_value=0, average_annual_home_appreciation=0.03, hoa=0, property_tax_rate=0.02, home_buying_costs=0.06):
        self.purchase_date = ensure_date(purchase_date)
        self.purchase_price = purchase_price
        self.down_payment = down_payment
        self.mortgage_rate = mortgage_rate
        self.mortgage_term_years = mortgage_term_years
        self.home_equity = self.down_payment if home_equity == 0 else home_equity
        self.loan_balance = self.purchase_price - self.down_payment
        self.initial_loan_balance = self.loan_balance
        self.interest_paid = 0
        self.home_value = self.purchase_price if home_value == 0 else home_value
        self.average_annual_home_appreciation = average_annual_home_appreciation
        self.property_tax_rate = 0.02 if property_tax_rate == 0 else property_tax_rate
        self.hoa = 100 if hoa == 0 else hoa
        self.home_buying_costs = 0.06 if home_buying_costs == 0 else home_buying_costs
        self.monthly_PI_payment = self.calculate_monthly_PI_payment()
        self.monthly_payment = self.calculate_monthly_payment()
        self.paid_off = False

    def calculate_monthly_PI_payment(self):
        r = self.mortgage_rate / 12
        n = self.mortgage_term_years * 12
        P = self.purchase_price - self.down_payment
        payment = P * (r * (1 + r)**n) / ((1 + r)**n - 1)
        return payment

    def calculate_monthly_payment(self):
        PI_payment = self.calculate_monthly_PI_payment()
        insurance = self.purchase_price * 0.003 / 12
        taxes = self.home_value * self.property_tax_rate / 12
        return PI_payment + insurance + taxes + self.hoa

    def calculate_home_equity(self, date):
        return self.home_value - self.loan_balance

    def make_payment(self, date):
        date = ensure_date(date)
        if self.paid_off:
            return 0
        
        # Calculate the number of months since purchase
        months_since_purchase = (date - self.purchase_date).days / 30.5
        
        # Calculate the remaining loan balance and interest paid
        r = self.mortgage_rate / 12
        n = self.mortgage_term_years * 12
        remaining_payments = n - months_since_purchase

        # Calculate interest and principal using amortization formula
        interest = self.loan_balance * r
        principal = self.monthly_PI_payment - interest
        
        self.loan_balance -= principal
        self.interest_paid += interest

        # Update home value based on appreciation rate once per year
        if months_since_purchase % 12 == 0:
            self.home_value *= (1 + self.average_annual_home_appreciation)
            self.home_value = min(self.home_value, self.purchase_price * 2)  # Cap appreciation at 2x purchase price

        # Update home equity
        self.home_equity = self.calculate_home_equity(date)

        # If loan is paid off, set paid_off to True
        if self.loan_balance <= 0:
            self.paid_off = True 
            self.loan_balance = 0
            self.home_equity = self.home_value
        
        return self.monthly_payment

class InvestmentVehicle:
    def __init__(self, name, annual_returns, standard_deviation, ratio, distribution_type):
        self.name = name
        self.annual_returns = annual_returns
        self.standard_deviation = standard_deviation
        self.ratio = ratio
        self.distribution_type = distribution_type
        self.current_month = random.randint(1, 12)
        self.current_year = 0
        self.previous_year_return = 0
        self.current_year_return = 0
        
        if distribution_type in ['historic-stocks', 'historic-real-estate']:
            data_file = 'stocks.csv' if distribution_type == 'historic-stocks' else 'realestate.csv'
            self.historic_data = pd.read_csv(data_file)
            self.start_index = random.randint(0, len(self.historic_data) - 1)
        
    def get_monthly_return(self):
        if self.distribution_type == 'normal-monthly':
            return np.random.normal(self.annual_returns / 12, self.standard_deviation / math.sqrt(12))
        elif self.distribution_type == 'normal-yearly-gradient':
            if self.current_month == 1:
                self.previous_year_return = self.current_year_return
                self.current_year_return = np.random.normal(self.annual_returns, self.standard_deviation)
            weight_current = self.current_month / 12
            return (1 - weight_current) * self.previous_year_return / 12 + weight_current * self.current_year_return / 12
        elif self.distribution_type in ['historic-stocks', 'historic-real-estate']:
            index = (self.start_index + self.current_year * 12 + self.current_month - 1) % len(self.historic_data)
            return self.historic_data.iloc[index]['Return']
        
    def increment_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1

class MajorPurchase:
    def __init__(self, name, cost, date, purchase_type, term=None, interest_rate=None, down_payment=None, monthly_payment=None):
        self.name = name
        self.cost = cost
        self.date = ensure_date(date)
        self.purchase_type = purchase_type  # 'cash', 'finance', or 'lease'
        self.term = term
        self.interest_rate = interest_rate
        self.down_payment = down_payment
        self.monthly_payment = monthly_payment
        self.remaining_balance = cost if purchase_type == 'finance' else 0

    def make_payment(self):
        if self.purchase_type == 'finance':
            interest = self.remaining_balance * (self.interest_rate / 12)
            principal = self.monthly_payment - interest
            self.remaining_balance -= principal
            return self.monthly_payment
        elif self.purchase_type == 'lease':
            return self.monthly_payment
        return 0


class User:
    def __init__(self):
        self.age = 0
        self.income = 0
        self.budget = {} 
        self.expenditure = sum([value for value in self.budget.values()])
        self.income_growth = 0.03
        self.risk_tolerance = 0.1
        self.expenditure_growth_beyond_inflation = 0.03
        self.current_savings = 0
        self.max_401k_contribution = True
        self.max_ira_contribution = True
        self.max_hsa_contribution = False
        self.other_tax_sheltered_income = 0
        self.tax_brackets = {0.1: 9875, 0.12: 40125, 0.22: 85525, 0.24: 163300, 0.32: 207350, 0.35: 518400, 0.37: 1000000000} #update if you don't live in texas
        self.investment_vehicles = []
        self.investments = 0
        self.post_retirement_expenses = 0
        self.major_purchases = []
        self.married = False
        self.emergency_fund_current = 0
        self.emergency_fund_target = 0
        self.time_series = pd.DataFrame()
        self.home = None
        self.home_purchase_date = None
        self.owns_home = False
        self.home_purchase_price = 0
        self.down_payment = 0
        self.mortgage_rate = 0
        self.mortgage_term_years = 0
        self.home_equity = 0
        self.home_value = 0
        self.property_tax =0.02
        self.inflation = 0.03
        self.time = datetime.datetime.now().date()
        self.month = 0
        self.average_life_event_cost = 1000
        self.life_events_per_year = 1
        self.life_events_std_dev = 1000
        self.pay_off_mortgage_before_retirement = False
        self.post_retirement_expenses = 0
        self.average_post_retirement_income = 0
        self.retirement_income_ratio_brackets = {.1: .025, .25: .03, .75: .04, .85: .05, 1: .06}
        self.retirement_income_ratio = self.get_retirement_income_ratio()
        self.retirement_goal = (self.post_retirement_expenses - self.average_post_retirement_income) / self.retirement_income_ratio
        self.retirement_age = False
        self.location_change = False
        self.location_col_adjustment = 0
        self.location_property_tax_adjustment = 0
        self.location_state_income_tax_adjustment = 0
        self.location_change_date = None
        self.location_change_moving_costs = 0
        self.location_change_state = "None"
        self.state = "None"
        self.state_tax_data = get_state_tax_data(self.state)


    def get_retirement_income_ratio(self):
        if self.risk_tolerance < .1:
            return self.retirement_income_ratio_brackets[.1]
        elif self.risk_tolerance < .25:
            return self.retirement_income_ratio_brackets[.25]
        elif self.risk_tolerance < .75:
            return self.retirement_income_ratio_brackets[.75]
        elif self.risk_tolerance < .85:
            return self.retirement_income_ratio_brackets[.85]
        else:
            return self.retirement_income_ratio_brackets[1]

    def calculate_state_income_tax(self, income):
        if not self.state_tax_data or self.state_tax_data['income_tax'] == 'none':
            return 0
        tax = 0
        for bracket in self.state_tax_data['income_tax']:
            if income > bracket['bracket']:
                tax += (income - bracket['bracket']) * (bracket['rate'] / 100)
        return tax

    def calculate_taxes(self, expenses):
        federal_taxes = 0
        brackets = {
            0: 0,
            0.1: 9875,
            0.12: 40125,
            0.22: 85525,
            0.24: 163300,
            0.32: 207350,
            0.35: 518400,
            0.37: 1000000000
        }
        deductions = 27700 if self.married else 14600
        single_401k_limit = 23000
        married_401k_limit = 76500
        single_ira_limit = 6500
        married_ira_limit = 13000
        
        # Calculate Social Security and Medicare taxes
        social_security_tax_rate = 0.062
        medicare_tax_rate = 0.0145
        social_security_taxable_income = min(self.income, 147000)  # Social Security wage base for 2023
        social_security_tax = social_security_taxable_income * social_security_tax_rate
        medicare_tax = self.income * medicare_tax_rate
        
        # Calculate available income after expenses
        available_income = self.income - expenses
        
        # Adjust 401k and IRA contributions based on available income
        max_401k = min(married_401k_limit if self.married else single_401k_limit, available_income)
        max_ira = min(married_ira_limit if self.married else single_ira_limit, available_income - max_401k)
        
        tmp_income = self.income
        state_income_tax = self.calculate_state_income_tax(tmp_income)
        deductions += max_401k if self.max_401k_contribution else 0
        deductions += max_ira if self.max_ira_contribution else 0
        deductions += self.other_tax_sheltered_income
        tmp_income -= deductions
        
        prev_bracket = 0
        for bracket in brackets.keys():
            if tmp_income > brackets[bracket]:
                federal_taxes += (bracket - prev_bracket) * brackets[prev_bracket]
                tmp_income -= brackets[bracket]
            else:
                federal_taxes += (bracket - prev_bracket) * tmp_income
                break
            prev_bracket = bracket
        
        total_taxes = federal_taxes + social_security_tax + medicare_tax + state_income_tax
        return total_taxes
    
    def get_simple_taxes(self, income):
        federal_taxes = 0
        brackets = {
            0: 0,
            0.1: 9875,
            0.12: 40125,
            0.22: 85525,
            0.24: 163300,
            0.32: 207350,
            0.35: 518400,
            0.37: 1000000000
        }
        #caluclate taxes for a given income without anything other than standard deduction (does not make deductions for 401k, ira, hsa, itemized deductions)
        deductions = 27700 if self.married else 14600
        tmp_income = income - deductions
        prev_bracket = 0
        for bracket in brackets.keys():
            if tmp_income > brackets[bracket]:
                federal_taxes += (bracket - prev_bracket) * brackets[prev_bracket]
                tmp_income -= brackets[bracket]
            else:
                federal_taxes += (bracket - prev_bracket) * tmp_income
                break
            prev_bracket = bracket
        
        social_security_tax_rate = 0.062
        medicare_tax_rate = 0.0145
        social_security_taxable_income = min(income, 147000)
        social_security_tax = social_security_taxable_income * social_security_tax_rate
        medicare_tax = income * medicare_tax_rate
        #st.write(f"tax on {income} is {federal_taxes + social_security_tax + medicare_tax}")
        return federal_taxes + social_security_tax + medicare_tax
        
    def add_investment_vehicle(self, name, annual_returns, standard_deviation, ratio, distribution_type):
        self.investment_vehicles.append(InvestmentVehicle(name, annual_returns, standard_deviation, ratio, distribution_type))
    
    def add_major_purchase(self, name, cost, date, purchase_type, term=None, interest_rate=None, down_payment=None, monthly_payment=None):
        purchase = MajorPurchase(name, cost, date, purchase_type, term, interest_rate, down_payment, monthly_payment)
        self.major_purchases.append(purchase)
    
    def set_home_purchase_date(self, date):
        self.home_purchase_date = ensure_date(date)
        self.owns_home = False if datetime.datetime.now().date() < self.home_purchase_date else True

    def get_random_month_investment_return(self, investment_vehicle):
        return np.random.normal(investment_vehicle.annual_returns / 12, investment_vehicle.standard_deviation / math.sqrt(12))
        
    def get_random_month_all_investment_returns(self):
        total_return = 0
        for vehicle in self.investment_vehicles:
            total_return += vehicle.get_monthly_return() * vehicle.ratio
            vehicle.increment_month()
        return total_return
        
    def get_random_month_all_investment_returns(self):
        keys = ["average_annual", "std_dev", "ratio"]
        return sum([self.get_random_month_investment_return(investment_vehicle)*investment_vehicle.ratio for investment_vehicle in self.investment_vehicles])
    
    def get_random_year_all_investment_returns(self):
        return sum([self.get_random_year_investment_return(investment_vehicle)*investment_vehicle.ratio for investment_vehicle in self.investment_vehicles])
    
    def add_budget_item(self, item):
        self.budget[item["name"]] = {"value":item["value"], "frequency":item["frequency"]}
    
    def get_annual_expenses(self):
        expenses = []
        for value in self.budget.values():
            if isinstance(value, dict) and value.get("frequency") == "annual":
                expenses.append(value.get("value", 0))
        return sum(expenses)

    def get_monthly_expenses(self):
        expenses = []
        for value in self.budget.values():
            if isinstance(value, dict) and value.get("frequency") == "monthly":
                expenses.append(value.get("value", 0))
            if isinstance(value, dict) and value.get("frequency") == "weekly":
                expenses.append(value.get("value", 0)*4.33)
        return sum(expenses)

    def check_home_purchase(self):
        if self.home_purchase_date and not self.owns_home:
            if ensure_date(self.time) > ensure_date(self.home_purchase_date):
                state_property_tax_rate = self.state_tax_data['property_tax'] / 100 if self.state_tax_data else 0
                self.home = Home(self.home_purchase_date, self.home_purchase_price, self.down_payment, self.mortgage_rate, self.mortgage_term_years, property_tax_rate=state_property_tax_rate)
                self.investments -= self.home.down_payment
                self.owns_home = True
            if "rent" in self.budget.keys() and self.owns_home:
                #remove rent and add mortgage payment
                self.add_budget_item({"name":"mortgage", "value":self.home.monthly_payment, "frequency":"monthly"})
                self.budget["rent"]["value"] = 0
            if self.owns_home and "mortgage" in self.budget.keys():
                if self.home.paid_off:
                    self.budget.pop("mortgage")
                    self.owns_home = False
        return self.owns_home

    def step_month(self):
        self.month += 1
        is_new_year = False if self.month % 12 else True
        contribute_to_savings = 0
        monthly_expenses = self.get_monthly_expenses()
        income = self.income / 12
        if is_new_year:
            self.age += 1
            self.income *= (1 + self.income_growth)
            self.expenditure *= (1 + self.expenditure_growth_beyond_inflation)
            annual_expenses = self.get_annual_expenses()
            taxes = self.calculate_taxes((12 * monthly_expenses) + annual_expenses)
            contribute_to_savings -= annual_expenses
        else:
            taxes = 0
            annual_expenses = 0

        # calculate expenses
        monthly_expenses = self.get_monthly_expenses()

        # random life events (life_events_per_year is an average, use random)
        if random.random() < self.life_events_per_year / 12:
            self.emergency_fund_current -= np.random.normal(self.average_life_event_cost, self.life_events_std_dev)

        # calculate savings
        this_month_savings = income - monthly_expenses - taxes - annual_expenses
        if this_month_savings > 0:
            # prioritize maxing out emergency fund
            if self.emergency_fund_current < self.emergency_fund_target:
                if self.emergency_fund_current + this_month_savings > self.emergency_fund_target:
                    this_month_savings -= self.emergency_fund_target - self.emergency_fund_current
                    self.emergency_fund_current = self.emergency_fund_target
                else:
                    self.emergency_fund_current += this_month_savings
                    this_month_savings = 0

        # calculate investment returns
        investment_returns = 1 + self.get_random_month_all_investment_returns()
        self.investments += this_month_savings
        self.investments *= investment_returns

        # check if major expenses are due
        for purchase in self.major_purchases:
            if self.time >= purchase.date:
                if purchase.purchase_type == 'cash':
                    self.investments -= purchase.cost
                    self.major_purchases.remove(purchase)
                elif purchase.purchase_type in ['finance', 'lease']:
                    if purchase.down_payment and purchase.down_payment > 0:
                        self.investments -= purchase.down_payment
                        purchase.down_payment = 0
                    monthly_payment = purchase.make_payment()
                    self.investments -= monthly_payment
                    if purchase.purchase_type == 'finance' and purchase.remaining_balance <= 0:
                        self.major_purchases.remove(purchase)
                    elif purchase.purchase_type == 'lease' and (self.time - purchase.date).days >= purchase.term * 30:
                        self.major_purchases.remove(purchase)

        # check if home purchase
        if self.check_home_purchase():
            self.home.make_payment(self.time)

        self.home_equity = 0 if not self.owns_home else self.home.home_equity

        # calculate net worth
        net_worth = self.investments + self.home_equity + self.emergency_fund_current
        mortgage_balance = 0 if not self.owns_home else self.home.loan_balance
        initial_loan_balance = 0 if not self.owns_home else self.home.initial_loan_balance
        housing_cost = 0
        if "rent" in self.budget.keys():
            housing_cost += self.budget["rent"]["value"]
        if "mortgage" in self.budget.keys():
            housing_cost += self.budget["mortgage"]["value"]
        
        home_equity_value_without_growth = float(initial_loan_balance if initial_loan_balance is not None else 0) - float(mortgage_balance if mortgage_balance is not None else 0) + float(self.down_payment if self.down_payment is not None else 0)
        row = {
            "month": self.month,
            "age": self.age,
            "mortgage balance": mortgage_balance,
            "income": income,
            "annual_income": 12 * income,
            "expenditure": monthly_expenses + annual_expenses,
            "housing_cost": housing_cost,
            "investment_returns": investment_returns,
            "taxes": taxes,
            "home_equity_value_with_growth": self.home_equity,
            "home_equity_value_without_growth": home_equity_value_without_growth,
            "investments": self.investments,
            "emergency_fund": self.emergency_fund_current,
            "net_worth": net_worth
        }
        # round all values to 2 decimal places if they are floats
        for key in row.keys():
            if isinstance(row[key], float):
                row[key] = round(row[key], 2)
        self.time_series = pd.concat([self.time_series, pd.DataFrame(row, index=[0])], ignore_index=True)

        # if location change and the date of the location change is this month, multiply each budget item by the COL adjustment
        if self.location_change:
            self.location_change_date = ensure_date(self.location_change_date)
            if self.location_change_date and self.location_change_date < self.time:
                self.state = self.location_change_state

                for key in self.budget.keys():
                    self.budget[key]["value"] *= self.location_col_adjustment if self.location_col_adjustment is not None else 0
                if self.owns_home:
                    self.home.hoa *= self.location_col_adjustment
                    self.home.property_tax_rate = self.location_property_tax_adjustment + self.state_tax_data['property_tax'] / 100 if self.state_tax_data else 0
                self.location_change = False
            elif self.location_change_date and self.location_change_date > self.time and self.location_change_moving_costs > 0:
                # add major expense for moving costs
                self.add_major_purchase("moving costs", self.location_change_moving_costs, self.location_change_date)
                self.location_change_moving_costs = 0

        self.time += timedelta(days=30.5)

        # check if retirement goal is met
        paid_off = False
        loan_balance = 0
        if self.owns_home:
            paid_off = self.home.paid_off
            loan_balance = self.home.loan_balance
        if self.retirement_goal == 0:
            self.retirement_goal = (self.post_retirement_expenses - self.average_post_retirement_income) / self.retirement_income_ratio
            self.retirement_goal += self.get_simple_taxes(self.post_retirement_expenses) / self.retirement_income_ratio
        if self.investments > self.retirement_goal and not self.retirement_age and not self.pay_off_mortgage_before_retirement:
            self.retirement_age = self.age
        if self.pay_off_mortgage_before_retirement and paid_off and not self.retirement_age:
            self.retirement_age = self.age
        if self.pay_off_mortgage_before_retirement and not paid_off and not self.retirement_age:
            updated_goal = self.retirement_goal + loan_balance
            if self.investments > updated_goal:
                self.retirement_age = self.age

    def step_year(self):
        for i in range(12):
            self.step_month()
    
    def run_simulation(self, years):
        for i in range(years):
            self.step_year()

    def save_user_as_file(self):
        with open('user_data.pkl', 'wb') as outp:
            pickle.dump(self, outp, pickle.HIGHEST_PROTOCOL)

    def load_user_from_file(self):
        with open('user_data.pkl', 'rb') as inp:
            user = pickle.load(inp)
            self.__dict__.update(user.__dict__)

# Define a global counter and lock
global_months_counter = 0
threadLock = threading.Lock()
# Initialize progress state
if 'progress' not in st.session_state:
    st.session_state['progress'] = 0

def increment_counter(months):
    global global_months_counter
    with threadLock:
        global_months_counter += months

def reset_counter():
    global global_months_counter
    global_months_counter = 0

def update_progress_bar(total_months, pb=None):
    if not pb:
        pb = st.progress(0)
    st.session_state['progress'] = global_months_counter / total_months
    pb.progress(st.session_state['progress'])

def monte_carlo_simulation(years=20, simulations=1000, num_threads=4, user=User()):
    all_time_series = []
    retirement_ages = []

    total_months = years * 12 * simulations
    progress_bar = st.progress(0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for _ in range(simulations):
            user_copy = User()
            user_copy.__dict__.update(user.__dict__)
            # Deep copy investment vehicles
            user_copy.investment_vehicles = [InvestmentVehicle(v.name, v.annual_returns, v.standard_deviation, v.ratio, v.distribution_type) for v in user.investment_vehicles]
            futures.append(executor.submit(run_simulation, user_copy, years))

        for future in concurrent.futures.as_completed(futures):
            time_series, retirement_age = future.result()
            all_time_series.append(time_series)
            retirement_ages.append(retirement_age)
            # Update the global counter and progress bar
            increment_counter(years * 12)
            update_progress_bar(total_months, progress_bar)

    # Filter out None values from retirement_ages
    valid_retirement_ages = [age for age in retirement_ages if age is not None]

    if not valid_retirement_ages:
        st.warning("No simulations reached the retirement goal.")
        return None, None, None, None, None

    average_retirement_age = sum(valid_retirement_ages) / len(valid_retirement_ages)
    stdev_retirement_age = np.std(valid_retirement_ages)
    
    combined_time_series = pd.concat(all_time_series, ignore_index=True)
    average_time_series = combined_time_series.groupby('month').mean().reset_index()

    reset_counter()
    return average_time_series, average_retirement_age, stdev_retirement_age, all_time_series, retirement_ages

def run_simulation(user, years):
    time_series = pd.DataFrame()
    retirement_age = None

    for _ in range(years * 12):
        user.step_month()
        if user.investments >= user.retirement_goal and retirement_age is None:
            retirement_age = user.age

    time_series = user.time_series
    return time_series, retirement_age

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
        user.add_investment_vehicle(
            investment_vehicle["name"],
            investment_vehicle["annual_returns"],
            investment_vehicle["standard_deviation"],
            investment_vehicle["ratio"],
            investment_vehicle.get("distribution_type", "normal-monthly")  # Default to "normal-monthly" if not specified
        )
    
    for major_purchase in user_data.get("major_purchases", []):
        user.add_major_purchase(
            major_purchase["name"],
            major_purchase["cost"],
            major_purchase["date"],
            major_purchase["purchase_type"],
            major_purchase.get("term"),
            major_purchase.get("interest_rate"),
            major_purchase.get("down_payment"),
            major_purchase.get("monthly_payment")
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
        
    simulate_years = user_data.get("simulate_years", 10)
    num_simulations = user_data.get("num_simulations", 10)

    ts_df, average_retirement_age, stdev_retirement_age, all_time_series, retirement_ages = monte_carlo_simulation(years=simulate_years, simulations=num_simulations, user=user)

    return ts_df, average_retirement_age, stdev_retirement_age, all_time_series, retirement_ages, user
