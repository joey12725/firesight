import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import datetime
import json
from datetime import date
from st_repeating_field_group import generate_repeating_field_group
from datetime import date
from importlib.metadata import version
import pandas as pd


with open('statetaxes.json', 'r') as file:
    state_taxes = json.load(file)['states']

global income_keys 
income_keys = {
    "income_type": {
        "type": "choice",
        "default": "salary/hourly",
        "choices": ["salary/hourly", "bonus", "stock_options", "commission", "gig_work", "rental", "government_assistance", "other"]
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

#cities is the first column of cost-of-living.csv file
#countries is the second column of cost-of-living.csv

# Load cost-of-living data

cost_of_living_data = pd.read_csv("cost-of-living.csv")
def deduplicate(ls):
    return list(dict.fromkeys(ls))

cities = deduplicate(list(cost_of_living_data["city"]))
countries = deduplicate(list(cost_of_living_data["country"]))

global milestone_keys
milestone_keys = {
    # Individual checkboxes for each milestone type
    "buy_a_house": {
        "type": "checkbox",
        "default": False
    },
    "change_location": {
        "type": "checkbox",
        "default": False
    },
    "major_expense": {
        "type": "checkbox",
        "default": False
    },
    "change_income": {
        "type": "checkbox",
        "default": False
    },
    "change_budget": {
        "type": "checkbox",
        "default": False
    },
    "major_windfall": {
        "type": "checkbox",
        "default": False
    },
        "family_change": {
            "type": "checkbox",
        "default": False
    },
    # Date for milestone
    "date": {"type": "date", "default": datetime.date.today()},
    "family_change_type": {
        "type": "choice",
        "default": "marriage",
        "choices": ["marriage", "divorce", "birth", "death", "dependant_adult"],
        "only_show_if": {
            "kwargs": {"family_change": "family_change"},
            "func": lambda family_change: family_change 
    },
    },
    "twins": {
        "type": "checkbox",
        "default": False,
        "only_show_if": {
            "kwargs": {"family_change": "family_change_type"},
            "func": lambda family_change: family_change == "birth"
        }
    },
    "number_of_dependant_adults": {
        "type": int,
        "default": 0,
        "only_show_if": {
            "kwargs": {"family_change": "family_change_type"},
            "func": lambda family_change: family_change == "dependant_adult"
        },
    },

    # House purchase fields, conditionally shown if "buy_a_house" is checked
    "house_price": {
        "type": float,
        "default": 300000.0,
        "only_show_if": {
            "kwargs": {"buy_a_house": "buy_a_house"},
            "func": lambda buy_a_house: buy_a_house
        }
    },
    "down_payment": {
        "type": float,
        "default": 60000.0,
        "only_show_if": {
            "kwargs": {"buy_a_house": "buy_a_house"},
            "func": lambda buy_a_house: buy_a_house
        }
    },
    "mortgage_rate": {
        "type": float,
        "default": 0.04,
        "only_show_if": {
            "kwargs": {"buy_a_house": "buy_a_house"},
            "func": lambda buy_a_house: buy_a_house
        }
    },
    "mortgage_term_years": {
        "type": int,
        "default": 30,
        "only_show_if": {
            "kwargs": {"buy_a_house": "buy_a_house"},
            "func": lambda buy_a_house: buy_a_house
        }
    },
    "property_tax_rate": {
        "type": float,
        "default": 0.02,
        "only_show_if": {
            "kwargs": {"buy_a_house": "buy_a_house"},
            "func": lambda buy_a_house: buy_a_house
        }
    },
    "annual_maintenance_cost": {
        "type": float,
        "default": 3000.0,
        "only_show_if": {
            "kwargs": {"buy_a_house": "buy_a_house"},
            "func": lambda buy_a_house: buy_a_house
        }
    },

    # Location change fields, conditionally shown if "change_location" is checked
    "country": {
        "type": "choice",
        "choices": countries,  # Placeholder, replace with actual logic for country list
        "default": "United States",
        "only_show_if": {
            "kwargs": {"change_location": "change_location"},
            "func": lambda change_location: change_location
        }
    },
    "city": {
        "type": "choice",
        "choices": cities,  # Placeholder, replace with actual city logic
        "default": "New York",
        "only_show_if": {
            "kwargs": {"change_location": "change_location"},
            "func": lambda change_location: change_location
        }
    },
    "moving_cost": {
        "type": float,
        "default": 5000.0,
        "only_show_if": {
            "kwargs": {"change_location": "change_location"},
            "func": lambda change_location: change_location
        }
    },
    "expense_adjustment": {
        "type": "choice",
        "choices": ["Leave expenses the same", "Adjust for similar quality of life", "Manual adjustment"],
        "default": "Leave expenses the same",
        "only_show_if": {
            "kwargs": {"change_location": "change_location"},
            "func": lambda change_location: change_location
        }
    },
    "manual_expense_adjustment": {
        "type": float,
        "default": 1.0,
        "only_show_if": {
            "kwargs": {"change_location": "change_location", "expense_adjustment": "expense_adjustment"},
            "func": lambda change_location, expense_adjustment: change_location and expense_adjustment == "Manual adjustment"
        }
    },

    # Major Expense / Major Purchase fields, shown if "major_expense" is checked
    "item_name": {
        "type": str,
        "default": "",
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense"},
            "func": lambda major_expense: major_expense
        }
    },
    "total_cost": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense"},
            "func": lambda major_expense: major_expense
        }
    },
    "purchase_type": {
        "type": "choice",
        "choices": ["cash", "finance", "lease"],
        "default": "cash",
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense"},
            "func": lambda major_expense: major_expense
        }
    },
    "down_payment": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type", "buy_a_house": "buy_a_house"},
            "func": lambda major_expense, purchase_type, buy_a_house: (major_expense and purchase_type in ["finance", "lease"]) or buy_a_house
        }
    },
    "loan_amount": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type"},
            "func": lambda major_expense, purchase_type: major_expense and purchase_type == "finance"
        }
    },
    "interest_rate": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type"},
            "func": lambda major_expense, purchase_type: major_expense and purchase_type == "finance"
        }
    },
    "loan_term_months": {
        "type": int,
        "default": 36,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type"},
            "func": lambda major_expense, purchase_type: major_expense and purchase_type == "finance"
        }
    },
    "lease_term_months": {
        "type": int,
        "default": 36,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type"},
            "func": lambda major_expense, purchase_type: major_expense and purchase_type == "lease"
        }
    },
    "monthly_lease_payment": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type"},
            "func": lambda major_expense, purchase_type: major_expense and purchase_type == "lease"
        }
    },
    "buy_residual": {
        "type": "checkbox",
        "default": False,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type"},
            "func": lambda major_expense, purchase_type: major_expense and purchase_type == "lease"
        }
    },
    "residual_value": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_expense": "major_expense", "purchase_type": "purchase_type", "buy_residual": "buy_residual"},
            "func": lambda major_expense, purchase_type, buy_residual: major_expense and purchase_type == "lease" and buy_residual
        }
    },

    # Major Windfall fields
    "windfall_amount": {
        "type": float,
        "default": 0.0,
        "only_show_if": {
            "kwargs": {"major_windfall": "major_windfall"},
            "func": lambda major_windfall: major_windfall 
        }
    }
}

