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
                 home_equity=0, home_value=0, hoa=0, property_tax_rate=0.02, home_buying_costs=0.06):
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
        self.property_tax_rate = property_tax_rate
        self.hoa = hoa
        self.home_buying_costs = home_buying_costs
        self.monthly_PI_payment = self.calculate_monthly_PI_payment()
        self.monthly_payment = self.calculate_monthly_payment()
        self.paid_off = False
        
        # Load historical real estate data
        self.historic_data = pd.read_csv('realestate.csv')
        self.start_index = random.randint(0, len(self.historic_data) - 1)
        self.current_index = self.start_index

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

    def calculate_home_equity(self):
        return self.home_value - self.loan_balance

    def get_monthly_appreciation(self):
        return self.historic_data.iloc[self.current_index]['Return']

    def make_payment(self, date):
        date = ensure_date(date)
        if self.paid_off:
            return 0
        
        # Calculate interest and principal
        r = self.mortgage_rate / 12
        interest = self.loan_balance * r
        principal = self.monthly_PI_payment - interest
        
        self.loan_balance -= principal
        self.interest_paid += interest

        # Update home value based on historical appreciation data
        monthly_appreciation = self.get_monthly_appreciation()
        self.home_value *= (1 + monthly_appreciation)

        # Update home equity
        self.home_equity = self.calculate_home_equity()

        # If loan is paid off, set paid_off to True
        if self.loan_balance <= 0:
            self.paid_off = True 
            self.loan_balance = 0
            self.home_equity = self.home_value
        
        # Move to the next month in the historical data
        self.current_index = (self.current_index + 1) % len(self.historic_data)
        
        return self.monthly_payment

    def __str__(self):
        return f"Home Purchase Price: {self.purchase_price}, Down Payment: {self.down_payment}, Mortgage Rate: {self.mortgage_rate}, Mortgage Term: {self.mortgage_term_years}, Home Equity: {self.home_equity}, Home Value: {self.home_value}, Monthly Payment: {self.monthly_payment}, Paid Off: {self.paid_off}"
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
    
    def __str__(self):
        return f"{self.name}: {self.annual_returns}, {self.standard_deviation}, {self.ratio}, {self.distribution_type}"
    

