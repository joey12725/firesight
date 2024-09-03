import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import datetime
import json
from datetime import date
from st_repeating_field_group import generate_repeating_field_group
from datetime import date

with open('statetaxes.json', 'r') as file:
    state_taxes = json.load(file)['states']
global income_keys 
income_keys = {
    "income_type": {
        "type": "choice",
        "default": "salary/hourly",
        "choices": ["salary/hourly", "bonus", "stock_options", "commission", "gig_work", "rental", "startup", "government_assistance", "other"]
    },
    "name": {"type": str, "default": "Primary Income"},
    "amount": {
        "type": int,
        "default": 50000,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type not in ["startup", "gig_work", "rental", "commission"]
        }
    },
    "frequency": {
        "type": "choice",
        "default": "annual",
        "choices": ["hourly", "weekly", "biweekly", "monthly", "annual"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type not in ["bonus", "gig_work", "startup", "rental", "commission"]
        }
    },
    "overtime_eligible": {
        "type": "checkbox",
        "default": False,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "salary/hourly"
        }
    },
    "overtime_rate": {
        "type": float,
        "default": 1.5,
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "overtime_eligible": "overtime_eligible"},
            "func": lambda income_type, overtime_eligible: income_type == "salary/hourly" and overtime_eligible
        }
    },
    "bonus_frequency": {
        "type": "choice",
        "default": "annual",
        "choices": ["monthly", "quarterly", "biannual", "annual"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "bonus"
        }
    },
    "stock_options_type": {
        "type": "choice",
        "default": "pre_ipo",
        "choices": ["pre_ipo", "post_ipo"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "number_of_options": {
        "type": int,
        "default": 10000,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "strike_price": {
        "type": float,
        "default": 1.0,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "vesting_period": {
        "type": int,
        "default": 4,
        "label": "Vesting Period (years)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "vesting_cliff": {
        "type": int,
        "default": 1,
        "label": "Vesting Cliff (years)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "vesting_frequency": {
        "type": "choice",
        "default": "monthly",
        "choices": ["monthly", "quarterly", "annually"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "current_stock_price": {
        "type": float,
        "default": 10.0,
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "stock_options_type": "stock_options_type"},
            "func": lambda income_type, stock_options_type: income_type == "stock_options" and stock_options_type == "post_ipo"
        }
    },
    "estimated_ipo_price": {
        "type": float,
        "default": 20.0,
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "stock_options_type": "stock_options_type"},
            "func": lambda income_type, stock_options_type: income_type == "stock_options" and stock_options_type == "pre_ipo"
        }
    },
    "estimated_ipo_date": {
        "type": "date",
        "default": date.today().replace(year=date.today().year + 2),
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "stock_options_type": "stock_options_type"},
            "func": lambda income_type, stock_options_type: income_type == "stock_options" and stock_options_type == "pre_ipo"
        }
    },
    "average_time_at_job": {
        "type": float,
        "default": 3.5,
        "label": "Average Time at Job (years)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "time_at_job_std_dev": {
        "type": float,
        "default": 1.5,
        "label": "Standard Deviation of Time at Job (years)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "exercise_strategy": {
        "type": "choice",
        "default": "hold_until_exit",
        "choices": ["exercise_as_vested", "hold_until_exit", "custom"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "stock_options"
        }
    },
    "custom_exercise_percentage": {
        "type": float,
        "default": 50.0,
        "label": "Custom Exercise Percentage",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "exercise_strategy": "exercise_strategy"},
            "func": lambda income_type, exercise_strategy: income_type == "stock_options" and exercise_strategy == "custom"
        }
    },
    "startup_type": {
        "type": "choice",
        "default": "tech_startup",
        "choices": ["tech_startup", "retail", "service_based", "product", "franchise", "content_creation"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "startup"
        }
    },
    "startup_state_tax_state": {
        "type": "choice",
        "default": "California",
        "choices": [state["name"] for state in state_taxes],
        "label": "Startup State Tax State",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "startup"
        }
    },
    "startup_start_date": {
        "type": "date",
        "default": date.today(),
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "startup"
        }
    },
    "initial_investment": {
        "type": int,
        "default": 100000,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "startup"
        }
    },
    "first_year_failure_probability": {
        "type": float,
        "default": 0.9,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "startup"
        }
    },
    "failure_probability_decrease": {
        "type": float,
        "default": 0.1,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "startup"
        }
    },
    # Tech Startup Parameters
    "monthly_recurring_revenue_per_customer": {
        "type": int,
        "default": 100,
        "label": "Monthly Recurring Revenue (Per Customer)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "tech_startup"
        }
    },
    "customer_acquisition_cost_tech": {
        "type": int,
        "default": 100,
        "label": "Customer Acquisition Cost",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "tech_startup"
        }
    },
    "growth_rate_mom": {
        "type": float,
        "default": 10,
        "label": "Growth Rate (MoM)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "tech_startup"
        }
    },
    "churn_rate": {
        "type": float,
        "default": 5,
        "label": "Churn Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "tech_startup"
        }
    },
    "gross_margin_tech": {
        "type": float,
        "default": 80,
        "label": "Gross Margin",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "tech_startup"
        }
    },
    # Retail Parameters
    "average_revenue_per_sale": {
        "type": float,
        "default": 50,
        "label": "Average Revenue Per Sale",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "retail"
        }
    },
    "sales_volume": {
        "type": int,
        "default": 1000,
        "label": "Sales Volume",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "retail"
        }
    },
    "customer_acquisition_cost_retail": {
        "type": float,
        "default": 20,
        "label": "Customer Acquisition Cost",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "retail"
        }
    },
    "gross_margin_retail": {
        "type": float,
        "default": 50,
        "label": "Gross Margin",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "retail"
        }
    },
    "monthly_growth_rate_retail": {
        "type": float,
        "default": 5,
        "label": "Monthly Growth Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "retail"
        }
    },
    "return_rate": {
        "type": float,
        "default": 10,
        "label": "Return Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "retail"
        }
    },
    # Service-Based Business Parameters
    "hourly_rate": {
        "type": float,
        "default": 100,
        "label": "Hourly Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "service_based"
        }
    },
    "billable_hours_per_month": {
        "type": int,
        "default": 120,
        "label": "Billable Hours Per Month",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "service_based"
        }
    },
    "client_acquisition_cost": {
        "type": float,
        "default": 500,
        "label": "Client Acquisition Cost",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "service_based"
        }
    },
    "client_retention_rate": {
        "type": float,
        "default": 80,
        "label": "Client Retention Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "service_based"
        }
    },
    "gross_margin_service": {
        "type": float,
        "default": 70,
        "label": "Gross Margin",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "service_based"
        }
    },
    # Product Parameters
    "revenue_per_unit": {
        "type": float,
        "default": 100,
        "label": "Revenue Per Unit",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "product"
        }
    },
    "production_volume": {
        "type": int,
        "default": 1000,
        "label": "Production Volume",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "product"
        }
    },
    "cost_per_unit": {
        "type": int,
        "default": 50,
        "label": "Cost Per Unit",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "product"
        }
    },
    "monthly_growth_rate_product": {
        "type": float,
        "default": 5,
        "label": "Monthly Growth Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "product"
        }
    },
    "defect_rate": {
        "type": float,
        "default": 2,
        "label": "Defect Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "product"
        }
    },
    # Franchise Parameters
    "revenue_per_location": {
        "type": int,
        "default": 50000,
        "label": "Revenue Per Location",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "franchise"
        }
    },
    "royalty_fee_percentage": {
        "type": int,
        "default": 6,
        "label": "Royalty Fee Percentage",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "franchise"
        }
    },
    "operating_costs_per_location": {
        "type": int,
        "default": 30000,
        "label": "Operating Costs Per Location",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "franchise"
        }
    },
    "growth_rate_locations": {
        "type": float,
        "default": 20,
        "label": "Growth Rate (Locations)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "franchise"
        }
    },
    "location_success_rate": {
        "type": float,
        "default": 80,
        "label": "Location Success Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "franchise"
        }
    },
    # Content Creation Parameters
    "revenue_per_subscriber": {
        "type": float,
        "default": 2,
        "label": "Revenue Per Subscriber",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "content_creation"
        }
    },
    "subscriber_growth_rate": {
        "type": float,
        "default": 10,
        "label": "Subscriber Growth Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "content_creation"
        }
    },
    "conversion_rate": {
        "type": float,
        "default": 5,
        "label": "Conversion Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "content_creation"
        }
    },
    "revenue_per_paying_subscriber": {
        "type": float,
        "default": 10,
        "label": "Revenue Per Paying Subscriber",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "content_creation"
        }
    },
    "engagement_rate": {
        "type": float,
        "default": 15,
        "label": "Engagement Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "startup_type": "startup_type"},
            "func": lambda income_type, startup_type: income_type == "startup" and startup_type == "content_creation"
        }
    },
    # 401k Matching
    "401k_match_eligible": {
        "type": "checkbox",
        "default": False,
        "label": "Eligible for 401k Match",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type in ["salary/hourly", "bonus"]
        }
    },
    "401k_match_percentage": {
        "type": float,
        "default": 5.0,
        "label": "401k Match Percentage",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "match_eligible": "401k_match_eligible"},
            "func": lambda income_type, match_eligible: income_type in ["salary/hourly", "bonus"] and match_eligible
        }
    },
    "overtime_eligible" : {
        "type": "checkbox",
        "default": False,
        "label": "Eligible for Overtime",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "salary/hourly"
        },
    },
    "overtime_rate": {
        "type": float,
        "default": 1.5,
        "label": "Overtime Rate",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "overtime_eligible": "overtime_eligible"},
            "func": lambda income_type, overtime_eligible: income_type == "salary/hourly" and overtime_eligible
        }
    },
    "monthly_overtime_hours": {
        "type": int,
        "default": 12,
        "label": "Monthly Overtime Hours",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "overtime_eligible": "overtime_eligible"},
            "func": lambda income_type, overtime_eligible: income_type == "salary/hourly" and overtime_eligible
        }
    },
        "number_of_units": {
        "type": int,
        "default": 1,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },
    "rent_per_unit": {
        "type": float,
        "default": 1000,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },
    "rental_state": {
        "type": "choice",
        "default": "California",
        "choices": [state["name"] for state in state_taxes],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },
    "non_tax_costs_percentage": {
        "type": float,
        "default": 10,
        "label": "Non-Tax Costs (% of rent)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },
    "has_mortgage": {
        "type": "checkbox",
        "default": True,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },
    "mortgage_monthly_payment": {
        "type": float,
        "default": 1500,
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "has_mortgage": "has_mortgage"},
            "func": lambda income_type, has_mortgage: income_type == "rental" and has_mortgage
        }
    },
    "mortgage_interest_rate": {
        "type": float,
        "default": 3.5,
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "has_mortgage": "has_mortgage"},
            "func": lambda income_type, has_mortgage: income_type == "rental" and has_mortgage
        }
    },
    "mortgage_remaining_years": {
        "type": int,
        "default": 30,
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "has_mortgage": "has_mortgage"},
            "func": lambda income_type, has_mortgage: income_type == "rental" and has_mortgage
        }
    },
    "occupancy_rate": {
        "type": float,
        "default": 95,
        "label": "Occupancy Rate (%)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },

    "property_management_fee": {
        "type": float,
        "default": 8,
        "label": "Property Management Fee (% of rent)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "rental"
        }
    },
    
    # Gig work improvements
    "gigs_per_month": {
        "type": int,
        "default": 20,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "gig_work"
        }
    },
    "average_take_home_per_gig": {
        "type": float,
        "default": 100,
        "label": "Average Take-Home Pay Per Gig (before taxes)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "gig_work"
        }
    },
    "gig_expenses_percentage": {
        "type": float,
        "default": 20,
        "label": "Gig-Related Expenses (% of income)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "gig_work"
        }
    },
    "gig_work_hours_per_month": {
        "type": int,
        "default": 80,
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "gig_work"
        }
    },
    "has_growth": {
        "type": "checkbox",
        "default": False,
        "label": "Income Growth",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type not in ["startup"]
        }
    },
    "growth_type": {
        "type": "choice",
        "default": "percentage",
        "choices": ["percentage", "inflation"],
        "label": "Growth Type",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "has_growth": "has_growth"},
            "func": lambda income_type, has_growth: income_type not in ["startup"] and has_growth
        }
    },
    "growth_percentage": {
        "type": float,
        "default": 3.0,
        "label": "Annual Growth Percentage",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "has_growth": "has_growth", "growth_type": "growth_type"},
            "func": lambda income_type, has_growth, growth_type: income_type not in ["startup"] and has_growth and growth_type == "percentage"
        }
    },
    "commission_type": {
        "type": "choice",
        "default": "percentage",
        "choices": ["percentage", "fixed"],
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "commission"
        }
    },
    "commission_percentage": {
        "type": float,
        "default": 5.0,
        "label": "Commission Percentage",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "commission_type": "commission_type"},
            "func": lambda income_type, commission_type: income_type == "commission" and commission_type == "percentage"
        }
    },
    "commission_fixed_amount": {
        "type": float,
        "default": 1000,
        "label": "Fixed Commission Amount",
        "only_show_if": {
            "kwargs": {"income_type": "income_type", "commission_type": "commission_type"},
            "func": lambda income_type, commission_type: income_type == "commission" and commission_type == "fixed"
        }
    },
    "sales_target": {
        "type": int,
        "default": 100000,
        "label": "Sales Target",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "commission"
        }
    },
    "sales_standard_deviation": {
        "type": int,
        "default": 20000,
        "label": "Sales Standard Deviation",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "commission"
        }
    },
    "commission_cap": {
        "type": int,
        "default": 0,
        "label": "Commission Cap (0 for no cap)",
        "only_show_if": {
            "kwargs": {"income_type": "income_type"},
            "func": lambda income_type: income_type == "commission"
        }
    },
}
income_keys = {},