global states 
states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Washington D.C.", "Puerto Rico", "None"]

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

# Load cost of living data
cost_of_living = pd.read_csv('cost-of-living.csv')


def personal_info_and_simulation_settings_page(user_data):
    st.header("Personal Information and Simulation Settings")
    
    user_data['age'] = st.number_input("Age", min_value=0, value=user_data.get('age', 22), step=1)
    
    user_data['state'] = st.selectbox("State", options=states, index=states.index(user_data.get('state', "California")))
    
    user_data['married'] = st.checkbox("Are you married?", value=user_data.get('married', True))
    
    if user_data['married']:
        user_data['spouse_age'] = st.number_input("Spouse Age", min_value=0, value=user_data.get('spouse_age', 22), step=1)

    tooltip("Please note: If you have a partner, use either average or combined numbers as makes sense (combined income, average age).")

    dependents = st.number_input("How many kids or adult dependent do you have?", min_value=0)
    user_data['dependents'] = dependents

    user_data["city"] = st.selectbox("City", options=cities, index=cities.index(user_data.get('city', "Austin")))
    user_data["country"] = st.selectbox("Country", options=countries, index=countries.index(user_data.get('country', "United States")))
    st.subheader("Simulation Settings")
    user_data['simulate_years'] = st.slider("Simulation Years", min_value=1, max_value=50, value=user_data.get('simulate_years', 10), step=1)
    tooltip("This is the number of years you want to simulate to see if you can retire early. It should be a few years longer than your expected retirement age. More years takes more time but reduces the chances of the simulation not reaching your retirement age.")
    
    user_data['num_simulations'] = st.slider("Number of Simulations", min_value=1, max_value=100, value=user_data.get('num_simulations', 10), step=1, format="Count: %d")
    tooltip("This is the number of simulations you want to run to see if you can retire early. More simulations will give you a more accurate result, but a longer time to compute.")
    
    user_data['inflation'] = st.slider("Inflation", min_value=0.0, max_value=0.1, value=user_data.get('inflation', 0.03), step=0.01)

    if user_data['simulate_years'] < 12:
        st.warning(f"Unless you are confident you are less than {user_data['simulate_years']} years from your FIRE number, it is recommended to simulate a larger number of years to ensure you have a good buffer.")
    if user_data['num_simulations'] < 10:
        st.warning(f"The more simulations you run, the more accurate your results will be. It is recommended to run at least 10 simulations.")