class MajorPurchase:
    def __init__(self, item_name, purchase_date, total_cost, purchase_type, down_payment=0, loan_amount=0, 
                 interest_rate=0, loan_term_months=0, lease_term_months=0, monthly_lease_payment=0, 
                 buy_residual=False, residual_value=0, consider_in_net_worth=False, asset_value_change=0):
        self.item_name = item_name
        self.purchase_date = purchase_date
        self.total_cost = total_cost
        self.purchase_type = purchase_type
        self.down_payment = down_payment
        self.loan_amount = loan_amount
        self.interest_rate = interest_rate
        self.loan_term_months = loan_term_months
        self.lease_term_months = lease_term_months
        self.monthly_lease_payment = monthly_lease_payment
        self.buy_residual = buy_residual
        self.residual_value = residual_value
        self.consider_in_net_worth = consider_in_net_worth
        self.asset_value_change = asset_value_change / 100  # Convert percentage to decimal
        self.current_value = total_cost
        self.remaining_balance = loan_amount if purchase_type == 'finance' else 0
        self.months_elapsed = 0

    def update_value(self):
        if self.consider_in_net_worth:
            self.current_value *= (1 + self.asset_value_change / 12)  # Monthly appreciation/depreciation

    def make_payment(self, current_date):
        if ensure_date(current_date) < ensure_date(self.purchase_date):
            return 0  # No payment if current date is before purchase date

        self.months_elapsed = (ensure_date(current_date) - ensure_date(self.purchase_date)).days // 30  # Approximate number of months

        if self.purchase_type == 'finance':
            if self.months_elapsed <= self.loan_term_months:
                monthly_rate = self.interest_rate / 12
                payment = (self.loan_amount * monthly_rate * (1 + monthly_rate) ** self.loan_term_months) / ((1 + monthly_rate) ** self.loan_term_months - 1)
                interest = self.remaining_balance * monthly_rate
                principal = payment - interest
                self.remaining_balance -= principal
                return payment
            return 0
        elif self.purchase_type == 'lease':
            if self.months_elapsed <= self.lease_term_months:
                return self.monthly_lease_payment
            elif self.buy_residual and self.months_elapsed == self.lease_term_months + 1:
                return self.residual_value
            return 0
        return 0

    def get_net_worth_impact(self):
        if self.consider_in_net_worth:
            if self.purchase_type in ['cash', 'finance']:
                return self.current_value - self.remaining_balance
            elif self.purchase_type == 'lease' and self.buy_residual and self.months_elapsed > self.lease_term_months:
                return self.current_value
        return 0

    def __str__(self):
        return f"{self.item_name}: {self.total_cost}, {self.purchase_type}, {self.down_payment}, {self.loan_amount}, {self.interest_rate}, {self.loan_term_months}, {self.lease_term_months}, {self.monthly_lease_payment}, {self.buy_residual}, {self.residual_value}, {self.consider_in_net_worth}, {self.asset_value_change}"


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
        self.total_growth = 1 + self.inflation + self.expenditure_growth_beyond_inflation

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
    
    def add_major_purchase(self, item_name, purchase_date, total_cost, purchase_type, down_payment=0, loan_amount=0, 
                           interest_rate=0, loan_term_months=0, lease_term_months=0, monthly_lease_payment=0, 
                           buy_residual=False, residual_value=0, consider_in_net_worth=False, asset_value_change=0):
        purchase = MajorPurchase(item_name, purchase_date, total_cost, purchase_type, down_payment, loan_amount, 
                                 interest_rate, loan_term_months, lease_term_months, monthly_lease_payment, 
                                 buy_residual, residual_value, consider_in_net_worth, asset_value_change)
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
        self.budget[item["name"]] = {
            "value": item["value"],
            "frequency": item["frequency"],
            "last_update": self.time
        }

    def update_budget_items(self):
        self.budget = {k: {**v, "value": v["value"] * (1+(self.expenditure_growth_beyond_inflation/12)+(self.inflation/12))} for k, v in self.budget.items()}
        if "mortgage" in self.budget:
            self.budget["mortgage"]["value"] = self.home.monthly_payment

    def calculate_monthly_expenses(self):
        monthly_expenses = 0
        for item in self.budget.values():
            if item['frequency'] == 'monthly':
                monthly_expenses += item['value']
            elif item['frequency'] == 'weekly':
                monthly_expenses += item['value'] * 4.33
            # Annual expenses are handled separately
        return monthly_expenses

    def calculate_annual_expenses(self):
        return sum(item['value'] for item in self.budget.values() if item['frequency'] == 'annual')

    def check_home_purchase(self):
        if self.home_purchase_date and not self.owns_home:
            if ensure_date(self.time) >= ensure_date(self.home_purchase_date):
                state_property_tax_rate = self.state_tax_data['property_tax'] / 100 if self.state_tax_data else 0
                self.home = Home(self.home_purchase_date, self.home_purchase_price, self.down_payment, 
                                 self.mortgage_rate, self.mortgage_term_years, 
                                 property_tax_rate=state_property_tax_rate)
                self.investments -= self.home.down_payment
                self.owns_home = True
                
                # Remove rent from budget and add mortgage
                if "rent" in self.budget:
                    del self.budget["rent"]
                self.add_budget_item({
                    "name": "mortgage",
                    "value": self.home.monthly_payment,
                    "frequency": "monthly"
                })
        
        if self.owns_home and "mortgage" in self.budget:
            if self.home.paid_off:
                del self.budget["mortgage"]

        return self.owns_home

    def step_month(self):
        self.month += 1
        self.time += timedelta(days=30.44)
        is_new_year = self.month % 12 == 0

        # Update budget items for inflation and growth
        self.update_budget_items()

        # Calculate expenses
        monthly_expenses = self.calculate_monthly_expenses()
        annual_expenses = self.calculate_annual_expenses() if is_new_year else 0

        # Calculate income and taxes
        income = self.income / 12
        if is_new_year:
            self.age += 1
            self.income *= (1 + self.income_growth)
            taxes = self.calculate_taxes(monthly_expenses * 12 + annual_expenses)
        else:
            taxes = 0

        # Handle random life events
        if np.random.random() < self.life_events_per_year / 12:
            life_event_cost = np.random.normal(self.average_life_event_cost, self.life_events_std_dev)
            self.emergency_fund_current -= life_event_cost
            monthly_expenses += life_event_cost  # Add to this month's expenses

        # Calculate savings and investments
        this_month_savings = income - monthly_expenses - taxes - annual_expenses
        if this_month_savings > 0:
            if self.emergency_fund_current < self.emergency_fund_target:
                emergency_fund_contribution = min(this_month_savings, self.emergency_fund_target - self.emergency_fund_current)
                self.emergency_fund_current += emergency_fund_contribution
                this_month_savings -= emergency_fund_contribution

        # Update investments
        investment_returns = 1 + self.get_random_month_all_investment_returns()
        self.investments = (self.investments + this_month_savings) * investment_returns

        # Handle major purchases
        for purchase in self.major_purchases:
            if ensure_date(self.time) >= ensure_date(purchase.purchase_date):
                if purchase.months_elapsed == 0:
                    if purchase.purchase_type == 'cash':
                        self.investments -= purchase.total_cost
                    elif purchase.purchase_type in ['finance', 'lease']:
                        self.investments -= purchase.down_payment
                payment = purchase.make_payment(ensure_date(self.time))
                self.investments -= payment
                purchase.update_value()

        # Check for home purchase
        self.check_home_purchase()

        # Update home equity
        self.home_equity = 0 if not self.owns_home else self.home.home_equity
        
        # Calculate net worth
        net_worth = self.investments + self.home_equity + self.emergency_fund_current
        for purchase in self.major_purchases:
            net_worth += purchase.get_net_worth_impact()

        # Prepare row for time series
        row = {
            "month": self.month,
            "age": self.age,
            "income": income,
            "annual_income": self.income,
            "monthly_expenses": monthly_expenses,
            "annual_expenses": annual_expenses,
            "taxes": taxes,
            "investments": self.investments,
            "emergency_fund": self.emergency_fund_current,
            "net_worth": net_worth,
            "home_equity": self.home_equity
        }

        # Add budget items to the row
        for item_name, item in self.budget.items():
            row[f"budget_{item_name}"] = item['value']

        if self.home:
            row["home_value"] = self.home.home_value
            row["loan_balance"] = self.home.loan_balance
            self.home.make_payment(self.time)
        # Append to time series
        self.time_series = pd.concat([self.time_series, pd.DataFrame([row])], ignore_index=True)

        # Check for retirement
        if not self.retirement_age:
            if self.investments >= self.retirement_goal:
                if not self.pay_off_mortgage_before_retirement or (self.owns_home and self.home.paid_off):
                    self.retirement_age = self.age
        if self.retirement_goal <= 0:
            self.retirement_goal = (self.post_retirement_expenses-self.average_post_retirement_income)/self.retirement_income_ratio
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
    
    def __str__(self):
        return f"User: {self.age}, {self.income}, {self.budget}, {self.expenditure}, {self.income_growth}, {self.risk_tolerance}, {self.expenditure_growth_beyond_inflation}, {self.current_savings}, {self.max_401k_contribution}, {self.max_ira_contribution}, {self.max_hsa_contribution}, {self.other_tax_sheltered_income}, {self.investment_vehicles}, {self.investments}, {self.post_retirement_expenses}, {self.major_purchases}, {self.married}, {self.emergency_fund_current}, {self.emergency_fund_target}, {self.time_series}, {self.home}, {self.home_purchase_date}, {self.owns_home}, {self.home_purchase_price}, {self.down_payment}, {self.mortgage_rate}, {self.mortgage_term_years}, {self.home_equity}, {self.home_value}, {self.property_tax}, {self.inflation}, {self.time}, {self.month}, {self.average_life_event_cost}, {self.life_events_per_year}, {self.life_events_std_dev}, {self.pay_off_mortgage_before_retirement}, {self.post_retirement_expenses}, {self.average_post_retirement_income}, {self.retirement_income_ratio_brackets}, {self.retirement_income_ratio}, {self.retirement_goal}, {self.retirement_age}, {self.location_change}, {self.location_col_adjustment}, {self.location_property_tax_adjustment}, {self.location_state_income_tax_adjustment}, {self.location_change_date}, {self.location_change_moving_costs}, {self.location_change_state}, {self.state}, {self.state_tax_data}, {self.total_growth}"
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
        reset_counter()
    average_retirement_age = sum(valid_retirement_ages) / max(len(valid_retirement_ages), 0.1)
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
        user.pay_off_mortgage_before_retirement = user_data["home_purchase"].get("pay_off_before_retirement", False)
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