import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import random
import requests
import math
import json
import threading
import concurrent.futures
import sys
import streamlit as st
import warnings

warnings.filterwarnings('ignore')

# Helper function to ensure all dates are datetime.date
def ensure_date(date):
    if isinstance(date, str):
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()
    elif isinstance(date, datetime.datetime):
        return date.date()
    elif isinstance(date, datetime.date):
        return date
    elif date is None:
        return datetime.datetime.today().date()
    else:
        raise ValueError("Unsupported date format")


# ---- DATA LOADING ----
with open('statetaxes.json', 'r') as file:
    state_taxes = json.load(file)['states']

col_data = pd.read_csv('cost-of-living.csv')

stocks_data = pd.read_csv('stocks.csv')       # Must have a 'Return' column of monthly returns
real_estate_data = pd.read_csv('realestate.csv')  # Also with a 'Return' column or similar


def get_state_tax_data(state_name):
    for state in state_taxes:
        if state['name'] == state_name:
            return state
    return None


# -----------------------------
# Specialized Return Generation
# -----------------------------
class ReturnGenerator:
    """
    A specialized return generator that can do:
      - Block bootstrap on historical data (with a chosen block size).
      - Simple Markov chain or multi-state approach for some assets.
    We generate a full sequence of monthly returns at the start,
    then each month we just step through that pre-generated sequence.
    """

    def __init__(self, asset_name: str, n_months: int,
                 block_size: int = 12,
                 real_estate_type: str = "REIT"):
        """
        :param asset_name: "Index Funds", "Bonds", "Crypto", "Rental Real Estate", etc.
        :param n_months: how many months to generate in total
        :param block_size: for block bootstrap from historical data
        :param real_estate_type: "REIT", "long term rentals", "short term rentals", "house flipping"
        """
        self.asset_name = asset_name
        self.n_months = n_months
        self.block_size = block_size
        self.real_estate_type = real_estate_type

        # We'll store the monthly returns in a list
        self.returns = []
        self.generate_returns()

    def generate_returns(self):
        """
        Generates the entire monthly return sequence for the asset.
        For large n_months, we repeatedly pick blocks or use states as needed.
        """
        if self.asset_name == 'Index Funds':
            self.returns = self.block_bootstrap(stocks_data['Return'].values, self.n_months)

        elif self.asset_name == 'Rental Real Estate':
            # We'll rely on real_estate_type
            # Then do block bootstrapping from real_estate_data with a small multiplier, noise, etc.
            base_data = real_estate_data['Return'].values
            # Then we adjust or add noise depending on real_estate_type
            raw_seq = self.block_bootstrap(base_data, self.n_months)
            if self.real_estate_type == "long term rentals":
                # minimal change
                self.returns = raw_seq
            elif self.real_estate_type == "short term rentals":
                # add some volatility
                self.returns = [r + np.random.normal(0, abs(r)*0.1) for r in raw_seq]
            elif self.real_estate_type == "house flipping":
                # a cyclical approach with possible negative months
                # for house flipping we might do short blocks with bigger stdev
                # but let's keep it simple:
                self.returns = [np.random.normal(r*0.5, 0.1) for r in raw_seq]
            else:
                # default REIT
                self.returns = raw_seq

        elif self.asset_name == 'Bonds':
            # We'll do a small Markov chain with 3 states: normal, rising_rates, dropping_rates
            self.returns = self.markov_bonds(self.n_months)

        elif self.asset_name == 'High Yield Savings':
            self.returns = self.markov_high_yield(self.n_months)

        elif self.asset_name == 'Peer-to-Peer Lending':
            self.returns = self.markov_p2p(self.n_months)

        elif self.asset_name == 'Individual Stocks':
            self.returns = self.markov_individual_stocks(self.n_months)

        elif self.asset_name == 'Cryptocurrency':
            self.returns = self.markov_crypto(self.n_months)

        elif self.asset_name == 'Other':
            self.returns = self.markov_other(self.n_months)

        else:
            # fallback: 0% returns
            self.returns = [0.0]*self.n_months

    def block_bootstrap(self, data, n_months):
        """
        Takes an array 'data' of historical monthly returns and
        picks random consecutive blocks of size self.block_size until we have n_months.
        """
        length = len(data)
        if length < self.block_size:
            # fallback
            return list(np.random.choice(data, size=n_months))

        out = []
        while len(out) < n_months:
            start_idx = random.randint(0, length - self.block_size)
            block = data[start_idx:start_idx+self.block_size]
            out.extend(block)
        return out[:n_months]

    # ------------------
    # Markov / State-based Approaches
    # ------------------

    def markov_bonds(self, n_months):
        """
        A toy Markov approach for bonds:
        States: "Normal" ~ 0.2% monthly, "RisingRate" ~ negative or low return, "FallingRate" ~ 0.4% monthly
        Transition probabilities are somewhat arbitrary.
        """
        # transitions: normal->normal (60%), normal->rising(20%), normal->falling(20%)
        # rising->normal(50%), rising->rising(30%), rising->falling(20%)
        # falling->normal(50%), falling->rising(20%), falling->falling(30%)
        states = ["normal", "rising", "falling"]
        transition = {
            "normal":   [0.6, 0.2, 0.2],
            "rising":   [0.5, 0.3, 0.2],
            "falling":  [0.5, 0.2, 0.3],
        }
        returns_map = {
            "normal":   lambda: np.random.normal(0.002, 0.001),   # ~0.2% monthly
            "rising":   lambda: np.random.normal(-0.001, 0.001),  # negative or near zero
            "falling":  lambda: np.random.normal(0.004, 0.001),   # ~0.4% monthly
        }

        # pick initial state
        current_state = random.choice(states)
        seq = []
        for _ in range(n_months):
            seq.append(returns_map[current_state]())
            # move to next
            probs = transition[current_state]
            r = random.random()
            cum = 0
            for i, p in enumerate(probs):
                cum += p
                if r <= cum:
                    current_state = states[i]
                    break
        return seq

    def markov_high_yield(self, n_months):
        """
        High-yield savings: mostly stable 0.1% to 0.2% monthly
        occasionally small dip or higher jump
        We'll do 2 states: stable(90%), bonus(10%)
        """
        states = ["stable", "bonus"]
        transition = {
            "stable": [0.9, 0.1],
            "bonus":  [0.8, 0.2],
        }
        returns_map = {
            "stable": lambda: np.random.normal(0.0016, 0.0004),
            "bonus":  lambda: np.random.normal(0.002, 0.0004),
        }
        current_state = random.choice(states)
        seq = []
        for _ in range(n_months):
            seq.append(returns_map[current_state]())
            r = random.random()
            cum = 0
            for i, p in enumerate(transition[current_state]):
                cum += p
                if r <= cum:
                    current_state = states[i]
                    break
        return seq

    def markov_p2p(self, n_months):
        """
        Peer-to-peer lending: ~5-6% annual net, but default cycles can cause lumps.
        We'll do states: normal, meltdown
        """
        states = ["normal", "meltdown"]
        transition = {
            "normal":   [0.95, 0.05],
            "meltdown": [0.7, 0.3]
        }
        # normal ~ 0.4% monthly, meltdown ~ -2% monthly
        returns_map = {
            "normal":   lambda: np.random.normal(0.004, 0.002),
            "meltdown": lambda: np.random.normal(-0.02, 0.01),
        }
        current_state = random.choice(states)
        seq = []
        for _ in range(n_months):
            seq.append(returns_map[current_state]())
            # transition
            r = random.random()
            cum = 0
            for i, p in enumerate(transition[current_state]):
                cum += p
                if r <= cum:
                    current_state = states[i]
                    break
        return seq

    def markov_individual_stocks(self, n_months):
        """
        Somewhat volatile, ~10% annual but with strong up/down states.
        States: bull, bear, sideways
        """
        states = ["bull", "bear", "sideways"]
        transition = {
            "bull":     [0.7, 0.1, 0.2],
            "bear":     [0.2, 0.6, 0.2],
            "sideways": [0.3, 0.2, 0.5],
        }
        returns_map = {
            "bull":     lambda: np.random.normal(0.015, 0.02),   # ~1.5% avg monthly
            "bear":     lambda: np.random.normal(-0.015, 0.02),
            "sideways": lambda: np.random.normal(0.0, 0.005),
        }
        current_state = random.choice(states)
        seq = []
        for _ in range(n_months):
            seq.append(returns_map[current_state]())
            r = random.random()
            cum = 0
            for i, p in enumerate(transition[current_state]):
                cum += p
                if r <= cum:
                    current_state = states[i]
                    break
        return seq

    def markov_crypto(self, n_months):
        """
        Crypto: can have big bull/bear cycles with high volatility.
        States: mania, crash, normal
        """
        states = ["mania", "crash", "normal"]
        transition = {
            "mania":  [0.7, 0.2, 0.1],
            "crash":  [0.1, 0.6, 0.3],
            "normal": [0.2, 0.3, 0.5],
        }
        returns_map = {
            "mania":  lambda: np.random.normal(0.05, 0.08),  # 5% mo avg
            "crash":  lambda: np.random.normal(-0.08, 0.08),
            "normal": lambda: np.random.normal(0.0, 0.03),
        }
        current_state = random.choice(states)
        seq = []
        for _ in range(n_months):
            seq.append(returns_map[current_state]())
            r = random.random()
            cum = 0
            for i, p in enumerate(transition[current_state]):
                cum += p
                if r <= cum:
                    current_state = states[i]
                    break
        return seq

    def markov_other(self, n_months):
        """
        Other: moderate ~7% annual, fairly stable or mid-vol.
        We'll do states: stable, mild_bull, mild_bear
        """
        states = ["stable", "mild_bull", "mild_bear"]
        transition = {
            "stable":     [0.6, 0.2, 0.2],
            "mild_bull":  [0.3, 0.5, 0.2],
            "mild_bear":  [0.4, 0.1, 0.5]
        }
        returns_map = {
            "stable":     lambda: np.random.normal(0.005, 0.003),
            "mild_bull":  lambda: np.random.normal(0.01, 0.005),
            "mild_bear":  lambda: np.random.normal(-0.005, 0.005),
        }
        current_state = random.choice(states)
        seq = []
        for _ in range(n_months):
            seq.append(returns_map[current_state]())
            r = random.random()
            cum = 0
            for i, p in enumerate(transition[current_state]):
                cum += p
                if r <= cum:
                    current_state = states[i]
                    break
        return seq

    # -------------
    # Helper method
    # -------------
    def get_return_for_month(self, month_idx):
        # month_idx is 0-based
        if month_idx < len(self.returns):
            return self.returns[month_idx]
        else:
            # If for some reason we exceed, return 0
            return 0.0