def income_page(user_data):
    st.header("Income Information")
    
    tooltip("This should be your gross annual income, combined if you are married, from all sources")
    
    # Assume we have access to income_keys
    user_data['income'] = generate_repeating_field_group(income_keys, "income_source")

def budget_page(user_data):
    st.header("Budget")
    
    tooltip("This budget should represent your actual monthly expenses, including things like healthcare premiums that are deducted from your paycheck, but not things like 401k contributions. Do not include savings in this budget, this is only for your expenditures, all of you income not used in the budget will be invested in your investment portfolio.")
    tooltip(r"A typical FIRE strategy includes high savings rates, often between 50-70% of income allowing your nest egg to be built as quickly as possible.")
    tooltip("If rent is a budget category and you plan to purchase a home, it will automatically be removed at your planned home purchase date and replaced with a mortgage payment.")
    
    budget_item_keys = {
        "type": {"type": "choice", "default": "rent", "choices": ["rent", "mortgage", "utilities", "groceries", "dining_out", "gas", "healthcare", "clothing", "public_transport", "entertainment", "gym", "other"]},
        "name": {"type": str, "default": "", "only_show_if": {"kwargs": {"type": "type"}, "func": lambda type: type == "other"}},
        "value": {"type": int, "default": 2000, "only_show_if": {"kwargs": {"type": "type"}, "func": lambda type: type != "mortgage"}},
        "frequency": {"type": "choice", "default": "monthly", "choices": ["weekly", "monthly", "annual"], "only_show_if": {"kwargs": {"type": "type"}, "func": lambda type: type != "mortgage"}},
        "changes_if_not_working": {"type": "checkbox", "default": False},
        #if would_be_different_if_not_working is true, then ask for what it would be different if not working
        "value_if_not_working": {
            "type": int, 
            "default": 0,         
            "only_show_if": {
                "kwargs": {"changes_if_not_working": "changes_if_not_working"},
                "func": lambda changes_if_not_working: changes_if_not_working
            }
        }
    }
    
    user_data['budget_items'] = generate_repeating_field_group(budget_item_keys, "budget", user_data.get('budget_items', []))
    
    user_data['expenditure_growth_beyond_inflation'] = st.slider("Expenditure Growth Beyond Inflation", min_value=0.0, max_value=0.1, value=user_data.get('expenditure_growth_beyond_inflation', 0.03), step=0.01)
    tooltip("This is your lifestyle creep percentage each year beyond inflation.")