# DynamoDB configuration
try:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('firesight-users')
except:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    table = dynamodb.Table('firesight-users')

# Set page configuration
st.set_page_config(page_title="FIRESight - Edit Profile", page_icon="👨")

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

# Database functions
def fetch_user_profile(user_id):
    response = table.get_item(Key={'userid': user_id})
    return response.get('Item', {}).get('profile', None)

def update_user_profile(user_id, profile):
    table.update_item(
        Key={'userid': user_id},
        UpdateExpression='SET profile = :val1',
        ExpressionAttributeValues={':val1': profile}
    )

def load_user_profile(user_id):
    profile_json = fetch_user_profile(user_id)
    if profile_json:
        return json.loads(profile_json)
    return None

def save_user_profile(user_id, user_data):
    profile_json = json.dumps(user_data, indent=4)
    update_user_profile(user_id, profile_json)

# Main app
def main():
    st.title("Edit your FIRESight Profile")
    tooltip("FIRE (Financial Independence, Retire Early) is a financial movement that emphasizes achieving financial independence and retiring earlier than the traditional retirement age. This simulator helps you explore how attainable FIRE is for you.", type="markdown")

    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in")
        return

    user_data = load_user_profile(user_id)

    tabs = st.tabs([
        "Personal Info",
        "Income",
        "Budget",
        "Investments",
        "Major Expenses",
        "Home Purchase",
        "Location Change",
        "Retirement",
        "Simulation Settings"
    ])

    with tabs[0]:
        personal_info_page(user_data)

    with tabs[1]:
        income_page(user_data)

    with tabs[2]:
        budget_page(user_data)

    with tabs[3]:
        investments_page(user_data)

    with tabs[4]:
        major_expenses_page(user_data)

    with tabs[5]:
        home_purchase_page(user_data)

    with tabs[6]:
        location_change_page(user_data)

    with tabs[7]:
        retirement_page(user_data)

    with tabs[8]:
        simulation_settings_page(user_data)

    if st.button("Save Profile"):
        save_user_profile(user_id, user_data)
        st.success("Profile updated successfully")