# ---- Classes ----

class Lease:
    def __init__(self, data):
        self.item_name = data.get('item_name', 'Leased Item')
        self.monthly_payment = data.get('monthly_payment', 0)
        self.lease_term_months = data.get('lease_term_months', 36)
        self.residual_value = data.get('residual_value', 0)
        self.buyout_option = data.get('buyout_option', False)
        self.months_elapsed = 0
        self.consider_in_net_worth = data.get('consider_in_net_worth', False)
        self.asset_value = data.get('asset_value', 0)
        self.asset_value_change = data.get('asset_value_change', 0)
        self.is_active = True

    def make_payment(self):
        if self.months_elapsed >= self.lease_term_months:
            self.is_active = False
            return 0
        self.months_elapsed += 1
        return self.monthly_payment

    def get_net_worth_impact(self):
        if self.consider_in_net_worth:
            return self.asset_value
        return 0

    def update_value(self):
        self.asset_value *= (1 + self.asset_value_change / 12)


class Home:
    def __init__(self, purchase_date, purchase_price, down_payment, mortgage_rate, mortgage_term_years,
                 property_tax_rate=0.02, hoa=0):
        self.purchase_date = ensure_date(purchase_date)
        self.purchase_price = purchase_price
        self.down_payment = down_payment
        self.mortgage_rate = mortgage_rate
        self.mortgage_term_years = mortgage_term_years
        self.loan_balance = self.purchase_price - self.down_payment
        self.initial_loan_balance = self.loan_balance
        self.interest_paid = 0
        self.home_value = self.purchase_price
        self.property_tax_rate = property_tax_rate
        self.hoa = hoa
        self.paid_off = False

        self.monthly_PI_payment = self.calculate_monthly_PI_payment()
        self.monthly_payment = self.calculate_monthly_payment()

        # We will do a block bootstrap approach for the entire mortgage term
        # to track property appreciation. But for simplicity, we do it once,
        # storing in a ReturnGenerator with enough months:
        self.term_months = max(360, self.mortgage_term_years * 12)  # ensure at least 30 yrs
        self.re_generator = ReturnGenerator("Rental Real Estate", self.term_months, block_size=12, real_estate_type="long term rentals")
        self.internal_month = 0

    def calculate_monthly_PI_payment(self):
        r = self.mortgage_rate / 12
        n = self.mortgage_term_years * 12
        P = self.purchase_price - self.down_payment
        if r == 0:
            return P / n
        payment = P * (r * (1 + r)**n) / ((1 + r)**n - 1)
        return payment

    def calculate_monthly_payment(self):
        PI_payment = self.calculate_monthly_PI_payment()
        insurance = self.purchase_price * 0.003 / 12
        taxes = self.home_value * self.property_tax_rate / 12
        return PI_payment + insurance + taxes + self.hoa

    def calculate_home_equity(self):
        return self.home_value - self.loan_balance

    def make_payment(self, date):
        date = ensure_date(date)
        # Apply appreciation from our stored sequence
        monthly_appreciation = self.re_generator.get_return_for_month(self.internal_month)
        self.internal_month += 1
        self.home_value *= (1 + monthly_appreciation)

        if self.paid_off:
            return 0

        r = self.mortgage_rate / 12
        interest = self.loan_balance * r
        principal = self.monthly_PI_payment - interest

        self.loan_balance -= principal
        self.interest_paid += interest

        self.home_equity = self.calculate_home_equity()

        if self.loan_balance <= 0:
            self.paid_off = True
            self.loan_balance = 0
            self.home_equity = self.home_value

        return self.monthly_payment

    def __str__(self):
        return (f"Home Purchase Price: {self.purchase_price}, "
                f"Down Payment: {self.down_payment}, Mortgage Rate: {self.mortgage_rate}, "
                f"Mortgage Term: {self.mortgage_term_years}, Home Equity: {self.home_equity}, "
                f"Home Value: {self.home_value}, Monthly Payment: {self.monthly_payment}, Paid Off: {self.paid_off}")


