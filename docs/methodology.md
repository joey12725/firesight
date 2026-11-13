# How the simulation works

FIRESight answers one question: *given my income, spending, debts, portfolio and plans, at what age am I financially independent, and how sure is that?* It does this by living out your financial life one month at a time, many times over, under different simulated markets.

All of it lives in [`FIRE.py`](../FIRE.py). The Streamlit pages only collect inputs and draw results.

## One simulated month

`User.step_month()` runs this sequence for every month of the horizon:

1. **Advance the clock.** Age goes up by 1/12 and the date moves forward.
2. **Milestones.** Anything dated this month fires: buy a house (cash goes to the down payment, rent is swapped for a mortgage payment), a major purchase (cash, financed as a new loan, or leased), a windfall, a move (moving cost plus a spending multiplier, either manual or from the cost-of-living table), or a family change (marriage, birth, divorce, a dependent adult).
3. **Grow income and spending.** Income sources with raises compound annually. Budget items grow with inflation plus your "lifestyle creep" rate.
4. **Earn.** Every income source reports its monthly cash:
   - salary or hourly pay, with optional overtime
   - bonuses on their own cadence
   - commission drawn from a normal distribution around your sales target
   - rental units: rent × occupancy, minus maintenance, management and the property's own mortgage
   - gig work, net of expenses
   - stock options that vest on a cliff and schedule, are worth something after a liquidity event, and reset if you change jobs (job tenure is random)
   - after 67, a simple Social Security amount
   - once you stop working, only rental income keeps paying.
5. **Spend.** Budget items, normalized to monthly. Items can have a different value once you stop working (health insurance is the usual one).
6. **Service debts.** Each loan is amortized with the standard formula `P·r(1+r)^n / ((1+r)^n − 1)`. Savings and checking accounts earn their interest.
7. **Manage cash.** Keep an emergency buffer of six months of expenses plus three months of income. Anything above it gets invested at your target allocation. Shortfalls sell investments pro rata.
8. **Market returns.** Each asset class in the portfolio steps forward one month on its own return path (below).
9. **Record** net worth, cash, portfolio, home equity and every line item into the run's time series.
10. **Check for financial independence** (below). The first month it passes, that age is recorded and you stop working.
11. **Taxes,** once every 12 months on that year's income: federal brackets with the standard deduction for single or married filers, your state's brackets from `statetaxes.json`, FICA up to the Social Security wage base, and a child tax credit per dependent.

## Where returns come from

Each asset class has its own return model. All of them generate the whole path up front, so a run is consistent from start to finish.

| Asset class | Model |
|---|---|
| Index funds, retirement accounts | **Block bootstrap** of real monthly US stock-market returns back to 1928 (`stocks.csv`). The model copies random 12-month blocks of history end to end, so streaks, crashes and recoveries keep their real shape instead of being smoothed into a bell curve. |
| Rental real estate, home appreciation | Block bootstrap of monthly US home-price changes (`realestate.csv`). Short-term rentals add volatility and house flipping adds a lot more. |
| Bonds | Three-state Markov chain: normal, rising rates (flat or slightly negative), falling rates (strong). |
| High-yield savings | Two-state chain: stable around 2%/yr, with occasional better months. |
| Peer-to-peer lending | Normal most of the time, with rare "meltdown" stretches of defaults. |
| Individual stocks | Bull, bear and sideways regimes with sticky transitions. |
| Crypto | Mania, crash and normal regimes with very high volatility. |
| Other | Mild bull/bear/stable regimes around 7%/yr. |

The regime models are deliberately simple. They give each asset class a recognizable personality (bonds are boring, crypto is not) and let the portfolio mix change the shape of the outcome distribution, not only its average.

## When are you "financially independent"?

Three goal definitions are built in:

- **Safe withdrawal rate** (default). You're done when net worth ≥ (retirement spending − other retirement income) ÷ withdrawal rate. With a 4% rate that's the familiar 25× rule. The target rises with inflation every month, so you're always chasing today's lifestyle in future dollars.
- **Reduced-income stress test.** Every six months, once net worth passes ten years of expenses, the model clones your current situation, removes the income sources you choose, and runs ten fresh 10-year futures from there. You're retired only if all ten keep at least 90% of their starting net worth.
- **Fixed number.** Retire at a dollar amount.

## Monte Carlo and scenario comparison

`run_monte_carlo_simulation()` repeats the whole life simulation `num_simulations` times with independent random paths, then reports:

- the retirement age of every run that got there, and how many did
- per-month percentiles of net worth (the fan chart)
- an average time series across runs, and every individual run.

Scenario analysis (`scenarios.compare()`) runs your current plan and the changed plan **on the same random seed**. Both versions see identical market histories, job changes and commissions, so the difference between them comes from the decision you're testing and not from one of them getting luckier markets. Pass `seed=` anywhere for fully reproducible results.

## Extending it

- **New asset class:** add a branch in `ReturnGenerator.generate_returns()`, add the name to `INVESTMENT_TYPES`, and add an allocation slider in `pages/Edit Profile.py`.
- **New income type:** add a branch to `IncomeSource.__init__` and `get_monthly_income`, and a choice in `income_keys` in `pages/Edit Profile.py`.
- **Custom monthly logic:** set `user.monthly_hook = fn` on a `User` before running. It's called with the user once per simulated month (for example to model a sabbatical or a mid-career pivot).
- **New goal definition:** add a branch to `User.check_retirement()`.

## Data sources

- `stocks.csv`: monthly US stock-market total returns, January 1928 to November 2020.
- `realestate.csv`: 400 months of US home-price changes.
- `statetaxes.json`: state income-tax brackets (listed by lower threshold) plus property, corporate and sales tax rates for all 50 states, DC and Puerto Rico.
- `cost-of-living.csv`: city-level prices and salaries for several thousand cities worldwide, from the public Numbeo-derived *Global Cost of Living* dataset on Kaggle. Column `x54` (average monthly net salary in USD) is used as the cost-of-living index when a move is set to "adjust for similar quality of life".
- Federal brackets and the standard deduction are 2020 figures.
