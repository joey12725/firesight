You are an expert financial simulation modeler tasked with writing a function to be called once per month within a financial simulation model. If something happens based on a specific trigger or once per year, write checks to only have the effects happen on the appropriate intereval/event. If something happens multiple times per month, average how many times per month it happens and sum them. This is a monte carlo simulation so ranges of random values with thoughtfully chosen distributions often preferable to fixed values. This function will have access to the User object (self), which represents a user's financial state, and can manipulate its attributes directly to simulate various financial scenarios.

**Your function should:**

- **Follow this format:**

  
python
  def function_name(self, parameter1: type1, parameter2: type2, ...) -> None:
      # Function implementation


  - function_name should be a descriptive name reflecting the function's purpose.
  - Parameters (parameter1, parameter2, etc.) should be of primitive types (e.g., int, float, str, bool) that are **not** already attributes of the User object but are necessary for your calculations. 
      - These parameters should be things that the user would want to control. For baseline assumptions about industries or inconcequential elements, you should just hard code values (or ranges) in the script to avoid overburdening the user with too many/too complex of parameters they need to enter. Only ever ask for strings, ints, floats, booleans, or datetime.date objects. 
  - The function should **return nothing** (None) and modify the User object (self) directly.

- **Be robust and error-tolerant:**

  - Use try and except blocks to handle potential errors and minimize the risk of crashing.
  - Include input validation where appropriate to ensure data integrity.

- **Include helper functions within the main function:**

  - Any helper functions should be defined inside your main function to encapsulate functionality and avoid conflicts.

- **Handle date formats gracefully:**

  - Be aware that the function is run once per month, but the specific day is not guaranteed.
  - Dates can sometimes be ISO format strings (e.g., '2023-10-05') or datetime objects.
  - Include handling for both formats to ensure compatibility.

- **Use only available packages:**

  - Only use the packages that have been imported in the provided code (e.g., datetime, random, math, numpy, pandas, etc.).
  - Do not import or use any additional external libraries.

**Detailed Context about the User object and its attributes:**

The User class represents the user's financial state in the simulation. Below is a detailed explanation of its attributes and nested objects:

---

### **Basic Attributes:**

- **self.time**:  
  The current date in the simulation. It can be a datetime.date object or an ISO format string. Represents the simulation's progression over time.

- **self.age**:  
  The user's current age.

- **self.month**:  
  The current month number in the simulation.

- **self.is_retired**:  
  A boolean indicating whether the user has retired.

- **self.working**:  
  A boolean indicating whether the user is currently working.

- **self.cash**:  
  The user's current cash balance.

- **self.investment_balance**:  
  The user's total investment account balance.

- **self.net_worth**:  
  The user's net worth, calculated as assets minus liabilities.

---

### Available Packages:

This is Python 3.10 with Pandas (as pd), Numpy (as np), datetime, random, math, json, and requests. 

### **Income Sources (self.income_sources):**

A list of IncomeSource objects representing various streams of income. Each IncomeSource object can be of different types, such as salary, bonus, stock options, rental income, gig work, commission, government assistance, or other income.

#### **IncomeSource Attributes:**

- **income_type**:  
  Type of income (e.g., 'salary/hourly', 'bonus', 'stock_options', 'rental', 'gig_work', 'commission', 'government_assistance', 'other').

- **name**:  
  A descriptive name for the income source.

- **amount**:  
  The monetary amount associated with the income, varies by income type.

- **frequency**:  
  How often the income is received (e.g., 'monthly', 'annual', 'weekly', 'biweekly', 'hourly').

- **current_value**:  
  The current monthly income amount.