class IncomeSource:
    def __init__(self, data):
        self.income_type = data.get('income_type', 'salary/hourly')
        self.name = data.get('name', 'Primary Income')
        self.has_growth = data.get('has_growth', False)
        self.growth_type = data.get('growth_type', 'percentage') if self.has_growth else None
        if self.has_growth and self.growth_type == 'percentage':
            self.growth_percentage = data.get('growth_percentage', 0.03) / 100
        else:
            self.growth_percentage = None

        self.last_update = None
        self.current_value = 0
        self.random_state = np.random.RandomState()

        if self.income_type == 'salary/hourly':
            self.amount = data.get('amount', 50000)
            self.frequency = data.get('frequency', 'annual')
            self.overtime_eligible = data.get('overtime_eligible', False)
            if self.overtime_eligible:
                self.overtime_rate = data.get('overtime_rate', 1.5)
                self.monthly_overtime_hours = data.get('monthly_overtime_hours', 12)

        elif self.income_type == 'bonus':
            self.amount = data.get('amount', 5000)
            self.bonus_frequency = data.get('bonus_frequency', 'annual')
            self.months_until_next_bonus = self.get_months_until_next_bonus(self.bonus_frequency)

        elif self.income_type == 'stock_options':
            self.stock_options_type = data.get('stock_options_type', 'pre_ipo')
            self.number_of_options = data.get('number_of_options', 10000)
            self.strike_price = data.get('strike_price', 1.0)
            self.vesting_period = data.get('vesting_period', 4)
            self.vesting_cliff = data.get('vesting_cliff', 1)
            self.vesting_frequency = data.get('vesting_frequency', 'monthly')
            self.current_stock_price = data.get('current_stock_price', 10.0) if self.stock_options_type == 'post_ipo' else None
            self.estimated_ipo_price = data.get('estimated_ipo_price', 20.0) if self.stock_options_type == 'pre_ipo' else None
            self.estimated_ipo_date = ensure_date(data.get('estimated_ipo_date', datetime.datetime.now().date() + timedelta(days=365*2))) if self.stock_options_type == 'pre_ipo' else None
            self.average_time_at_job = data.get('average_time_at_job', 3.5)
            self.time_at_job_std_dev = data.get('time_at_job_std_dev', 1.5)
            self.exercise_strategy = data.get('exercise_strategy', 'hold_until_exit')
            self.custom_exercise_percentage = data.get('custom_exercise_percentage', 50.0) if self.exercise_strategy == 'custom' else None
            self.vested_options = 0
            self.total_vested_options = 0
            self.months_at_job = 0
            self.exercised_options = 0
            self.job_duration = max(1, int(self.random_state.normal(self.average_time_at_job, self.time_at_job_std_dev) * 12))
            self.option_type = data.get('option_type', 'ISO')  # or 'NSO'
            self.eighty_three_b = data.get('eighty_three_b', False)

        elif self.income_type == 'rental':
            self.number_of_units = data.get('number_of_units', 1)
            self.rent_per_unit = data.get('rent_per_unit', 1000.0)
            self.rental_state = data.get('rental_state', 'California')
            self.non_tax_costs_percentage = data.get('non_tax_costs_percentage', 10.0) / 100
            self.has_mortgage = data.get('has_mortgage', True)
            if self.has_mortgage:
                self.mortgage_monthly_payment = data.get('mortgage_monthly_payment', 1500.0)
                self.mortgage_interest_rate = data.get('mortgage_interest_rate', 3.5) / 100
                self.mortgage_remaining_years = data.get('mortgage_remaining_years', 30)
            self.occupancy_rate = data.get('occupancy_rate', 95.0) / 100
            self.property_management_fee = data.get('property_management_fee', 8.0) / 100
            self.property_value = self.number_of_units * self.rent_per_unit * 100
            self.home = Home(datetime.datetime.now().date(), self.property_value, self.property_value * 0.2,
                             self.mortgage_interest_rate, self.mortgage_remaining_years)

        elif self.income_type == 'gig_work':
            self.gigs_per_month = data.get('gigs_per_month', 20)
            self.average_take_home_per_gig = data.get('average_take_home_per_gig', 100.0)
            self.gig_expenses_percentage = data.get('gig_expenses_percentage', 20.0) / 100
            self.gig_work_hours_per_month = data.get('gig_work_hours_per_month', 80)
        elif self.income_type == 'commission':
            self.commission_type = data.get('commission_type', 'percentage')
            if self.commission_type == 'percentage':
                self.commission_percentage = data.get('commission_percentage', 5.0) / 100
            else:
                self.commission_fixed_amount = data.get('commission_fixed_amount', 1000.0)
            self.sales_target = data.get('sales_target', 100000)
            self.sales_standard_deviation = data.get('sales_standard_deviation', 20000)
            self.commission_cap = data.get('commission_cap', 0)
        elif self.income_type == 'government_assistance':
            self.amount = data.get('amount', 1000)
            self.frequency = data.get('frequency', 'monthly')
        elif self.income_type == 'other':
            self.amount = data.get('amount', 1000)
            self.frequency = data.get('frequency', 'monthly')

    def get_months_until_next_bonus(self, frequency):
        if frequency == 'monthly':
            return 1
        elif frequency == 'quarterly':
            return 3
        elif frequency == 'biannual':
            return 6
        elif frequency == 'annual':
            return 12
        else:
            return 12

    def update(self, current_date):
        if self.has_growth and self.last_update:
            months_elapsed = (current_date.year - self.last_update.year)*12 + (current_date.month - self.last_update.month)
            if self.growth_type == 'percentage' and hasattr(self, 'amount'):
                growth_factor = (1 + self.growth_percentage) ** (months_elapsed/12)
                self.amount *= growth_factor
        self.last_update = current_date

    def get_monthly_income(self, current_date, user_age):
        income = 0
        if self.income_type == 'salary/hourly':
            if self.frequency == 'annual':
                income = self.amount / 12
                hourly_rate = self.amount / (40*52)
            elif self.frequency == 'monthly':
                income = self.amount
                hourly_rate = (self.amount*12)/(40*52)
            elif self.frequency == 'weekly':
                income = self.amount * 4.33
                hourly_rate = self.amount / 40
            elif self.frequency == 'biweekly':
                income = self.amount * 2.17
                hourly_rate = (self.amount*26)/(40*52)
            elif self.frequency == 'hourly':
                income = self.amount * 40 * 4.33
                hourly_rate = self.amount
            else:
                hourly_rate = 0

            if self.overtime_eligible:
                overtime_income = self.monthly_overtime_hours * hourly_rate * self.overtime_rate
                income += overtime_income

        elif self.income_type == 'bonus':
            if self.months_until_next_bonus == 0:
                income = self.amount
                self.months_until_next_bonus = self.get_months_until_next_bonus(self.bonus_frequency)
            else:
                self.months_until_next_bonus -= 1

        elif self.income_type == 'stock_options':
            # no direct monthly income
            income = 0
            self.months_at_job += 1
            if self.months_at_job >= self.job_duration:
                self.vested_options = 0
                self.total_vested_options = 0
                self.exercised_options = 0
                self.months_at_job = 0
                self.job_duration = max(1, int(self.random_state.normal(self.average_time_at_job, self.time_at_job_std_dev)*12))

        elif self.income_type == 'rental':
            gross = self.number_of_units*self.rent_per_unit*self.occupancy_rate
            expenses = gross*self.non_tax_costs_percentage + gross*self.property_management_fee
            if self.has_mortgage:
                expenses += self.home.make_payment(current_date)
            income = gross - expenses

        elif self.income_type == 'gig_work':
            gross_income = self.gigs_per_month*self.average_take_home_per_gig
            expenses = gross_income*self.gig_expenses_percentage
            income = gross_income - expenses

        elif self.income_type == 'commission':
            sales = self.random_state.normal(self.sales_target, self.sales_standard_deviation)
            if self.commission_type == 'percentage':
                commission = sales*self.commission_percentage
            else:
                commission = self.commission_fixed_amount
            if self.commission_cap>0:
                commission = min(commission, self.commission_cap)
            income = commission/12

        elif self.income_type == 'government_assistance':
            if self.frequency == 'monthly':
                income = self.amount
            elif self.frequency == 'annual':
                income = self.amount/12

        elif self.income_type == 'other':
            if self.frequency=='monthly':
                income = self.amount
            elif self.frequency=='annual':
                income = self.amount/12

        self.current_value = income
        return income

    def get_net_worth_contribution(self, current_date):
        """
        Enhanced with 83(b) + ISO/NSO approximation:
          - If 83(b) is chosen, we assume tax is paid at the time of grant on the difference (strike vs. FMV).
          - For ISO, we assume no immediate ordinary income but potential AMT in real scenario. Simplify here.
          - For NSO, the spread is taxed as ordinary income at exercise. Simplify as well.
        We'll just return current "option value" minus any "tax we assume was paid." (This is simplified.)
        """
        net_worth = 0
        if self.income_type == 'stock_options':
            months_since_start = self.months_at_job
            if months_since_start >= self.vesting_cliff*12:
                total_vesting_months = self.vesting_period*12 - self.vesting_cliff*12
                if total_vesting_months>0:
                    if self.vesting_frequency=='monthly':
                        vest_inc = float(self.number_of_options)/total_vesting_months
                    elif self.vesting_frequency=='quarterly':
                        vest_inc = float(self.number_of_options)/(total_vesting_months/3)
                    elif self.vesting_frequency=='annually':
                        vest_inc = float(self.number_of_options)/(self.vesting_period-self.vesting_cliff)
                    else:
                        vest_inc = float(self.number_of_options)/total_vesting_months
                    self.vested_options += vest_inc
                    self.total_vested_options = min(self.vested_options, self.number_of_options)

            # Determine if stock is liquid
            if self.stock_options_type=='post_ipo':
                # add noise
                noisy_price = max(0, (self.current_stock_price or 10) + np.random.normal(0, (self.current_stock_price or 10)*0.05))
                option_value = max(0, noisy_price - self.strike_price)
            else:
                if current_date>= (self.estimated_ipo_date or datetime.date.today()):
                    # IPO has occurred
                    noisy_price = max(0, (self.estimated_ipo_price or 20) + np.random.normal(0, (self.estimated_ipo_price or 20)*0.10))
                    option_value = max(0, noisy_price - self.strike_price)
                else:
                    option_value = 0

            # 83(b) election approximation:
            # if 83(b) is true, we assume the user already paid tax on the difference at grant time
            # so no big ordinary income at vest, but the net worth is the final value
            # The code below is highly simplified. Real 83(b) is more complex with AMT, etc.
            if self.eighty_three_b:
                # We ignore the big tax event here, assume it was paid from outside. 
                # net_worth is the vested portion's "market minus strike" if price>strike
                net_worth += (self.total_vested_options - self.exercised_options)*option_value
            else:
                # If ISO or NSO without 83(b), we assume net_worth is the unrealized gain 
                # that would be subject to tax at exercise. We'll just show it fully here
                net_worth += (self.total_vested_options - self.exercised_options)*option_value

        return net_worth


