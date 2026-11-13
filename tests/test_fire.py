import datetime
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import FIRE  # noqa: E402


def minimal_profile(**overrides):
    profile = {
        "age": 30,
        "state": "Texas",
        "married": False,
        "income": [{"income_type": "salary/hourly", "name": "Salary", "amount": 100000, "frequency": "annual"}],
        "budget_items": [{"type": "rent", "name": "rent", "value": 2000, "frequency": "monthly"}],
        "assets_and_debts": [],
        "investment_index_funds": 100,
        "simulate_years": 2,
        "num_simulations": 3,
        "post_retirement_expenses": 40000,
    }
    profile.update(overrides)
    return profile


class TestFire(unittest.TestCase):
    def test_ensure_date_parses_and_handles_inputs(self):
        d = FIRE.ensure_date("2021-01-02")
        self.assertEqual(d, datetime.date(2021, 1, 2))
        dt = datetime.datetime(2020, 5, 1)
        self.assertEqual(FIRE.ensure_date(dt), datetime.date(2020, 5, 1))
        d2 = datetime.date(2019, 12, 31)
        self.assertEqual(FIRE.ensure_date(d2), d2)
        self.assertIsInstance(FIRE.ensure_date(None), datetime.date)
        with self.assertRaises(ValueError):
            FIRE.ensure_date(123)

    def test_get_state_tax_data_lookup(self):
        data = FIRE.get_state_tax_data("Alabama")
        self.assertIsInstance(data, dict)
        self.assertEqual(data["name"], "Alabama")
        self.assertIsNone(FIRE.get_state_tax_data("NotAState"))

    def test_block_bootstrap_respects_length_and_source(self):
        rg = FIRE.ReturnGenerator("Index Funds", 1)
        data = np.array([0.01, 0.02, 0.03])
        seq = rg.block_bootstrap(data, 5)
        self.assertEqual(len(seq), 5)
        self.assertTrue(set(seq).issubset(set(data)))

    def test_block_bootstrap_keeps_historical_blocks_contiguous(self):
        rg = FIRE.ReturnGenerator("Index Funds", 1, block_size=4)
        data = np.arange(100, dtype=float)
        seq = rg.block_bootstrap(data, 12)
        for start in range(0, 12, 4):
            block = seq[start:start + 4]
            self.assertTrue(all(b - a == 1 for a, b in zip(block, block[1:])))

    def test_return_generator_lengths_for_various_assets(self):
        assets = ["Index Funds", "Bonds", "High Yield Savings", "Cryptocurrency", "Other",
                  "Retirement Accounts", "Peer-to-Peer Lending", "Individual Stocks", "Rental Real Estate"]
        for asset in assets:
            rg = FIRE.ReturnGenerator(asset, 10)
            self.assertEqual(len(rg.returns), 10)
            self.assertIsInstance(float(rg.get_return_for_month(0)), float)

    def test_retirement_accounts_earn_market_returns(self):
        rg = FIRE.ReturnGenerator("Retirement Accounts", 120)
        self.assertTrue(any(r != 0 for r in rg.returns))

    def test_investment_vehicle_provides_sequence_then_zero(self):
        iv = FIRE.InvestmentVehicle("Index Funds", 100, total_months=3)
        vals = [iv.get_monthly_return() for _ in range(3)]
        self.assertEqual(len(vals), 3)
        self.assertTrue(any(v != 0 for v in vals))
        self.assertEqual(iv.get_monthly_return(), 0.0)

    def test_lease_payments_and_value_updates(self):
        lease = FIRE.Lease({"monthly_payment": 100, "lease_term_months": 2, "asset_value": 1000, "asset_value_change": 12, "consider_in_net_worth": True})
        p1 = lease.make_payment()
        lease.update_value()
        self.assertEqual(p1, 100)
        self.assertGreater(lease.asset_value, 1000)
        lease.make_payment()
        lease.make_payment()
        self.assertFalse(lease.is_active)
        self.assertEqual(lease.make_payment(), 0)
        self.assertGreater(lease.get_net_worth_impact(), 0)

    def test_home_zero_interest_pays_off_after_term(self):
        home = FIRE.Home(purchase_date=datetime.date.today(), purchase_price=120000, down_payment=20000, mortgage_rate=0.0, mortgage_term_years=1)
        home.re_generator.get_return_for_month = lambda idx: 0
        for _ in range(13):
            home.make_payment(datetime.date.today())
        self.assertAlmostEqual(home.loan_balance, 0, delta=1e-6)
        self.assertTrue(home.paid_off)
        self.assertEqual(home.make_payment(datetime.date.today()), 0)

    def test_mortgage_payment_matches_amortization_formula(self):
        home = FIRE.Home(datetime.date.today(), 300000, 60000, 0.06, 30)
        # $240k at 6% over 30 years is a well-known $1,438.92/month
        self.assertAlmostEqual(home.monthly_PI_payment, 1438.92, places=2)

    def test_budget_item_update_and_monthly_expense(self):
        item = FIRE.BudgetItem({"value": 1000, "frequency": "monthly"})
        self.assertTrue(item.get_monthly_expense())
        item.update(0.12)
        self.assertGreater(item.value, 1000)
        self.assertAlmostEqual(FIRE.BudgetItem({"value": 1200, "frequency": "annual"}).get_monthly_expense(), 100)

    def test_asset_or_debt_update_behaviour(self):
        asset = FIRE.AssetOrDebt({"type": "Checking Account", "value": 1000})
        before = asset.value
        asset.update()
        self.assertGreater(asset.value, before)
        debt = FIRE.AssetOrDebt({"type": "Auto Loan", "value": 12000, "remaining_term": 1})
        for _ in range(12):
            debt.update()
        self.assertLessEqual(debt.value, 0)

    def test_income_source_salary_and_rental(self):
        sal = FIRE.IncomeSource({"income_type": "salary/hourly", "amount": 120000, "frequency": "annual"})
        income = sal.get_monthly_income(datetime.date.today(), 30)
        self.assertTrue(9000 < income < 11000)
        rent_src = FIRE.IncomeSource({"income_type": "rental", "number_of_units": 1, "rent_per_unit": 1000, "occupancy_rate": 100, "non_tax_costs_percentage": 0, "property_management_fee": 0})
        rent_src.has_mortgage = False
        self.assertEqual(rent_src.get_monthly_income(datetime.date.today(), 30), 1000)

    def test_federal_tax_brackets_single_and_married(self):
        single = FIRE.User(minimal_profile(married=False))
        married = FIRE.User(minimal_profile(married=True))
        self.assertEqual(single.calculate_federal_tax(12400), 0)
        # 10% of the first 9,875 of taxable income
        self.assertAlmostEqual(single.calculate_federal_tax(12400 + 9875), 987.5)
        self.assertLess(married.calculate_federal_tax(100000), single.calculate_federal_tax(100000))

    def test_state_tax_is_zero_in_texas_and_positive_in_california(self):
        tx = FIRE.User(minimal_profile(state="Texas"))
        ca = FIRE.User(minimal_profile(state="California"))
        self.assertEqual(tx.calculate_state_tax(100000), 0)
        self.assertGreater(ca.calculate_state_tax(100000), 0)

    def test_state_brackets_are_lower_thresholds(self):
        al = FIRE.User(minimal_profile(state="Alabama"))
        # 2% on the first $500, 4% up to $3,000, 5% above
        self.assertAlmostEqual(al.calculate_state_tax(10000), 10 + 100 + 350)
        self.assertEqual(al.calculate_state_tax(0), 0)

    def test_starting_balances_are_counted_once(self):
        profile = minimal_profile(assets_and_debts=[
            {"type": "Checking Account", "value": 10000},
            {"type": "Retirement Accounts", "value": 50000},
            {"type": "Student Loan", "value": 20000, "interest_rate": 5.0, "remaining_term": 10},
        ])
        user = FIRE.User(profile)
        self.assertEqual(user.cash, 10000)
        self.assertEqual(user.investment_balance, 50000)
        self.assertAlmostEqual(user.calculate_net_worth(), 40000)

    def test_allocations_must_sum_to_100(self):
        with self.assertRaises(ValueError):
            FIRE.User(minimal_profile(investment_index_funds=60))
        # slider rounding noise is tolerated, and the hyphenated P2P key maps correctly
        FIRE.User(minimal_profile(investment_index_funds=66.6667, investment_peer_to_peer_lending=33.3333))

    def test_monthly_hook_runs_each_step(self):
        user = FIRE.User(minimal_profile())
        calls = []
        user.monthly_hook = lambda u: calls.append(u.month)
        user.step_month()
        user.step_month()
        self.assertEqual(calls, [1, 2])

    def test_fixed_value_goal_retires_when_net_worth_crosses_it(self):
        profile = minimal_profile(retirement_goal_method="Fixed Value", fixed_retirement_goal=1,
                                  assets_and_debts=[{"type": "Checking Account", "value": 5000}])
        user = FIRE.User(profile)
        user.step_month()
        self.assertTrue(user.is_retired)
        self.assertFalse(user.working)
        self.assertAlmostEqual(user.retirement_age, 30 + 1 / 12)

    def test_reduced_income_goal_runs(self):
        profile = minimal_profile(retirement_goal_method="Simulate Additional Years with Reduced Income",
                                  remove_income_sources={"Salary": True}, simulate_years=1,
                                  assets_and_debts=[{"type": "Retirement Accounts", "value": 5_000_000}])
        user = FIRE.User(profile)
        user.run_simulation()
        self.assertTrue(user.is_retired)

    def test_monte_carlo_is_reproducible_with_seed(self):
        profile = minimal_profile(investment_index_funds=50, investment_cryptocurrency=50)
        a = FIRE.run_monte_carlo_simulation(profile, seed=42)
        b = FIRE.run_monte_carlo_simulation(profile, seed=42)
        self.assertEqual(len(a[3]), 3)
        self.assertEqual(len(a[0]), 24)
        np.testing.assert_allclose(a[0]["net_worth"], b[0]["net_worth"])


if __name__ == "__main__":
    unittest.main()