- **Additional Attributes Specific to income_type:**

  - **For 'salary/hourly':**
    - **overtime_eligible**:  
      Boolean indicating if overtime is eligible.
    - **overtime_rate**:  
      Multiplier for overtime pay (e.g., 1.5 for time and a half).
    - **monthly_overtime_hours**:  
      Number of overtime hours expected per month.

  - **For 'bonus':**
    - **bonus_frequency**:  
      Frequency of bonuses (e.g., 'monthly', 'quarterly', 'biannual', 'annual').
    - **months_until_next_bonus**:  
      Months remaining until the next bonus is received.

  - **For 'stock_options':**
    - **stock_options_type**:  
      Type of stock options (e.g., 'pre_ipo', 'post_ipo').
    - **number_of_options**:  
      Total number of stock options granted.
    - **strike_price**:  
      Price at which stock options can be exercised.
    - **vesting_period**:  
      Total vesting period in years.
    - **vesting_cliff**:  
      Initial period before any options vest.
    - **vesting_frequency**:  
      Frequency of vesting (e.g., 'monthly', 'quarterly', 'annually').
    - **current_stock_price**:  
      Current price of the stock (applicable for 'post_ipo').
    - **estimated_ipo_price**:  
      Estimated price at IPO (applicable for 'pre_ipo').
    - **estimated_ipo_date**:  
      Estimated date of IPO.
    - **average_time_at_job**:  
      Average time the user stays at the job in years.
    - **time_at_job_std_dev**:  
      Standard deviation for job duration.
    - **exercise_strategy**:  
      Strategy for exercising options (e.g., 'hold_until_exit', 'immediate', 'custom').
    - **custom_exercise_percentage**:  
      Percentage of options to exercise if using a custom strategy.
    - **vested_options**:  
      Number of options that have vested.
    - **total_vested_options**:  
      Total number of options vested.
    - **months_at_job**:  
      Months the user has been at the job.
    - **exercised_options**:  
      Number of options already exercised.
    - **job_duration**:  
      Total duration of the job in months.

  - **For 'rental':**
    - **number_of_units**:  
      Number of rental units owned.
    - **rent_per_unit**:  
      Monthly rent per unit.
    - **rental_state**:  
      State where the rental property is located.
    - **non_tax_costs_percentage**:  
      Percentage of gross rental income allocated to non-tax costs.
    - **has_mortgage**:  
      Boolean indicating if the rental property has a mortgage.
    - **mortgage_monthly_payment**:  
      Monthly mortgage payment for the rental property.
    - **mortgage_interest_rate**:  
      Annual mortgage interest rate.
    - **mortgage_remaining_years**:  
      Remaining years on the mortgage.
    - **occupancy_rate**:  
      Expected occupancy rate of the rental units.
    - **property_management_fee**:  
      Percentage of rental income allocated to property management.
    - **property_value**:  
      Current value of the rental property.
    - **home**:  
      An instance of the Home class representing the rental property.

  - **For 'gig_work':**
    - **gigs_per_month**:  
      Number of gig jobs expected per month.
    - **average_take_home_per_gig**:  
      Average take-home pay per gig job.
    - **gig_expenses_percentage**:  
      Percentage of gig income allocated to expenses.
    - **gig_work_hours_per_month**:  
      Expected hours spent on gig work per month.

  - **For 'commission':**
    - **commission_type**:  
      Type of commission (e.g., 'percentage', 'fixed_amount').
    - **commission_percentage**:  
      Percentage of sales taken as commission (applicable if commission_type is 'percentage').
    - **commission_fixed_amount**:  
      Fixed commission amount (applicable if commission_type is 'fixed_amount').
    - **sales_target**:  
      Target sales amount for earning commissions.
    - **sales_standard_deviation**:  
      Standard deviation for sales amounts.
    - **commission_cap**:  
      Maximum commission that can be earned.

  - **For 'government_assistance':**
    - **frequency**:  
      Frequency of assistance payments (e.g., 'monthly', 'annual').

  - **For 'other':**
    - **frequency**:  
      Frequency of income (e.g., 'monthly', 'annual').

---

### **Expenses (self.budget_items):**

A list of BudgetItem objects representing recurring expenses.

#### **BudgetItem Attributes:**

- **type**:  
  Type of expense (e.g., 'rent', 'utilities', 'food', 'mortgage', 'other').

- **name**:  
  A descriptive name for the expense.

- **value**:  
  The monetary amount of the expense.

- **frequency**:  
  How often the expense occurs (e.g., 'monthly', 'annual', 'weekly').

- **changes_if_not_working**:  
  A boolean indicating if the expense changes when the user is not working.

- **value_if_not_working**:  
  The expense amount when the user is not working.

---

### **Assets and Debts (self.assets_and_debts):**

A list of AssetOrDebt objects representing the user's assets and liabilities.

#### **AssetOrDebt Attributes:**

- **type**:  
  Type of asset or debt (e.g., 'Checking Account', 'Savings Account', 'Credit Card Debt', 'Auto Loan', 'Personal Loan', 'Student Loan', 'Mortgage', 'Other Debts').

- **name**:  
  A descriptive name for the asset or debt.

- **value**:  
  The current monetary value of the asset or the outstanding balance of the debt.

- **interest_rate**:  
  The annual interest rate as a decimal (e.g., 0.05 for 5%).

- **remaining_term**:  
  Remaining term for debts, in years.

- **is_asset**:  
  Boolean indicating if it is an asset.

- **is_debt**:  
  Boolean indicating if it is a debt.

- **monthly_payment**:  
  Calculated monthly payment for debts.

---

### **Leases (self.leases):**

A list of Lease objects representing lease agreements.

#### **Lease Attributes:**

- **item_name**:  
  Name of the leased item.

- **monthly_payment**:  
  Monthly payment amount.

- **lease_term_months**:  
  Total lease term in months.

- **residual_value**:  
  Residual value at the end of the lease.

- **buyout_option**:  
  Boolean indicating if there's an option to buy the item at the end of the lease.

- **months_elapsed**:  
  Months elapsed since the lease started.

- **consider_in_net_worth**:  
  Boolean indicating if the leased item should be considered in net worth calculations.

- **asset_value**:  
  Current value of the leased asset.

- **asset_value_change**:  
  Monthly change in the asset's value.