class BudgetItem:
    def __init__(self, data):
        self.type = data.get('type', 'rent')
        self.name = data.get('name', self.type) if self.type != 'other' else data.get('name', 'Other')
        self.value = data.get('value', 2000.0)
        self.frequency = data.get('frequency', 'monthly')
        self.changes_if_not_working = data.get('changes_if_not_working', False)
        self.value_if_not_working = data.get('value_if_not_working', self.value) if self.changes_if_not_working else self.value
        self.last_update = None

    def update(self, inflation_rate):
        self.value *= (1 + inflation_rate/12)
        if self.changes_if_not_working:
            self.value_if_not_working *= (1 + inflation_rate/12)

    def get_monthly_expense(self, working=True):
        val = self.value if (working or not self.changes_if_not_working) else self.value_if_not_working
        if self.frequency=='monthly':
            return val
        elif self.frequency=='weekly':
            return val*4.33
        elif self.frequency=='annual':
            return val/12
        else:
            return val


class AssetOrDebt:
    def __init__(self, data):
        self.type = data.get('type', 'Checking Account')
        self.name = data.get('name', self.type)
        self.value = data.get('value', 0.0)
        self.remaining_term = data.get('remaining_term', 0)
        self.is_debt = self.type in ['Credit Card Debt', 'Auto Loan', 'Personal Loan', 'Student Loan', 'Mortgage', 'Other Debts']
        self.is_asset = not self.is_debt

        default_interest_rates = {
            'Checking Account': 0.0001,
            'Savings Account': 0.01,
            'Certificate of Deposit': 0.02,
            'Retirement Accounts': 0.07,
            'Investment Account': 0.07,
            'Real Estate': 0.03,
            'Credit Card Debt': 0.18,
            'Auto Loan': 0.05,
            'Personal Loan': 0.08,
            'Student Loan': 0.04,
            'Mortgage': 0.04,
            'Other Debts': 0.10,
        }

        interest_rate_input = data.get('interest_rate', None)
        if interest_rate_input is not None:
            self.interest_rate = interest_rate_input / 100.0
        else:
            self.interest_rate = default_interest_rates.get(self.type, 0.0)

        self.monthly_payment = self.calculate_monthly_payment()
        self.original_balance = self.value

    def calculate_monthly_payment(self):
        if self.is_debt and self.remaining_term>0:
            r = self.interest_rate/12
            n = self.remaining_term*12
            P = self.value
            if r==0:
                return P/n
            pay = P*(r*(1+r)**n)/((1+r)**n-1)
            return pay
        else:
            return 0

    def update(self):
        if self.is_asset:
            # asset appreciates
            self.value *= (1 + self.interest_rate/12)
            return 0
        elif self.is_debt and self.remaining_term>0:
            interest = self.value*(self.interest_rate/12)
            principal = self.monthly_payment - interest
            if principal<0:
                self.value += -principal
                cash_flow = self.monthly_payment
            else:
                self.value -= principal
                cash_flow = self.monthly_payment
            self.remaining_term -= 1/12

            if self.value<=0:
                leftover = -self.value if self.value<0 else 0
                self.value = 0
                self.remaining_term = 0
                cash_flow += leftover
            return cash_flow
        else:
            return 0