def investments_page(user_data):
    st.header("Investments")
    
    # Updated Assets and Debts section
    st.subheader("Assets and Debts")
    
    asset_debt_keys = {
        "type": {
            "type": "choice",
            "choices": [
                "Home (Being Paid Off)", "Home (Paid Off)", "Checking Account", "Savings Account",
                "Index Funds", "Bonds", "Rental Real Estate", "Retirement Accounts",
                "High Yield Savings", "Peer-to-Peer Lending", "Individual Stocks",
                "Cryptocurrency", "Other Assets", "Credit Card Debt", "Auto Loan",
                "Personal Loan", "Student Loan", "Other Debts"
            ],
            "default": "Checking Account"
        },
        "name": {"type": str, "default": ""},
        "value": {"type": float, "default": 0.0},
        "interest_rate": {
            "type": float,
            "default": 0.0,
            "only_show_if": {
                "kwargs": {"type": "type"},
                "func": lambda type: type in [
                    "Home (Being Paid Off)", "Credit Card Debt", "Auto Loan",
                    "Personal Loan", "Student Loan", "Other Debts",
                    "High Yield Savings", "Savings Account"
                ]
            }
        },
        "remaining_term": {
            "type": int,
            "default": 30,
            "only_show_if": {
                "kwargs": {"type": "type"},
                "func": lambda type: type in [
                    "Home (Being Paid Off)", "Auto Loan", "Personal Loan",
                    "Student Loan", "Other Debts"
                ]
            }
        }
    }
    
    user_data['assets_and_debts'] = generate_repeating_field_group(asset_debt_keys, "asset_debt", user_data.get('assets_and_debts', []))
    
    # Existing Investment Allocation section
    st.subheader("Investment Allocation")

    investment_types = [
        'index_funds', 'bonds', 'rental_real_estate', 'retirement_accounts',
        'high_yield_savings', 'peer_to_peer_lending', 'individual_stocks',
        'cryptocurrency', 'other'
    ]

    # Initialize session state for investment allocations
    if 'investments' not in st.session_state:
        st.session_state.investments = {
            inv_type: user_data.get(f'investment_{inv_type}', 0.0)
            for inv_type in investment_types
        }
        # If all values are 0, set a default distribution
        if sum(st.session_state.investments.values()) == 0:
            default_value = 100 / len(investment_types)
            for inv_type in investment_types:
                st.session_state.investments[inv_type] = default_value

    def normalize_allocations(changed_type):
        changed_value = st.session_state[f'slider_{changed_type}']
        st.session_state.investments[changed_type] = changed_value

        other_types = [t for t in investment_types if t != changed_type]
        other_total = sum(st.session_state.investments[t] for t in other_types)
        remaining = 100 - changed_value

        if other_total == 0:
            # Distribute the remaining evenly among other types
            for t in other_types:
                st.session_state.investments[t] = remaining / (len(investment_types) - 1)
        else:
            # Adjust other values proportionally
            factor = remaining / other_total
            for t in other_types:
                st.session_state.investments[t] *= factor

        # Update all slider values
        for inv_type in investment_types:
            st.session_state[f'slider_{inv_type}'] = st.session_state.investments[inv_type]

    # Create sliders for each investment type
    for inv_type in investment_types:
        st.slider(
            f"{inv_type.replace('_', ' ').title()} Allocation (%)",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.investments[inv_type],
            key=f'slider_{inv_type}',
            on_change=normalize_allocations,
            args=(inv_type,)
        )

    # Display total allocation
    total_allocation = sum(st.session_state.investments.values())
    st.write(f"Total Allocation: {total_allocation:.2f}%")
    if abs(total_allocation - 100) > 0.01:
        st.warning("Total allocation should be 100%")

    # Update user_data with the new allocations
    for inv_type in investment_types:
        user_data[f'investment_{inv_type}'] = st.session_state.investments[inv_type]

    # Display total allocation
    total_allocation = sum(st.session_state.investments.values())
    if abs(total_allocation - 100) > 0.01:
        st.warning("Total allocation should be 100%")

    # Update user_data with the new allocations
    for inv_type in investment_types:
        user_data[f'investment_{inv_type}'] = st.session_state.investments[inv_type]

def milestones_page(user_data, milestone_keys=milestone_keys):
    st.header("Milestones")
    
    def update_cities(country):
        cities = sorted(cost_of_living[cost_of_living['country'] == country]['city'].unique().tolist())
        return cities if cities else ["No cities available"]

    budget_fields = {}
    for item in user_data.get('budget_items', []):
        budget_fields[f"budget_{item['name'].lower().replace(' ', '_') if "name" in item.keys() else item["type"]}_{item['frequency']}"] = {
            "type": float,
            "default": item['value'],
            "only_show_if": {
                "kwargs": {"change_budget": "change_budget"},
                "func": lambda change_budget: change_budget
            }
        }

    income_fields = {}
    for source in (user_data.get('income', []) if isinstance(user_data.get('income', []), list) else []):
        for key, value in income_keys.items(): #FIX THIS
            income_fields[f"income_{source['name'].lower().replace(' ', '_')}_{key}"] = {
                **value,
                "default": source.get(key, value['default']),
                "only_show_if": {
                    "kwargs": {"change_income": "change_income"},
                    "func": lambda change_income: change_income
                }
            }

    milestone_keys = { **milestone_keys, **budget_fields, **income_fields }


    user_data['milestones'] = generate_repeating_field_group(milestone_keys, "milestone", user_data.get('milestones', []))
    #update the date field to use iso format
    for milestone in user_data['milestones']:
        if "date" in milestone.keys():
            milestone['date'] = milestone['date'].isoformat()