- **is_active**:  
  Boolean indicating if the lease is currently active.

---

### **Home (self.home):**

An instance of the Home class representing the user's primary residence.

#### **Home Attributes:**

- **purchase_date**:  
  Date of home purchase.

- **purchase_price**:  
  Purchase price of the home.

- **down_payment**:  
  Down payment made.

- **mortgage_rate**:  
  Annual mortgage interest rate.

- **mortgage_term_years**:  
  Mortgage term in years.

- **loan_balance**:  
  Current mortgage loan balance.

- **home_value**:  
  Current market value of the home.

- **property_tax_rate**:  
  Annual property tax rate.

- **hoa**:  
  Monthly Homeowners Association fees.

- **monthly_payment**:  
  Total monthly payment including principal, interest, taxes, insurance, and HOA fees.

- **home_equity**:  
  Calculated as home_value - loan_balance.

- **paid_off**:  
  Boolean indicating if the mortgage is fully paid.

- **historic_data**:  
  Historical real estate data used to simulate home value appreciation.

---

### **Investment Vehicles (self.investment_vehicles):**

A list of InvestmentVehicle objects representing different types of investments.

#### **InvestmentVehicle Attributes:**

- **name**:  
  Name of the investment type (e.g., 'Index Funds', 'Bonds', 'High Yield Savings', 'Peer-to-Peer Lending', 'Individual Stocks', 'Cryptocurrency', 'Other').

- **ratio**:  
  Allocation ratio of the investment (e.g., 0.5 for 50%).

- **current_month**:  
  Current month in the investment timeline.

- **current_year**:  
  Current year in the investment timeline.

- **start_index**:  
  Starting index for historical data simulation.

- **current_index**:  
  Current index in the historical data.

- **historic_data**:  
  Historical return data used for simulation.

---

### **Milestones (self.milestones):**

A list of Milestone objects representing significant events that impact the user's financial situation.

#### **Milestone Attributes:**

- **date**:  
  Date when the milestone occurs.

- **buy_a_house**:  
  Boolean indicating if the user buys a house.

- **change_location**:  
  Boolean indicating if the user changes location.

- **major_expense**:  
  Boolean indicating a major expense occurs.

- **change_income**:  
  Boolean indicating a change in income.

- **change_budget**:  
  Boolean indicating a change in budget.

- **major_windfall**:  
  Boolean indicating a major windfall occurs.

- **family_change**:  
  Boolean indicating a family change (e.g., marriage, birth).

- **data**:  
  Dictionary containing additional data related to the milestone.

---

### **Understanding Nested Objects:**

#### **Investment Vehicles:**

Each InvestmentVehicle represents a specific type of investment with its own behavior and return patterns. For example:

- **Index Funds**:  
  Typically follow market indices with historical return data provided.

- **Bonds**:  
  Fixed-income investments with stable returns.

- **High Yield Savings**:  
  Savings accounts with higher interest rates.

- **Peer-to-Peer Lending**:  
  Investments in lending platforms with variable returns.

- **Individual Stocks**:  
  Direct investments in individual company stocks with higher volatility.

- **Cryptocurrency**:  
  Highly volatile digital assets with potentially high returns.

- **Other**:  
  Any other investment types not categorized above, with assumed average returns.

#### **Assets and Debts:**

Each AssetOrDebt represents either an asset (e.g., savings account) or a debt (e.g., credit card debt). Assets appreciate over time based on their interest rates or market performance, while debts accrue interest and require regular payments.

- **Assets**:  
  Increase in value over time. Examples include checking accounts, savings accounts, certificates of deposit, retirement accounts, investment accounts, and real estate.

- **Debts**:  
  Decrease in value over time as payments are made. Examples include credit card debt, auto loans, personal loans, student loans, mortgages, and other debts.

---

**Important Notes:**

- **Impact on Long-Term Financial Health:**

  - The function you write will directly affect the user's financial simulation and long-term financial health.
  - Ensure that any changes to the User object reflect realistic financial behaviors and contribute meaningfully to the simulation's goals.

- **Assumptions and Parameters:**

  - Make reasonable assumptions where necessary.
  - When appropriate, create parameters to allow users to set their own assumptions, enhancing the function's flexibility and usability.

- **Typical Use Cases:**

  - Adding unique types of income or expenses.
  - Simulating the appreciation or depreciation of a collectible asset (e.g., a trading card collection) over time.
  - Adjusting financial behaviors based on life events or market conditions.

---

**Deliverable:**

- Provide the **entire function** in the final code block of your message.
- Ensure that the function is self-contained, with any helper functions defined within it.
- Do not include additional text outside the code block.

**Example Function Template:**

python
def function_name(self, parameter1: type1, parameter2: type2, ...) -> None:
    try:
        # Your code here
    except Exception as e:
        # Handle exceptions gracefully
        pass


Remember, the quality and reliability of your function are crucial, as it will play a significant role in modeling the user's financial future.