class Milestone:
    def __init__(self, data):
        self.date = ensure_date(data.get('date', datetime.datetime.now().date()))
        self.buy_a_house = data.get('buy_a_house', False)
        self.change_location = data.get('change_location', False)
        self.major_expense = data.get('major_expense', False)
        self.change_income = data.get('change_income', False)
        self.change_budget = data.get('change_budget', False)
        self.major_windfall = data.get('major_windfall', False)
        self.family_change = data.get('family_change', False)
        self.data = data


class InvestmentVehicle:
    """
    Wraps a ReturnGenerator for the asset_name, ratio, real_estate_investment_type.
    We pre-generate N months of returns for the entire simulation, then each month we
    fetch the next return from that sequence.
    """
    def __init__(self, name, ratio, real_estate_investment_type="REIT", total_months=360):
        self.name = name
        self.ratio = ratio/100
        self.real_estate_investment_type = real_estate_investment_type
        self.current_month_idx = 0
        self.total_months = total_months

        # Pre-generate the monthly return sequence using our ReturnGenerator
        self.return_gen = ReturnGenerator(
            asset_name = self.name,
            n_months = self.total_months,
            block_size = 12,
            real_estate_type = self.real_estate_investment_type
        )

    def get_monthly_return(self):
        if self.current_month_idx>= self.total_months:
            return 0.0
        r = self.return_gen.get_return_for_month(self.current_month_idx)
        self.current_month_idx += 1
        return r


