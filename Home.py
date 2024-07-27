import streamlit as st

st.set_page_config(
    page_title="Welcome",
    page_icon="🔥",
)

st.write("# FIRESight")

st.markdown(
    """

## Overview

The FIRE (Financial Independence, Retire Early) Simulator is designed to help you plan your path to financial independence. This app provides powerful tools to model various financial scenarios, giving you insights into how different decisions can impact your goal of retiring early.

### Key Features

### 1. Scenario Planning
- **Compare Different Life Scenarios**: See how major life changes, like buying a house in 3 years or moving to a different city in 8 years, will affect your financial independence (FI) date. Easily visualize the long-term impact of your decisions.

### 2. Advanced Investment Simulations
- **Market Behavior Simulation**: Model broader market trends including booms and busts over months and years, not just average monthly returns. This feature helps you prepare for real-world market conditions.

### 3. Interactive Chatbot
- **Natural Language Queries**: Ask questions like, "What impact would buying a $350k house in 2 years with a gifted downpayment have on my FI date?" The chatbot will provide a detailed answer and a graph comparing your current plan to the new scenario.

### 4. International Relocation Support
- **Cost and Standard of Living Adjustments**: Plan moves to different cities or countries, adjusting for both cost of living and standard of living changes. For example, if you move to NYC, the app can factor in ditching your car and living in a smaller space.

### 5. Major Purchase Options
- **Flexible Payment Options**: Evaluate different payment methods for significant purchases, such as financing, leasing, or paying upfront with tax deductions. This feature helps you choose the best financial strategy for large expenses.

### 6. Detailed Financial Insights
- **Visualize Your Financial Future**: Run detailed simulations and view your projected net worth, investments, and retirement age. The app generates comprehensive charts and graphs to help you understand your financial trajectory.

### 7. Accessible Premium Features
- **Affordable Access**: While the basic app features are free, advanced functionalities are available for a small fee (e.g., $3), making powerful financial planning tools accessible to everyone.

## Get Started

Plan your journey to financial independence with the FIRE Simulator. Whether you're making big life changes, preparing for market fluctuations, or planning significant purchases, this app gives you the insights and tools you need to make informed financial decisions.

Try FIRESight.life today and take control of your financial future!
"""
)