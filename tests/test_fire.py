import sys
import os
from types import SimpleNamespace
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import datetime
import numpy as np
import unittest

# Provide a minimal stub for streamlit so FIRE.py can be imported
sys.modules['streamlit'] = SimpleNamespace(warning=lambda *args, **kwargs: None)

import FIRE


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

    def test_return_generator_lengths_for_various_assets(self):
        assets = ["Index Funds", "Bonds", "High Yield Savings", "Cryptocurrency", "Other"]
        for asset in assets:
            rg = FIRE.ReturnGenerator(asset, 10)
            self.assertEqual(len(rg.returns), 10)
            self.assertIsInstance(rg.get_return_for_month(0), float)

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

    def test_budget_item_update_and_monthly_expense(self):
        item = FIRE.BudgetItem({"value": 1000, "frequency": "monthly"})
        self.assertTrue(item.get_monthly_expense())
        item.update(0.12)
        self.assertGreater(item.value, 1000)

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

    def test_custom_code_executes_each_step(self):
        user_data = {
            "age": 30,
            "state": "Alaska",
            "married": False,
            "income": [],
            "budget_items": [],
            "assets_and_debts": [],
            "investment_index_funds": 100,
            "simulate_years": 1,
            "num_simulations": 1
        }
        user = FIRE.User(user_data)
        user.func = "self.custom_flag = True"
        user.step_month()
        self.assertTrue(getattr(user, "custom_flag", False))


if __name__ == "__main__":
    unittest.main()