# ----------------- MAIN User CLASS -----------------
class User:
    def __init__(self, user_data):
        self.time_series = pd.DataFrame()
        self.time = datetime.datetime.now().date()
        self.month = 0
        self.retirement_age = None
        self.net_worth = 0
        self.is_retired = False
        self.working = True
        self.retirement_check_months = 0
        self.last_reduced_income_check_month = 0
        self.custom_tax_brackets = user_data.get('custom_tax_brackets', None)
        self.leases = []
        self.yearly_income = 0
        self.yearly_taxes = 0
        self.func = None
        self.kwargs = {}
        self.yearly_expenses = 0
        self.social_security_age = 67
        self.load_user_data(user_data)

    def load_user_data(self, data):
        self.age = data.get('age', 22)
        self.birth_year = datetime.datetime.now().year - self.age
        self.state = data.get('state', 'California')
        self.married = data.get('married', True)
        self.spouse_age = data.get('spouse_age', 22) if self.married else None
        self.dependents = data.get('dependents', 0)

        self.simulate_years = data.get('simulate_years', 10)
        self.num_simulations = data.get('num_simulations', 10)
        self.inflation = data.get('inflation', 0.03)

        # Income
        self.income_sources = [IncomeSource(i) for i in data.get('income', [])]

        # Budget
        self.budget_items = [BudgetItem(b) for b in data.get('budget_items', [])]
        self.expenditure_growth_beyond_inflation = data.get('expenditure_growth_beyond_inflation', 0.03)

        # Assets & Debts
        self.assets_and_debts = [AssetOrDebt(a) for a in data.get('assets_and_debts', [])]

        # cash + investment
        self.cash = sum(a.value for a in self.assets_and_debts if a.type in ['Checking Account', 'Savings Account'])
        self.investment_balance = sum(a.value for a in self.assets_and_debts
                                      if a.type in ['Retirement Accounts', 'Brokerage Account','Investment Account',
                                                    'Certificate of Deposit'])

        # Read investment allocations
        self.investment_allocations = {}
        total_allocation = 0
        for key in ['Index Funds', 'Bonds', 'Rental Real Estate', 'Retirement Accounts', 
                    'High Yield Savings','Peer-to-Peer Lending', 'Individual Stocks', 
                    'Cryptocurrency', 'Other']:
            allocation = data.get(f'investment_{key.lower().replace(" ", "_")}', 0)
            self.investment_allocations[key] = allocation
            total_allocation += allocation
        if total_allocation != 100:
            raise ValueError("Investment allocations must sum to 100%")

        # Real estate investment type
        real_estate_investment_type = data.get('real_estate_investment_type', "REIT")

        # Pre-generate monthly returns for the entire simulation
        self.total_months_to_sim = self.simulate_years*12

        self.investment_vehicles = []
        for name, ratio in self.investment_allocations.items():
            if ratio>0:
                if name=='Rental Real Estate':
                    self.investment_vehicles.append(InvestmentVehicle(name, ratio, 
                                    real_estate_investment_type=real_estate_investment_type,
                                    total_months=self.total_months_to_sim))
                else:
                    self.investment_vehicles.append(InvestmentVehicle(name, ratio, 
                                    total_months=self.total_months_to_sim))

        # We store each vehicle's allocated balance
        self.vehicle_balances = {v.name: v.ratio*self.investment_balance for v in self.investment_vehicles}

        # Milestones
        self.milestones = [Milestone(m) for m in data.get('milestones', [])]

        # Retirement
        self.retirement_goal_method = data.get('retirement_goal_method', 'Safe Withdrawal Rate')
        if self.retirement_goal_method == 'Safe Withdrawal Rate':
            self.post_retirement_expenses = data.get('post_retirement_expenses', 0)
            self.average_post_retirement_income = data.get('average_post_retirement_income', 0)
            self.withdrawal_rate = data.get('withdrawal_rate', 0.04)
            self.adjust_for_inflation = data.get('adjust_for_inflation', True)
        elif self.retirement_goal_method == 'Simulate Additional Years with Reduced Income':
            self.remove_income_sources = data.get('remove_income_sources', {})
            self.additional_retirement_income = data.get('additional_retirement_income', 0)
            self.additional_simulation_years = data.get('additional_simulation_years', 30)
        elif self.retirement_goal_method == 'Fixed Value':
            self.fixed_retirement_goal = data.get('fixed_retirement_goal', 3000000.0)  # default 3M

        self.state_tax_data = get_state_tax_data(self.state)

        self.emergency_fund_target = 6*self.calculate_monthly_expenses()
        self.average_life_event_cost = 1000
        self.life_events_per_year = 1
        self.life_events_std_dev = 1000

        self.location = {'city': '', 'country': self.state}
        self.home = None
        self.func = data.get('func', None)
        if self.func:
            self.func+= self.get_execution_line()

    def get_execution_line(self):
        if self.func and (not hasattr(self, 'func') or not callable(self.func)):
            pass
        if self.func and (not hasattr(self, 'kwargs') or not isinstance(self.kwargs, dict)):
            pass
        if self.func:
            func_name = self.func.__name__ if hasattr(self.func, '__name__') else "unknown_func"
            kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
            return f"\n{func_name}(self, {kwargs_str})"
        return ""

    def calculate_monthly_income(self):
        # include social security if age >= self.social_security_age and not retired
        total = sum(i.get_monthly_income(self.time, self.age) 
                    for i in self.income_sources if self.working or i.income_type=='rental')
        if self.age>= self.social_security_age and not self.is_retired:
            total+= 1500  # simplified
        return total

    def calculate_monthly_expenses(self):
        total = sum(b.get_monthly_expense(working=self.working) for b in self.budget_items)
        lease_expenses = sum(l.monthly_payment for l in self.leases if l.is_active)
        return total+lease_expenses

    def calculate_federal_tax(self, income):
        if self.custom_tax_brackets:
            return self.calculate_custom_tax(income)
        brackets = [
            (9875, 0.10),
            (40125, 0.12),
            (85525, 0.22),
            (163300, 0.24),
            (207350, 0.32),
            (518400, 0.35),
            (float('inf'), 0.37),
        ]
        deduction = 24800 if self.married else 12400
        taxable_income = max(0, income - deduction)
        tax = 0
        prev_limit=0
        for limit, rate in brackets:
            bracket_size = limit - prev_limit
            if taxable_income> bracket_size:
                tax += bracket_size*rate
                taxable_income -= bracket_size
                prev_limit = limit
            else:
                tax += taxable_income*rate
                break
        return tax

    def calculate_state_tax(self, income):
        """Progressively calculate state tax based on income brackets."""
        if self.custom_tax_brackets:
            return 0
        if self.state_tax_data and self.state_tax_data['income_tax'] != 'none':
            tax = 0
            taxable_income = income
            prev_limit = 0
            for bracket in self.state_tax_data['income_tax']:
                limit = bracket['bracket']
                rate = bracket['rate'] / 100
                bracket_size = limit - prev_limit
                if taxable_income > bracket_size:
                    tax += bracket_size * rate
                    taxable_income -= bracket_size
                    prev_limit = limit
                else:
                    tax += taxable_income * rate
                    break
            return tax
        return 0

    def calculate_custom_tax(self, income):
        brackets = self.custom_tax_brackets
        sorted_brackets = sorted(brackets.items(), key=lambda x: float(x[0]))
        taxable = income
        tax=0
        prev_limit=0
        for limit, rate in sorted_brackets:
            limit = float(limit)
            if taxable> limit:
                tax+= (limit-prev_limit)*rate
                prev_limit = limit
            else:
                tax+= (taxable-prev_limit)*rate
                break
        return tax

    def calculate_taxes(self, income):
        federal = self.calculate_federal_tax(income)
        state = self.calculate_state_tax(income)
        # FICA with wage base
        wage_base=160200
        fica=0
        if income> wage_base:
            fica+= wage_base*0.0765
            fica+= (income-wage_base)*0.0145
        else:
            fica+= income*0.0765
        total = federal+state+fica
        ctc = min(self.dependents*2000, total)
        return max(0, total- ctc)

    def handle_milestones(self):
        for m in self.milestones:
            if (self.time.year==m.date.year) and (self.time.month==m.date.month):
                if m.family_change:
                    self.handle_family_change(m.data)
                if m.buy_a_house:
                    self.handle_buy_house(m.data)
                if m.major_windfall:
                    self.handle_major_windfall(m.data)
                if m.change_location:
                    self.handle_change_location(m.data)
                if m.major_expense:
                    self.handle_major_expense(m.data)

    def handle_family_change(self, data):
        ctype = data.get('family_change_type','marriage')
        if ctype=='marriage':
            self.married=True
            self.spouse_age = data.get('spouse_age', self.age)
        elif ctype=='birth':
            self.dependents+= 2 if data.get('twins',False) else 1
        elif ctype=='divorce':
            self.married=False
        elif ctype=='death':
            self.dependents = max(0, self.dependents-1)
        elif ctype=='dependant_adult':
            self.dependents+= data.get('number_of_dependant_adults',1)

    def handle_buy_house(self, data):
        hp = data.get('house_price', 300000.0)
        dp = data.get('down_payment', 60000.0)
        mr = data.get('mortgage_rate', 0.04)
        my = data.get('mortgage_term_years', 30)
        ptr= data.get('property_tax_rate', 0.02)
        hoa= data.get('hoa', 0)
        self.cash-= dp
        self.home = Home(self.time, hp, dp, mr, my, ptr, hoa)
        # remove rent from budget
        self.budget_items = [b for b in self.budget_items if b.type!='rent']
        item_data = {
            'type': 'mortgage',
            'name': 'Mortgage Payment',
            'value': self.home.monthly_payment,
            'frequency': 'monthly'
        }
        self.budget_items.append(BudgetItem(item_data))

    def handle_major_windfall(self, data):
        amt = data.get('windfall_amount', 0)
        self.cash+= amt

    def handle_change_location(self, data):
        self.location['country'] = data.get('country', self.location['country'])
        self.location['city'] = data.get('city', self.location['city'])
        moving_cost = data.get('moving_cost', 5000.0)
        if self.investment_balance>= moving_cost:
            self.investment_balance-= moving_cost
        else:
            needed = moving_cost- self.investment_balance
            self.investment_balance=0
            self.cash-= needed
        expense_adj = data.get('expense_adjustment','Leave expenses the same')
        if expense_adj=='Adjust for similar quality of life':
            from_city= data.get('from_city','Current City')
            to_city= self.location['city']
            col_from= self.get_cost_of_living_index(from_city)
            col_to= self.get_cost_of_living_index(to_city)
            if col_from and col_to:
                factor = col_to/col_from
                for i in self.budget_items:
                    i.value*= factor
                    if i.changes_if_not_working:
                        i.value_if_not_working*= factor
        elif expense_adj=='Manual adjustment':
            manual_factor= data.get('manual_expense_adjustment',1.0)
            for i in self.budget_items:
                i.value*= manual_factor
                if i.changes_if_not_working:
                    i.value_if_not_working*= manual_factor

    def get_cost_of_living_index(self, city_name):
        city_data= col_data[col_data['city'].str.lower()== city_name.lower()]
        if not city_data.empty:
            return city_data.iloc[0]['x54']
        return None

    def handle_major_expense(self, data):
        cost= data.get('total_cost',0)
        ptype= data.get('purchase_type','cash')
        if ptype=='cash':
            self.cash-= cost
        elif ptype=='finance':
            dp= data.get('down_payment',0)
            loan_amt= data.get('loan_amount', cost-dp)
            ir= data.get('interest_rate',0.05)/100
            term= data.get('loan_term_months',36)
            self.cash-= dp
            d= AssetOrDebt({
                'type': 'Personal Loan',
                'name': data.get('item_name','Major Purchase'),
                'value': loan_amt,
                'interest_rate': ir*100,
                'remaining_term': term/12
            })
            self.assets_and_debts.append(d)
        elif ptype=='lease':
            mp= data.get('monthly_payment',0)
            ltm= data.get('lease_term_months',36)
            rv= data.get('residual_value',0)
            bo= data.get('buyout_option',False)
            cinw= data.get('consider_in_net_worth',False)
            av= data.get('asset_value',0)
            avc= data.get('asset_value_change',0)
            ls= Lease({
                'item_name': data.get('item_name','Leased Item'),
                'monthly_payment': mp,
                'lease_term_months': ltm,
                'residual_value': rv,
                'buyout_option': bo,
                'consider_in_net_worth': cinw,
                'asset_value': av,
                'asset_value_change': avc
            })
            self.leases.append(ls)

    def update_leases(self):
        for l in self.leases:
            if l.is_active:
                payment= l.make_payment()
                self.cash-= payment
                l.update_value()

    def calculate_investment_return(self):
        """
        Steps each vehicle's monthly return, updates that portion
        of the portfolio, and sums up for self.investment_balance.
        """
        for vehicle in self.investment_vehicles:
            monthly_r = vehicle.get_monthly_return()
            balance_before = self.vehicle_balances[vehicle.name]
            new_balance = balance_before*(1+ monthly_r)
            self.vehicle_balances[vehicle.name] = new_balance
        self.investment_balance = sum(self.vehicle_balances.values())

    def update_assets_and_debts(self):
        total_pmt=0
        for ad in self.assets_and_debts:
            p= ad.update()
            total_pmt+= p
        if self.cash>= total_pmt:
            self.cash-= total_pmt
        else:
            needed= total_pmt- self.cash
            self.cash=0
            if self.investment_balance>= needed:
                self.liquidate_investments(needed)
            else:
                self.investment_balance=0

    def liquidate_investments(self, amount):
        total = self.investment_balance
        if total<=0:
            return
        for v in self.investment_vehicles:
            bal= self.vehicle_balances[v.name]
            if bal<=0: continue
            proportion= bal/ total
            sell = proportion*amount
            if sell> bal:
                sell= bal
            self.vehicle_balances[v.name]-= sell
        self.investment_balance= sum(self.vehicle_balances.values())
        self.cash+= amount

    def calculate_net_worth(self):
        net = self.investment_balance + self.cash
        net+= sum(a.value for a in self.assets_and_debts if a.is_asset)
        net-= sum(a.value for a in self.assets_and_debts if a.is_debt)
        net+= sum(i.get_net_worth_contribution(self.time) for i in self.income_sources)
        if self.home:
            net+= (self.home.home_value - self.home.loan_balance)
        net+= sum(l.get_net_worth_impact() for l in self.leases)
        return net

    def pay_annual_taxes(self):
        tx= self.calculate_taxes(self.yearly_income)
        if self.cash>= tx:
            self.cash-= tx
        else:
            needed= tx- self.cash
            self.cash=0
            if self.investment_balance>= needed:
                self.liquidate_investments(needed)
            else:
                self.investment_balance=0
        self.yearly_taxes= tx
        self.yearly_income=0
        self.yearly_expenses=0

    def manage_cash(self):
        # keep 6 mo of expenses + 3 mo of income
        desired = self.emergency_fund_target + 3*self.calculate_monthly_income()
        if self.cash> desired:
            excess= self.cash- desired
            self.cash-= excess
            self.add_investments(excess)
        elif self.cash< desired:
            needed= desired- self.cash
            if self.investment_balance>= needed:
                self.liquidate_investments(needed)
            else:
                self.cash+= self.investment_balance
                self.investment_balance=0

    def add_investments(self, amount):
        total_ratio = sum(v.ratio for v in self.investment_vehicles)
        if total_ratio<=0:
            return
        for v in self.investment_vehicles:
            share= (v.ratio/ total_ratio)* amount
            self.vehicle_balances[v.name]+= share
        self.investment_balance= sum(self.vehicle_balances.values())

    def record_monthly_data(self, income, expenses):
        row = {
            'month': self.month,
            'age': self.age,
            'income': income,
            'expenses': expenses,
            'taxes': None,  # annual lumpsum
            'cash': self.cash,
            'investment_balance': self.investment_balance,
            'net_worth': self.net_worth,
            'time': self.time,
            'working': self.working,
            'home_value': self.home.home_value if self.home else 0,
            'home_equity': (self.home.home_value - self.home.loan_balance) if self.home else 0,
            'home_loan_balance': self.home.loan_balance if self.home else 0,
        }
        # add each vehicle's balance
        for v in self.investment_vehicles:
            row[f'vehicle_balance_{v.name}'] = self.vehicle_balances[v.name]
        # budget items
        for b in self.budget_items:
            row[f'budget_{b.name}'] = b.get_monthly_expense(self.working)
        # assets and debts
        for ad in self.assets_and_debts:
            prefix= 'asset_' if ad.is_asset else 'debt_'
            row[f'{prefix}{ad.name}'] = ad.value
        # incomes
        for i_src in self.income_sources:
            row[f'income_{i_src.name}'] = i_src.current_value
        # leases
        for idx, l in enumerate(self.leases):
            row[f'lease_{l.item_name}_{idx}_payment'] = l.monthly_payment
            row[f'lease_{l.item_name}_{idx}_asset_value'] = l.asset_value if l.consider_in_net_worth else 0

        self.time_series = pd.concat([self.time_series, pd.DataFrame([row])], ignore_index=True)

    def check_retirement(self):
        if self.retirement_goal_method=='Safe Withdrawal Rate':
            req = (self.post_retirement_expenses - self.average_post_retirement_income)/ self.withdrawal_rate
            if self.net_worth>= req:
                self.is_retired= True
                return True
            else:
                if self.adjust_for_inflation:
                    self.post_retirement_expenses*= (1+ self.inflation/12)
                return False

        elif self.retirement_goal_method=='Simulate Additional Years with Reduced Income':
            if (self.month- self.last_reduced_income_check_month)< 6:
                return False
            self.last_reduced_income_check_month= self.month
            if self.net_worth>= 10* self.calculate_monthly_expenses()*12:
                init_nw= self.net_worth
                pass_count=0
                for _ in range(10):
                    sim_clone= self.clone_user_for_reduced_income_sim(10)
                    sim_clone.run_simulation()
                    if sim_clone.net_worth>= 0.9* init_nw:
                        pass_count+=1
                if pass_count==10:
                    self.is_retired= True
                    return True
            return False

        elif self.retirement_goal_method=='Fixed Value':
            if hasattr(self, 'fixed_retirement_goal'):
                if self.net_worth>= self.fixed_retirement_goal:
                    self.is_retired= True
                    return True
            return False

        return False

    def clone_user_for_reduced_income_sim(self, future_years):
        import copy
        sim_clone = User({})
        sim_clone.time_series = pd.DataFrame()
        sim_clone.time= self.time
        sim_clone.month= 0
        sim_clone.age= self.age
        sim_clone.dependents= self.dependents
        sim_clone.married= self.married
        sim_clone.state= self.state
        sim_clone.retirement_goal_method= self.retirement_goal_method
        sim_clone.average_post_retirement_income= getattr(self, 'average_post_retirement_income',0)
        sim_clone.post_retirement_expenses= getattr(self, 'post_retirement_expenses',0)
        sim_clone.withdrawal_rate= getattr(self, 'withdrawal_rate',0.04)
        sim_clone.adjust_for_inflation= getattr(self, 'adjust_for_inflation', True)
        sim_clone.additional_simulation_years= getattr(self, 'additional_simulation_years',30)

        # finances
        sim_clone.cash= self.cash
        sim_clone.investment_balance= self.investment_balance
        sim_clone.vehicle_balances= copy.deepcopy(self.vehicle_balances)

        sim_clone.inflation= self.inflation
        sim_clone.expenditure_growth_beyond_inflation= self.expenditure_growth_beyond_inflation

        sim_clone.budget_items = copy.deepcopy(self.budget_items)
        sim_clone.leases = copy.deepcopy(self.leases)
        sim_clone.assets_and_debts = [copy.deepcopy(a) for a in self.assets_and_debts]

        if self.home is not None:
            sim_clone.home= copy.deepcopy(self.home)
        else:
            sim_clone.home= None

        # remove certain incomes
        sim_clone.income_sources= []
        for i_src in self.income_sources:
            ic= copy.deepcopy(i_src)
            if ic.income_type in getattr(self, 'remove_income_sources', {}):
                action= self.remove_income_sources[ic.income_type]
                if action=='remove':
                    continue
                elif action=='zero':
                    ic.amount= 0
            sim_clone.income_sources.append(ic)

        sim_clone.milestones = []
        sim_clone.emergency_fund_target= self.emergency_fund_target
        sim_clone.state_tax_data= self.state_tax_data
        sim_clone.simulate_years= future_years
        sim_clone.is_retired= True
        sim_clone.working= False

        # Re-create investment vehicles with same ratio, total_months etc.
        sim_clone.investment_vehicles= []
        for v in self.investment_vehicles:
            # brand new ReturnGenerator if we want a new random path
            sim_clone.investment_vehicles.append(InvestmentVehicle(v.name, v.ratio*100,
                real_estate_investment_type=v.real_estate_investment_type, total_months= future_years*12))

        return sim_clone

    def step_month(self):
        self.month+=1
        self.time+= timedelta(days=30)
        self.age+= 1/12

        self.handle_milestones()

        for i_src in self.income_sources:
            i_src.update(self.time)

        for b in self.budget_items:
            b.update(self.inflation + self.expenditure_growth_beyond_inflation)

        self.update_leases()

        inc= self.calculate_monthly_income()
        exp= self.calculate_monthly_expenses()
        self.yearly_income+= inc
        self.yearly_expenses+= exp
        net= inc- exp
        self.cash+= net

        self.update_assets_and_debts()

        if self.home:
            home_pmt= self.home.make_payment(self.time)
            if self.cash>= home_pmt:
                self.cash-= home_pmt
            else:
                needed= home_pmt- self.cash
                self.cash=0
                if self.investment_balance>= needed:
                    self.liquidate_investments(needed)
                else:
                    self.investment_balance=0

        self.manage_cash()
        self.calculate_investment_return()

        self.net_worth= self.calculate_net_worth()

        self.record_monthly_data(inc, exp)

        if not self.is_retired:
            if self.check_retirement():
                self.retirement_age= self.age
                self.working= False

        if self.month%12==0:
            self.pay_annual_taxes()

        try:
            if self.func:
                exec(self.func)
        except Exception as e:
            st.warning(f"Error with AI defined functions. Continuing without utilizing the function.")

    def run_simulation(self):
        total_m = self.simulate_years*12
        for _ in range(total_m):
            self.step_month()


def run_monte_carlo_simulation(user_data):
    simulations = user_data.get('num_simulations', 100)
    simulate_years = user_data.get('simulate_years', 30)
    results = []
    retirement_ages = []

    for _ in range(simulations):
        user = User(user_data)
        user.run_simulation()
        results.append(user.time_series)
        if user.retirement_age:
            retirement_ages.append(user.retirement_age)

    average_retirement_age = np.mean(retirement_ages) if retirement_ages else None
    stdev_retirement_age = np.std(retirement_ages) if retirement_ages else None

    combined = pd.concat(results, ignore_index=True)
    numeric_cols = combined.select_dtypes(include=[np.number]).columns
    avg_ts = combined.groupby('month', as_index=False)[numeric_cols].mean()

    return avg_ts, average_retirement_age, stdev_retirement_age, results