def retirement_page(user_data):
    st.header("Retirement Planning")
    
    retirement_goal_method = st.selectbox(
        "Retirement Goal Method",
        options=["Safe Withdrawal Rate", "Simulate Additional Years with Reduced Income"]
    )
    
    if retirement_goal_method == "Safe Withdrawal Rate":
        user_data['post_retirement_expenses'] = st.number_input(
            "Post Retirement Expenses",
            min_value=0.0,
            value=user_data.get('post_retirement_expenses', 0.0),
            step=1000.0,
            help="What you want to live off of in your early retirement. It will grow with inflation."
        )
        tooltip("This is the amount you expect to spend each year in retirement. It should be adjusted for inflation.")
        
        user_data['average_post_retirement_income'] = st.number_input(
            "Average Post Retirement Income (not including investments)",
            min_value=0.0,
            value=user_data.get('average_post_retirement_income', 0.0),
            step=1000.0
        )
        tooltip("This is the amount you expect to earn each year in retirement outside of your investment. It should be adjusted for inflation.")
        
        user_data['withdrawal_rate'] = st.slider(
            "Withdrawal Rate",
            min_value=0.03,
            max_value=0.05,
            value=user_data.get('withdrawal_rate', 0.04),
            step=0.001,
            format="%.3f"
        )
        tooltip("The withdrawal rate is the percentage of your retirement portfolio you plan to withdraw each year. A rate of 0.04 (4%) is often considered safe for long-term retirement.")
        
        user_data['adjust_for_inflation'] = st.checkbox(
            "Adjust withdrawal rate for inflation",
            value=user_data.get('adjust_for_inflation', True)
        )
        tooltip("If checked, the withdrawal amount will increase each year with inflation to maintain purchasing power.")
        
    elif retirement_goal_method == "Simulate Additional Years with Reduced Income":
        user_data['remove_income_sources'] = {}
        for income_source in (user_data.get('income', []) if isinstance(user_data.get('income'), list) else []):
            remove = st.checkbox(f"Remove {income_source['name']}", key=f"remove_{income_source['name']}")
            user_data['remove_income_sources'][income_source['name']] = remove
            user_data['additional_retirement_income'] = st.number_input(
                "Annual Additional Retirement Income",
                min_value=0.0,
                value=user_data.get('additional_retirement_income', 0.0),
                step=1000.0
            )
        
        user_data['additional_simulation_years'] = st.slider(
            "Additional Simulation Years",
            min_value=10,
            max_value=50,
            value=user_data.get('additional_simulation_years', 30),
            step=1
        )
        
    user_data['retirement_goal_method'] = retirement_goal_method

def main():
    st.title("FIRESight - Your Path to Financial Independence")

    # Check if user is logged in
    if 'user_id' not in st.session_state:
        st.error("Please log in to access your profile.")
        st.stop()

    user_id = st.session_state['user_id']
    user_data = load_user_profile(user_id)

    if user_data is None:
        st.warning("No profile found. Creating a new profile.")
        user_data = {}

    # Navigation
    pages = {
        "Personal Info & Settings": personal_info_and_simulation_settings_page,
        "Income": income_page,
        "Budget": budget_page,
        "Investments": investments_page,
        "Milestones": milestones_page,
        "Retirement Planning": retirement_page
    }

    selection = st.sidebar.radio("Navigation", list(pages.keys()))

    # Display selected page
    # Note: No assignment to user_data here
    pages[selection](user_data)

    # Save button
    if st.sidebar.button("Save Profile"):
        save_user_profile(user_id, user_data)
        st.sidebar.success("Profile saved successfully!")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("FIRESight v1.0 - Your journey to financial independence starts here!")

if __name__ == "__main__":
    main()