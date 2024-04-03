import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import seaborn as sns
import random
import math
import streamlit as st
import datetime
import pickle
import concurrent.futures


# Add relocation date with COL adjustment, Tax adjustment
# Add "pay off mortgage" before retirement button

class Home:
    def __init__(self, purchase_date, purchase_price, down_payment, mortgage_rate, mortgage_term_years,
                 home_equity=0, home_value=0, average_annual_home_appreciation=0.03, hoa=0, property_tax_rate=0.02, home_buying_costs=0.06):
        self.purchase_date = purchase_date
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
        if self.paid_off:
            return 0
        
        # Calculate the number of months since purchase
        months_since_purchase = (date.date() - self.purchase_date).days / 30.5
        
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
    
class User():
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
        self.major_expenses = []
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
        self.time = datetime.datetime.now()
        self.month = 0
        self.average_life_event_cost = 1000
        self.life_events_per_year = 1
        self.life_events_std_dev = 1000
        self.pay_off_mortgage_before_retirement = False
        self.post_retirement_expenses = 0
        self.average_post_retirement_income = 0
        retirement_income_ratio_brackets = {.1: .025, .25: .03, .75: .04, .85: .05, 1: .06}
        #bracket connects risk tolerance to retirement income ratio
        if self.risk_tolerance < .1:
            self.retirement_income_ratio = retirement_income_ratio_brackets[.1]
        elif self.risk_tolerance < .25:
            self.retirement_income_ratio = retirement_income_ratio_brackets[.25]
        elif self.risk_tolerance < .75:
            self.retirement_income_ratio = retirement_income_ratio_brackets[.75]
        elif self.risk_tolerance < .85:
            self.retirement_income_ratio = retirement_income_ratio_brackets[.85]
        else:
            self.retirement_income_ratio = retirement_income_ratio_brackets[1]
        self.retirement_goal = (self.post_retirement_expenses - self.average_post_retirement_income) / self.retirement_income_ratio
        self.retirement_age = False
        self.location_change = False
        self.location_col_adjustment = 0
        self.location_property_tax_adjustment = 0
        self.location_state_income_tax_adjustment = 0
        self.location_change_date = None
        self.location_change_moving_costs = 0

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
        state_income_tax_rate = self.location_state_income_tax_adjustment
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
        state_income_tax = tmp_income * state_income_tax_rate
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
        
    def add_invstment_vehicle(self, name, average_annual, std_dev, ratio=1):
        self.investment_vehicles.append({"name": name, "average_annual":average_annual, "std_dev":std_dev, "ratio":ratio})
    
    def add_major_expense(self, name, cost, date):
        self.major_expenses.append({"name":name, "cost":cost, "date":date})
    
    def set_home_purchase_date(self, date):
        self.home_purchase_date = date
        self.owns_home = False if datetime.datetime.now() < self.home_purchase_date else True

    def get_random_month_investment_return(self, investment_vehicle):
        return np.random.normal(investment_vehicle["average_annual"]/12, investment_vehicle["std_dev"]/12)
        
    def get_random_year_investment_return(self, investment_vehicle):
        if isinstance(investment_vehicle, dict):
            for vehicle_data in investment_vehicle.values():
                return np.random.normal(vehicle_data["average_annual"], vehicle_data["std_dev"])
        else:
            return 0
        
    def get_random_month_all_investment_returns(self):
        keys = ["average_annual", "std_dev", "ratio"]
        return sum([self.get_random_month_investment_return(investment_vehicle)*investment_vehicle["ratio"] for investment_vehicle in self.investment_vehicles])
    
    def get_random_year_all_investment_returns(self):
        return sum([self.get_random_year_investment_return(investment_vehicle)*investment_vehicle["ratio"] for investment_vehicle in self.investment_vehicles])
    
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
            if self.time.date() > self.home_purchase_date:
                self.home = Home(self.home_purchase_date, self.home_purchase_price, self.down_payment, self.mortgage_rate, self.mortgage_term_years, property_tax_rate=self.property_tax)
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
        income = self.income/12
        if is_new_year:
            self.age += 1
            self.income *= (1+self.income_growth)
            self.expenditure *= (self.expenditure_growth_beyond_inflation)
            annual_expenses = self.get_annual_expenses()
            taxes = self.calculate_taxes((12*monthly_expenses) + annual_expenses)
            contribute_to_savings -= annual_expenses
        else:
            taxes = 0
            annual_expenses = 0
        #calculate expenses
        monthly_expenses = self.get_monthly_expenses()
        #random life events (life_events_per_year is an average, use random)
        if random.random() < self.life_events_per_year/12:
            self.emergency_fund_current -= np.random.normal(self.average_life_event_cost, self.life_events_std_dev)
        #calculate savings
        this_month_savings = income - monthly_expenses - taxes - annual_expenses
        if this_month_savings > 0:
            #prioritize maxing out emergency fund
            if self.emergency_fund_current < self.emergency_fund_target:
                if self.emergency_fund_current + this_month_savings > self.emergency_fund_target:
                    this_month_savings -= self.emergency_fund_target - self.emergency_fund_current
                    self.emergency_fund_current = self.emergency_fund_target
                else:
                    self.emergency_fund_current += this_month_savings
                    this_month_savings = 0
        #calculate investment returns
        investment_returns = 1+self.get_random_month_all_investment_returns()
        self.investments += this_month_savings
        self.investments *= investment_returns
        #check if major expenses are due
        this_month_major_expense = 0
        for major_expense in self.major_expenses:
            if major_expense["date"] - self.time.date() < datetime.timedelta(days=30.5):
                self.investments -= major_expense["cost"]
                self.major_expenses.remove(major_expense)
                this_month_major_expense = major_expense["cost"]
        #check if home purchase
        if self.check_home_purchase():
            self.home.make_payment(self.time)
        
        self.home_equity = 0 if not self.owns_home else self.home.home_equity
        if self.current_savings > 0:
            self.investments += self.current_savings
            self.current_savings = 0
        #calculate net worth
        net_worth = self.investments + self.home_equity + self.emergency_fund_current
        mortgage_balance = 0 if not self.owns_home else self.home.loan_balance
        inital_loan_balance = 0 if not self.owns_home else self.home.initial_loan_balance
        housing_cost = 0
        if "rent" in self.budget.keys():
            housing_cost += self.budget["rent"]["value"]
        if "mortgage" in self.budget.keys():
            housing_cost += self.budget["mortgage"]["value"]
        home_equity_value_without_growth = inital_loan_balance - mortgage_balance + self.down_payment
        row = {"month": self.month, "age":self.age, "mortgage balance": mortgage_balance,"income":income, "annual_income": 12*income, "expenditure":monthly_expenses+annual_expenses, "housing_cost": housing_cost,"investment_returns":investment_returns, "taxes":taxes, "major_expenses":this_month_major_expense, "home_equity_value_with_growth":self.home_equity, "home_equity_value_without_growth": home_equity_value_without_growth,"investments":self.investments, "emergency_fund":self.emergency_fund_current, "net_worth":net_worth}
        #round all values to 2 decimal places if they are floats
        for key in row.keys():
            if type(row[key]) == float:
                row[key] = round(row[key], 2)
            self.time_series = pd.concat([self.time_series, pd.DataFrame(row, index=[0])], ignore_index=True)
        #if location change and the date of the location change is this month, multiply each budget item by the COL adjustment
        if self.location_change and self.location_change_date < self.time.date():
            for key in self.budget.keys():
                self.budget[key]["value"] *= self.location_col_adjustment    
            if self.owns_home:
                self.home.hoa *= self.location_col_adjustment
                self.home.property_tax_rate = self.location_property_tax_adjustment
            self.location_change = False
        elif self.location_change and self.location_change_date > self.time.date() and self.location_change_moving_costs > 0:
            #add major expense for moving costs
            self.add_major_expense("moving costs", self.location_change_moving_costs, self.location_change_date)
            self.location_change_moving_costs = 0

        self.time += datetime.timedelta(days=30.5)
        #check if retirement goal is met
        paid_off = False
        loan_balance = 0
        if self.owns_home:
            paid_off = self.home.paid_off
            loan_balance = self.home.loan_balance
        if self.retirement_goal == 0:
            self.retirement_goal = (self.post_retirement_expenses - self.average_post_retirement_income) / self.retirement_income_ratio
            self.retirement_goal += self.get_simple_taxes(self.post_retirement_expenses)/self.retirement_income_ratio
        if self.investments > self.retirement_goal and not self.retirement_age and not self.pay_off_mortgage_before_retirement:
            #(self.post_retirement_expenses - self.average_post_retirement_income) / self.retirement_income_ratio
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



def run_simulation(user, years):
    user.run_simulation(years)
    return user.time_series, user.retirement_age

def monte_carlo_simulation(years=20, simulations=1000, num_threads=4):
    user = User()
    user.load_user_from_file()
    
    all_time_series = []
    retirement_ages = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for _ in range(simulations):
            user_copy = User()
            user_copy.__dict__.update(user.__dict__)
            futures.append(executor.submit(run_simulation, user_copy, years))
        
        for future in concurrent.futures.as_completed(futures):
            time_series, retirement_age = future.result()
            all_time_series.append(time_series)
            retirement_ages.append(retirement_age)
    
    anyFalse = False
    for age in retirement_ages:
        if age == False:
            retirement_ages.remove(age)
            anyFalse = True
    if anyFalse:
        st.write("Some simulations did not reach the retirement goal, expand the simulation time for more accurate results.")
    
    combined_time_series = pd.concat(all_time_series, ignore_index=True)
    average_time_series = combined_time_series.groupby('month').mean().reset_index()
    average_retirement_age = sum(retirement_ages) / len(retirement_ages)
    stdev_retirement_age = np.std(retirement_ages)
    
    return average_time_series, average_retirement_age, stdev_retirement_age