def personal_info_page(user_data):
    st.header("Personal Information")
    
    user_data['age'] = st.number_input("Age", min_value=0, value=user_data.get('age', 22), step=1)
    
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Washington D.C.", "Puerto Rico", "None"]
    user_data['state'] = st.selectbox("State", options=states, index=states.index(user_data.get('state', "California")))
    
    user_data['married'] = st.checkbox("Are you married?", value=user_data.get('married', True))
    
    tooltip("Please note: If you have a partner, use either average or combined numbers as makes sense (combined income, average age).")

def income_page(user_data):
    st.header("Income Information")
    
    tooltip("This should be your gross annual income, combined if you are married, from all sources")
    
    # Assume we have access to income_keys
    income_sources = generate_repeating_field_group(income_keys, "income_source")

    
    user_data['income_growth'] = st.slider("Income Growth", min_value=0.0, max_value=0.2, value=user_data.get('income_growth', 0.03), step=0.01)
    tooltip("This is the percentage that you expect your income to increase each year.")
    
    user_data['other_tax_sheltered_income'] = st.number_input("Other Tax Sheltered Income", min_value=0.0, value=user_data.get('other_tax_sheltered_income', 0.0), step=1000.0)
    tooltip("This is a portion of your total income, not additional income (e.g., charitable contributions or health savings account contributions below the maximum).")

