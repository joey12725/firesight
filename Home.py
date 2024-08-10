import streamlit as st
from streamlit_lottie import st_lottie
import requests

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

st.set_page_config(
    page_title="FIRESight - Your Path to Financial Independence",
    page_icon="🔥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    h1, h2, h3 {
        color: #FF6B6B;
    }
    .stButton>button {
        background-color: #FF6B6B;
        color: white;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #FF8E8E;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Header
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🔥 FIRESight")
    st.subheader("Illuminate Your Path to Financial Independence")

with col2:
    lottie_url = "https://lottie.host/50664d6f-1780-4c56-b29c-0576fc37a30a/BnsjF5Efz4.json"
    lottie_json = load_lottieurl(lottie_url)
    st_lottie(lottie_json, height=150, key="header_animation")

st.markdown("---")

# Introduction to FIRE
st.header("What is FIRE?")
st.write("""
FIRE stands for **Financial Independence, Retire Early**. It's a movement and lifestyle approach focused on aggressive savings and investment strategies that enable individuals to retire much earlier than traditional retirement plans would allow. The core principles of FIRE include:

- 🎯 **Setting Ambitious Financial Goals**: FIRE adherents typically aim to save 50-70% of their income, far exceeding the conventional wisdom of saving 10-15% for retirement.

- 💰 **Maximizing Savings Rate**: This involves not just earning more, but also significantly reducing expenses. FIRE followers often embrace minimalism and frugality as key lifestyle choices.

- 📈 **Strategic Investing**: FIRE strategies often involve low-cost index fund investing, real estate investments, and other passive income streams to grow wealth rapidly and sustainably.

- 🧮 **The 4% Rule**: Many in the FIRE community use the 4% rule as a benchmark, which suggests that you can withdraw 4% of your portfolio annually in retirement with a low risk of running out of money.

- 🏖️ **Redefining Retirement**: FIRE isn't just about retiring early to a life of leisure. For many, it's about gaining the financial freedom to pursue passion projects, start businesses, or work on their own terms.

- 📊 **Continuous Learning and Optimization**: FIRE requires ongoing financial education, regular review of investment strategies, and adaptation to changing market conditions and personal circumstances.

The FIRE movement challenges conventional notions about work, savings, and retirement, offering a path to financial freedom that can be achieved well before the traditional retirement age.
""")

st.markdown("---")

# Why FIRESight?
st.header("Why Choose FIRESight?")
st.write("""
FIRESight stands out as a superior tool for those pursuing FIRE due to its comprehensive approach, advanced features, and user-centric design. Here's what sets FIRESight apart:
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🚀 Advanced Simulations")
    st.write("""
    - **Monte Carlo Simulations**: Unlike basic calculators that use fixed return rates, FIRESight runs thousands of simulations with varying market conditions to provide a more realistic view of potential outcomes.
    - **Real-world Market Modeling**: Our simulations incorporate historical market data and volatility, including bull and bear markets, to better reflect real-world investment scenarios.
    - **Multiple Investment Vehicles**: FIRESight accounts for various investment types including stocks, bonds, real estate, and more, allowing for truly diversified portfolio modeling.
    """)

with col2:
    st.subheader("🎯 Personalized Planning")
    st.write("""
    - **Tailored Financial Profiles**: Input your unique financial situation, including income, expenses, savings, and existing investments for a truly personalized analysis.
    - **Life Event Adjustments**: Plan for major life events such as home purchases, career changes, or starting a family, and see how they impact your FIRE journey.
    - **Tax Optimization**: FIRESight considers tax implications of different investment strategies and retirement account types (401k, IRA, HSA) to maximize your after-tax returns.
    - **Geographic Flexibility**: Account for potential relocations and cost of living changes in your FIRE plan.
    """)

with col3:
    st.subheader("💡 Intelligent Insights")
    st.write("""
    - **AI-Powered Analysis**: Leverage machine learning algorithms to uncover insights and optimization opportunities in your financial plan.
    - **Natural Language Queries**: Ask questions about your FIRE plan in plain English and receive detailed, data-driven responses.
    - **Scenario Comparison**: Easily compare different financial scenarios to make informed decisions about saving, investing, and major life choices.
    - **Dynamic Visualizations**: Interact with clear, informative graphs and charts that bring your financial data to life and make complex information easy to understand.
    """)

st.markdown("---")
col1, col2 = st.columns(2)
# How FIRESight Works
with col1:
    lottie_url = "https://lottie.host/e1337b35-cba8-4685-8e88-a2764a4114e8/6fP1YsKkYt.json"
    lottie_json = load_lottieurl(lottie_url)
    st_lottie(lottie_json, height=1200, key="how_it_works_animation")

with col2:
    st.header("How FIRESight Works")
    st.write("""
    FIRESight employs a sophisticated, multi-step process to help you plan and achieve your FIRE goals:

    1. **Comprehensive Data Input**: 
    - Enter detailed information about your income, expenses, savings, and current investments.
    - Input your risk tolerance, retirement goals, and lifestyle preferences.
    - Add planned major life events or purchases that could impact your financial journey.

    2. **Advanced Financial Modeling**:
    - Our algorithms create a digital twin of your financial life, incorporating all aspects of your current and projected future situation.
    - We use machine learning models trained on vast amounts of historical financial data to project future market scenarios.

    3. **Monte Carlo Simulations**:
    - FIRESight runs thousands of simulations, each representing a possible future financial scenario.
    - These simulations account for market volatility, inflation, and the specific dynamics of different asset classes.

    4. **Tax Optimization**:
    - The system models various tax scenarios, including current tax laws and projected changes.
    - It suggests optimal strategies for tax-advantaged accounts and withdrawal sequences in retirement.

    5. **Risk Analysis**:
    - FIRESight assesses the probability of achieving your FIRE goals under different risk profiles.
    - It provides clear visualizations of best-case, worst-case, and most likely scenarios.

    6. **AI-Powered Insights**:
    - Our AI analyzes your results and compares them to successful FIRE strategies to generate personalized recommendations.
    - The system identifies potential weaknesses in your plan and suggests specific improvements.

    7. **Interactive Results Dashboard**:
    - Explore your results through an intuitive, interactive dashboard.
    - Visualize your projected net worth, investment growth, and withdrawal strategies.

    8. **Scenario Planning**:
    - Use the platform to model "what-if" scenarios, such as career changes, market downturns, or unexpected windfalls.
    - Compare different strategies side-by-side to make informed decisions.

    9. **Ongoing Optimization**:
    - Regularly update your information to refine projections and adjust your strategy.
    - Receive alerts and suggestions when new opportunities for optimization arise.

    By combining cutting-edge technology with comprehensive financial planning principles, FIRESight provides a robust, dynamic tool for anyone serious about achieving financial independence and retiring early.
    """)

st.markdown("---")

# Key Features
st.header("Key Features")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Comprehensive Modeling")
    st.write("""
    - **Multi-Stream Income Projection**: Model primary job income, side hustles, rental income, and passive income sources.
    - **Diverse Investment Portfolios**: Simulate a wide range of investment vehicles including stocks, bonds, REITs, cryptocurrencies, and more.
    - **Real Estate Investment Analysis**: Evaluate potential property investments, considering factors like appreciation, rental income, and maintenance costs.
    - **Tax-Advantaged Account Optimization**: Maximize the benefits of 401(k)s, IRAs, HSAs, and other tax-advantaged accounts.
    - **Inflation and Market Volatility**: Account for varying inflation rates and market conditions in long-term projections.
    - **Debt Repayment Strategies**: Optimize strategies for paying off mortgages, student loans, and other debts.
    """)
    
    st.subheader("🏠 Life Event Planning")
    st.write("""
    - **Home Purchase Simulation**: Model the impact of buying a home, including down payments, mortgage rates, and property appreciation.
    - **Career Change Analysis**: Evaluate the long-term effects of career moves, including salary changes and potential retraining costs.
    - **Family Planning**: Account for the financial impact of having children, including education costs and changes in household expenses.
    - **Geographic Relocation**: Assess the financial implications of moving to different cities or countries, considering cost of living adjustments.
    - **Education Expense Forecasting**: Plan for future education costs, whether for yourself or dependents.
    - **Healthcare Cost Projection**: Estimate future healthcare expenses based on age, health status, and location.
    """)

with col2:
    st.subheader("🤖 AI-Powered Insights")
    st.write("""
    - **Natural Language Queries**: Ask complex financial questions in plain English and receive detailed, data-driven answers.
    - **Scenario Comparisons**: Quickly compare multiple financial scenarios to understand trade-offs and make informed decisions.
    - **Personalized Recommendations**: Receive tailored advice based on your unique financial situation and goals.
    - **Risk Analysis and Mitigation**: Identify potential risks in your FIRE strategy and get suggestions for mitigating them.
    - **Behavioral Finance Insights**: Get alerts about potential behavioral biases that might be affecting your financial decisions.
    - **Market Trend Analysis**: Leverage AI to identify relevant market trends that could impact your FIRE journey.
    """)
    
    st.subheader("📈 Dynamic Visualizations")
    st.write("""
    - **Net Worth Projections**: View interactive charts showing projected net worth under various scenarios.
    - **Retirement Age Probability**: Visualize the likelihood of reaching your FIRE goal at different ages.
    - **Investment Allocation Optimization**: See how different asset allocations could affect your long-term financial outcomes.
    - **Savings Rate Impact Analysis**: Understand how changes in your savings rate influence your time to reach FIRE.
    - **Cash Flow Forecasting**: Get a clear picture of projected income, expenses, and savings over time.
    - **Tax Burden Visualization**: See how your tax liability is projected to change over time and in different scenarios.
    - **Withdrawal Strategy Modeling**: Visualize different retirement withdrawal strategies and their long-term impacts.
    """)

st.markdown("---")

# Call to Action
st.header("Ready to Ignite Your FIRE Journey?")
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.write("""
    Take the first step towards financial independence today. FIRESight offers the most comprehensive, technologically advanced platform for planning and achieving your FIRE goals. 
    
    By creating an account, you'll gain access to:
    - Personalized financial projections
    - Advanced scenario planning tools
    - AI-powered insights and recommendations
    - A supportive community of like-minded individuals
    
    Don't leave your financial future to chance. Let FIRESight illuminate the path to your early retirement and financial freedom.
    """)
    st.page_link("pages/Create Account and Log in.py", label="Get Started", icon="🔥") 

st.markdown("---")

# Footer
st.write("© 2023 FIRESight. All rights reserved. | Terms of Service | Privacy Policy")