def budget_page(user_data):
    st.header("Budget")
    
    tooltip("This budget should represent your actual monthly expenses, including things like healthcare premiums that are deducted from your paycheck, but not things like 401k contributions. Do not include savings in this budget, this is only for your expenditures, all of you income not used in the budget will be invested in your investment portfolio.")
    tooltip(r"A typical FIRE strategy includes high savings rates, often between 50-70% of income allowing your nest egg to be built as quickly as possible.")
    tooltip("If rent is a budget category and you plan to purchase a home, it will automatically be removed at your planned home purchase date and replaced with a mortgage payment.")
    
    budget_item_keys = {
        "name": {"type": str, "default": ""},
        "value": {"type": int, "default": 2000},
        "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"]}
    }
    
    user_data['budget_items'] = generate_repeating_field_group(budget_item_keys, "budget", user_data.get('budget_items', []))
    
    user_data['expenditure_growth_beyond_inflation'] = st.slider("Expenditure Growth Beyond Inflation", min_value=0.0, max_value=0.1, value=user_data.get('expenditure_growth_beyond_inflation', 0.03), step=0.01)
    tooltip("This is your lifestyle creep percentage each year beyond inflation.")

def investments_page(user_data):
    st.header("Investments")
    
    user_data['current_savings'] = st.number_input("Current Savings", min_value=0.0, value=user_data.get('current_savings', 25000.0), step=1000.0)
    user_data['max_401k_contribution'] = st.checkbox("Max 401k Contribution", value=user_data.get('max_401k_contribution', True))
    user_data['max_ira_contribution'] = st.checkbox("Max IRA Contribution", value=user_data.get('max_ira_contribution', True))
    user_data['max_hsa_contribution'] = st.checkbox("Max HSA Contribution", value=user_data.get('max_hsa_contribution', False))
    
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
    """, type="markdown")
    
    investment_vehicle_keys = {
        "name": {"type": str, "default": "S&P 500"},
        "annual_returns": {"type": float, "default": 0.1026},
        "standard_deviation": {"type": float, "default": 0.1532},
        "ratio": {"type": float, "default": 1.0},
        "distribution_type": {"type": "choice", "default": "normal-monthly", "choices": ["normal-monthly", "normal-yearly-gradient", "historic-stocks", "historic-real-estate"]}
    }
    
    user_data['investment_vehicles'] = generate_repeating_field_group(investment_vehicle_keys, "investment", user_data.get('investment_vehicles', []))

def major_expenses_page(user_data):
    st.header("Major Expenses")
    
    tooltip("Major expenses are one-time or infrequent expenses that you anticipate in the future. These could include things like a wedding, a new car, or a vacation. These expenses will be deducted from your savings when they occur.")
    tooltip("Financing only uses the down payment and cost fields. The monthly payment is calculated for you. The lease option only uses down payment and monthly payment fields. Cash purchases only use the cost field.")
    
    major_purchase_keys = {
        "item_name": {"type": str, "default": ""},
        "purchase_date": {"type": "date", "default": date.today()},
        "total_cost": {"type": float, "default": 0.0},
        "purchase_type": {"type": "choice", "choices": ["cash", "finance", "lease"], "default": "cash"},
        "down_payment": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type in ["finance", "lease"]
            }
        },
        "loan_amount": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "finance"
            }
        },
        "interest_rate": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "finance"
            }
        },
        "loan_term_months": {
            "type": int,
            "default": 36,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "finance"
            }
        },
        "lease_term_months": {
            "type": int,
            "default": 36,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "lease"
            }
        },
        "monthly_lease_payment": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "lease"
            }
        },
        "buy_residual": {
            "type": "checkbox",
            "default": False,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type"},
                "func": lambda purchase_type: purchase_type == "lease"
            }
        },
        "residual_value": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type", "buy_residual": "buy_residual"},
                "func": lambda purchase_type, buy_residual: purchase_type == "lease" and buy_residual
            }
        },
        "consider_in_net_worth": {
            "type": "checkbox",
            "default": False,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type", "buy_residual": "buy_residual"},
                "func": lambda purchase_type, buy_residual: purchase_type in ["cash", "finance"] or (purchase_type == "lease" and buy_residual)
            }
        },
        "asset_value_change": {
            "type": "slider",
            "default": 0,
            "min": -20,
            "max": 20,
            "step": 0.5,
            "only_show_if": {
                "kwargs": {"purchase_type": "purchase_type", "buy_residual": "buy_residual", "consider_in_net_worth": "consider_in_net_worth"},
                "func": lambda purchase_type, buy_residual, consider_in_net_worth: 
                    (purchase_type in ["cash", "finance"] and consider_in_net_worth) or 
                    (purchase_type == "lease" and buy_residual and consider_in_net_worth)
            }
        }
    }
    
    user_data['major_purchases'] = generate_repeating_field_group(major_purchase_keys, "major_purchase", user_data.get('major_purchases', []))

    user_data['emergency_fund_target'] = st.number_input("Emergency Fund Target", min_value=0.0, value=user_data.get('emergency_fund_target', 10000.0), step=1000.0)
    tooltip("This should represent at least 3-6 months of expenses.")

    user_data['average_life_event_cost'] = st.number_input("Average Life Event Cost", min_value=0.0, value=user_data.get('average_life_event_cost', 1000.0), step=1000.0)
    tooltip("It is important to model the unexpected for life events that you can't budget for. These events will come out of your emergency fund.")
    user_data['average_life_event_stdev'] = st.number_input("Life Event Standard Deviation", min_value=0.0, value=user_data.get('average_life_event_stdev', 500.0), step=1000.0)
    user_data['average_life_event_frequency'] = st.slider("Average Life Events per year", min_value=0, max_value=10, value=user_data.get('average_life_event_frequency', 1), step=1)

def home_purchase_page(user_data):
    st.header("Home Purchase")
    
    # Safely get home_purchase data, defaulting to an empty dict if not present
    home_purchase = user_data.get('home_purchase') or {}
    
    # Determine the initial status based on existing data
    if not home_purchase:
        initial_status = "No"
    elif (home_purchase.get('mortgage_balance') or 0) > 0:
        initial_status = "Currently paying it off"
    elif (home_purchase.get('price') or 0) > 0:
        initial_status = "Paid off"
    elif home_purchase.get('date'):
        initial_status = "Plan to in the future"
    else:
        initial_status = "No"

    home_status = st.selectbox(
        "Do you currently own a home or plan to in the future?", 
        options=["No", "Currently paying it off", "Paid off", "Plan to in the future"],
        index=["No", "Currently paying it off", "Paid off", "Plan to in the future"].index(initial_status)
    )

    if home_status != "No":
        st.subheader("Home Details")
        
        if home_status in ["Currently paying it off", "Paid off"]:
            home_purchase['price'] = st.number_input("Home Value", min_value=0.0, value=float(home_purchase.get("price") or 300000.0), step=10000.0)
            
            if home_status == "Currently paying it off":
                home_purchase['mortgage_balance'] = st.number_input("Current Mortgage Balance", min_value=0.0, value=float(home_purchase.get("mortgage_balance") or 200000.0), step=10000.0)
                home_purchase['mortgage_rate'] = st.slider("Mortgage Rate", min_value=0.0, max_value=0.1, value=float(home_purchase.get("mortgage_rate") or 0.04), step=0.001)
                home_purchase['mortgage_term_years'] = st.slider("Remaining Mortgage Term (Years)", min_value=1, max_value=30, value=int(home_purchase.get("mortgage_term_years") or 20), step=1)
            else:
                home_purchase['mortgage_balance'] = 0
                home_purchase['mortgage_rate'] = 0
                home_purchase['mortgage_term_years'] = 0

        elif home_status == "Plan to in the future":
            home_purchase['date'] = str(st.date_input("Planned Purchase Date", value=datetime.date.fromisoformat(home_purchase.get("date") or "2025-01-01"), min_value=datetime.date.today()))
            home_purchase['price'] = st.number_input("Estimated Purchase Price", min_value=0.0, value=float(home_purchase.get("price") or 300000.0), step=10000.0)
            home_purchase['down_payment'] = st.number_input("Planned Down Payment", min_value=0.0, value=float(home_purchase.get("down_payment") or 60000.0), step=1000.0)
            home_purchase['mortgage_rate'] = st.slider("Expected Mortgage Rate", min_value=0.0, max_value=0.1, value=float(home_purchase.get("mortgage_rate") or 0.04), step=0.001)
            home_purchase['mortgage_term_years'] = st.slider("Planned Mortgage Term (Years)", min_value=10, max_value=30, value=int(home_purchase.get("mortgage_term_years") or 30), step=1)

        home_purchase['property_tax'] = st.number_input("Annual Property Tax Rate", min_value=0.0, max_value=0.05, value=float(home_purchase.get("property_tax") or 0.02), step=0.001, format="%.3f")
        st.caption("This is the annual property tax rate for your area. It does not include your state's property tax.")
        
        default_maintenance = float(home_purchase.get("price") or 300000.0) * 0.01
        home_purchase['maintenance_cost'] = st.number_input("Annual Maintenance Cost", min_value=0.0, value=float(home_purchase.get("maintenance_cost") or default_maintenance), step=500.0)
        st.caption("This is the estimated annual cost for home maintenance and repairs. A common rule of thumb is 1% of the home's value.")
        
        home_purchase['pay_off_before_retirement'] = st.checkbox("Pay Off Mortgage Before Retirement", value=bool(home_purchase.get("pay_off_before_retirement")))

        user_data['home_purchase'] = home_purchase
    else:
        user_data['home_purchase'] = None

    return user_data

def location_change_page(user_data):
    st.header("Location Change")
    
    location_change = user_data.get('location_change') or {}
    
    plan_to_change = st.checkbox("Plan to Change Location (domestic only)", value=bool(location_change))
    
    if plan_to_change:
        st.subheader("Location Change Details")
        location_change_date_default = "2025-01-01"
        location_change_date_str = str(location_change.get("date") or location_change_date_default)
        
        try:
            location_change_date_value = datetime.date.fromisoformat(location_change_date_str)
        except ValueError:
            location_change_date_value = datetime.date.fromisoformat(location_change_date_default)

        location_change['date'] = str(st.date_input("Location Change Date", value=location_change_date_value, min_value=datetime.date.today()))
        location_change['moving_cost'] = st.number_input("Moving Cost", min_value=0.0, value=float(location_change.get("moving_cost") or 5000.0), step=1000.0)
        tooltip("This is the cost of moving to a new location. It is a one-time expense.")
        location_change['col_adjustment'] = st.slider("Cost of Living Adjustment", min_value=0.0, max_value=2.0, value=float(location_change.get("col_adjustment") or 1.0), step=0.01)
        tooltip("The ratio between your costs where you are and where you want to move. [Learn more](https://www.nerdwallet.com/cost-of-living-calculator).", type="markdown")
        
        states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Washington D.C.", "Puerto Rico", "None"]
        current_state = location_change.get("state") or "None"
        state_index = states.index(current_state) if current_state in states else states.index("None")
        location_change['state'] = st.selectbox("State", options=states, index=state_index)

        user_data['location_change'] = location_change
    else:
        user_data['location_change'] = None

    return user_data

def retirement_page(user_data):
    st.header("Retirement Planning")
    
    user_data['post_retirement_expenses'] = st.number_input("Post Retirement Expenses", min_value=0.0, value=user_data.get('post_retirement_expenses', 0.0), step=1000.0, help="What you want to live off of in your early retirement. It will grow with inflation.")
    tooltip("This is the amount you expect to spend each year in retirement. It should be adjusted for inflation.")
    
    user_data['average_post_retirement_income'] = st.number_input("Average Post Retirement Income (not including investments)", min_value=0.0, value=user_data.get('average_post_retirement_income', 0.0), step=1000.0)
    tooltip("This is the amount you expect to earn each year in retirement outside of your investment. It should be adjusted for inflation.")
    
    user_data['risk_tolerance'] = st.slider("Risk Tolerance", min_value=0.0, max_value=1.0, value=user_data.get('risk_tolerance', 0.5), step=0.01)
    tooltip(r"A risk tolerance of 0.5 adheres to the 4% rule, which is a theory stating that you can safely withdraw 4% of your retirement portfolio each year without running out. Lower values are more conservative, higher values more aggressive.")

def simulation_settings_page(user_data):
    st.header("Simulation Settings")
    
    user_data['simulate_years'] = st.slider("Simulation Years", min_value=1, max_value=50, value=user_data.get('simulate_years', 10), step=1, key="simulate_years_slider")
    tooltip("This is the number of years you want to simulate to see if you can retire early. It should be a few years longer than your expected retirement age. More years takes more time but reduces the chances of the simulation not reaching your retirement age.")
    
    user_data['num_simulations'] = st.slider("Number of Simulations", min_value=1, max_value=100, value=user_data.get('num_simulations', 10), step=1, format="Count: %d", key="num_simulations_slider")
    tooltip("This is the number of simulations you want to run to see if you can retire early. More simulations will give you a more accurate result, but a longer time to compute.")
    
    user_data['inflation'] = st.slider("Inflation", min_value=0.0, max_value=0.1, value=user_data.get('inflation', 0.03), step=0.01)

    if user_data['simulate_years'] < 12:
        st.warning(f"Unless you are confident you are less than {user_data['simulate_years']} years from your FIRE number, it is recommended to simulate a larger number of years to ensure you have a good buffer.")
    if user_data['num_simulations'] < 10:
        st.warning(f"The more simulations you run, the more accurate your results will be. It is recommended to run at least 10 simulations.")

if __name__ == "__main__":
    main()

