# Phase 4: Backtesting (breaches, Kupiec POF test, Basel traffic light)

_Completed 2026-11-23. Every number below comes from running `python run_backtest.py`
on 2026-11-23 (data up to 2026-11-23)._

## Goal

Check whether the Phase 2 VaR forecasts were **right**: count the days when the
actual loss was bigger than the forecast (**breaches**), and test whether there
were too many (or too few) for a 99% model.

**Why a Market Risk team cares:** this is the "validation" in model validation.
Regulators judge a bank's VaR model by its backtest. A model in the red zone gets a
higher capital multiplier and may have to be replaced. Reporting breaches daily is
the core of the job this project mirrors.

## Concepts

### Breach
A day when the loss exceeds the VaR forecast: `actual P&L < −VaR`.
- 23 Mar 2020: VaR ₹2.94L, P&L −₹4.19L → **breach**, ₹1.25L beyond VaR.
- 14 Feb 2020: VaR ₹0.78L, P&L −₹0.17L → no breach.
- A loss *exactly* equal to VaR is not a breach.

### Expected number of breaches
A correct 99% model breaches on 1% of days. Over 250 days that's 2.5; over our
4,755 days it's **47.6**. That's what a correct model is *expected* to produce,
not a limit. Small differences are luck.

### Basel traffic light (on the last 250 days)
| Breaches in 250 days | Zone | Meaning |
|---|---|---|
| 0–4 | Green | Consistent with a correct model |
| 5–9 | Amber | Suspicious; capital multiplier rises |
| 10+ | Red | The model is almost certainly wrong |

### Kupiec POF ("proportion of failures") test
"Is the true breach rate 1%?" Compare how well two rates explain the data: the
claimed rate p = 1% and the observed rate p̂ = breaches ÷ days.
- LR = −2 × [ln L(p) − ln L(p̂)], where ln L(r) = (T − x)·ln(1 − r) + x·ln(r).
- If the model is right, LR follows a chi-squared distribution with 1 degree of
  freedom → p-value. **Reject if p < 0.05** (LR > 3.84).

Worked examples (250 days):
| Breaches | LR | p-value | Verdict |
|---|---|---|---|
| 0 | 5.03 | 0.025 | **Reject**: too cautious |
| 3 | 0.09 | 0.76 | Pass |
| 10 | 12.96 | 0.0003 | Reject: far too many |

**Kupiec is two-sided:** too *few* breaches also fails. A model that never breaches
has VaR set too high, so the bank holds too much capital (money that can't be lent
or invested) and trading limits are needlessly tight. The traffic light only
punishes too many.

**ML link:** backtesting is evaluating on the test set. A breach is a "miss", and
Kupiec checks that the model's *claimed* miss rate (1%) matches its *actual* miss
rate, like checking a classifier's calibration.

### Large samples detect small gaps
53% heads in 10 tosses means nothing; 53% heads in 5,000 tosses is suspicious.
With 4,755 days, even 1.35% vs 1% becomes statistically detectable.

### Clustering (bunching)
A correct model's breaches should be spread out randomly. Ours bunch in crises
(2020, late 2008). Kupiec counts only the *total*, so it can't see this. Clustering
means the model reacts too slowly when volatility jumps, missing exactly when risk
is highest. The **Christoffersen test** checks this (FRAM slide 34; Later Stage).

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `backtest.py` → `find_breaches(var, pnl)` | VaR per day (₹, positive), P&L per day | True/False per day | `pnl.reindex(var.index)` lines dates up; breach = `pnl < -var` |
| `backtest.py` → `kupiec_pof(x, t, p)` | breaches, days, 0.01 | LR, p-value, verdict | `xlogy(a, b)` = a·ln(b) but 0 when a = 0 (no ln(0) crash with zero breaches); `chi2.sf` = 1 − cdf gives the p-value |
| `backtest.py` → `traffic_light(n)` | breaches in 250 days | "green"/"amber"/"red" | Basel thresholds 0–4 / 5–9 / 10+ |
| `backtest.py` → `rolling_zone(breaches, 250)` | daily breaches | rolling 250-day count + zone per day | `.rolling(250).sum()` counts breaches in each trailing year |
| `run_backtest.py` | — | prints the summary, zone shares, breaches per year, biggest breaches; writes `outputs/backtest.csv` | Recomputes Phase 2's rolling VaR, then backtests every model the same way |

**Library functions used for the first time:**
- `scipy.special.xlogy(a, b)`: a × ln(b), but 0 when a = 0.
- `scipy.stats.chi2.sf(x, df)`: the probability of a chi-squared value at least x.
- `Series.rolling(n).sum()`: a sum over each trailing n-row window.
- `Series.groupby(index.year).sum()`: totals per calendar year.
- `value_counts(normalize=True)`: the share of each value.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Breach definition | Loss strictly greater than VaR | Loss ≥ VaR | The standard convention; equality is a measure-zero edge case |
| Kupiec significance level | 5% | 1% | Common default. Historical simulation fails at 5% (p = 0.023) but would pass at 1%; stated openly |
| Sample for Kupiec | The whole history (4,755 days) | Only the last 250 days | More evidence, more power. The traffic light covers the regulator's 250-day view |
| Zone history | Rolling 250-day count for every day | Only today's zone | Shows how often each model would have been amber or red |

## Results (run of 2026-11-23)

**Period:** 2 Sep 2008 → 23 Nov 2026, **4,755 forecast days**. Expected breaches at
1% = **47.6**.

| | Historical | Parametric |
|---|---|---|
| Breaches | **64** | **82** |
| Breach rate | 1.35% | 1.72% |
| Kupiec LR | 5.19 | 20.72 |
| p-value | 0.023 | 0.0000053 |
| Kupiec (5%) | **Reject** (narrowly) | **Reject** (decisively) |
| Breaches in last 250 days | 3 | 7 |
| Zone today | **Green** | **Amber** |

**Share of days in each traffic-light zone** (rolling 250-day count):

| Zone | Historical | Parametric |
|---|---|---|
| Green | 77.7% | 54.3% |
| Amber | 22.3% | 40.6% |
| Red | **0.0%** | **5.1%** |

Worst 250-day count: historical **9** (amber; window ending 23 Mar 2020),
parametric **12** (red; window ending 4 May 2020).

**Breaches per year:**

| | 2008* | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Historical | 5 | 1 | 3 | 6 | 2 | 4 | 1 | 6 | 1 | 4 | 5 | 1 | **8** | 1 | 4 | 3 | 3 | 3 | 3 |
| Parametric | 4 | 1 | 3 | 5 | 1 | 6 | 2 | 8 | 0 | 5 | 6 | 1 | **11** | 4 | 5 | 3 | 6 | 4 | 7 |

\*2008: only 87 forecast days (from 2 Sep); 2026: to 23 Nov (233 days).

**Biggest breaches** (VaR → actual loss, ₹ lakh):

| Historical | Parametric |
|---|---|
| 12 Mar 2020: 1.60 → 3.41 (+1.82) | 23 Mar 2020: 1.36 → 4.19 (+2.83) |
| 16 Mar 2020: 1.95 → 3.71 (+1.76) | 16 Mar 2020: 1.10 → 3.71 (+2.62) |
| 12 Apr 2013: 0.87 → 2.60 (+1.73) | 12 Mar 2020: 0.95 → 3.41 (+2.46) |
| 24 Oct 2008: 2.21 → 3.79 (+1.58) | 12 Apr 2013: 0.89 → 2.60 (+1.71) |
| 9 Mar 2020: 0.93 → 2.37 (+1.44) | 18 Mar 2020: 1.24 → 2.94 (+1.70) |

12 Apr 2013 is Infosys's −21% results day: a single-stock shock that a calm
250-day window couldn't anticipate.

**Verdict:**
- Both models **underestimate risk** (more breaches than 47.6). Parametric is clearly
  worse: 72% too many breaches, because it misses the fat tails.
- Historical simulation is the better model here: green today, never red, and 35%
  too many breaches, which is narrowly rejected over 18 years.
- Breaches cluster in crises, which motivates Expected Shortfall, GARCH/EWMA
  (faster-reacting volatility) and the Christoffersen test (Later Stages).

## Bugs and fixes

1. **The p-value printed as `0.0`.** Rounding to 4 decimal places turned 0.0000053
   into 0.0, which looks like "impossible". **Fix:** print 2 significant figures
   (`5.3e-06`).
2. No logic bugs. The Kupiec function was hand-checked first (0, 3 and 10 breaches
   in 250 days, matching hand calculations to 2 decimal places), and the breach rule
   was checked on the equality edge case.

## Interview questions (with model answers)

1. **How do you backtest a VaR model?**
   Compare each day's VaR forecast (made from earlier data only) with that day's
   actual P&L; a breach is loss > VaR. Count breaches against the expected 1%, apply
   the Basel traffic light to the last 250 days, and run the Kupiec POF test on the
   breach rate.
2. **What is the Kupiec test, and what's its weakness?**
   A likelihood-ratio test of whether the observed breach rate equals the target
   (1%); LR ~ χ²(1). It's two-sided (too few breaches also fails). Its weakness: it
   only uses the count, so it can't detect clustering. That's what Christoffersen's
   independence test adds.
3. **What were your results?**
   Over 4,755 days (47.6 expected), historical simulation had 64 breaches (1.35%,
   Kupiec p = 0.023, narrowly rejected; green today, never red). Parametric had 82
   (1.72%, p ≈ 5e-6, rejected; amber today, red 5% of the time). Breaches clustered
   in 2020 (8 and 11).
4. **Why is a model with zero breaches a problem?**
   Its VaR is too high, so the bank holds excess capital that can't be lent or
   invested and limits are too tight. It isn't measuring risk accurately, so Kupiec
   rejects it.
5. **Historical passes the traffic light most of the time but fails Kupiec. How?**
   Different samples. The traffic light looks at 250 days, where 3 breaches vs 2.5
   expected is noise. Kupiec on 4,755 days has the power to detect that 1.35% is
   above 1%.

## My check questions (2026-11-23)

1. **Q:** Over 4,755 days, about how many breaches should a correct 99% VaR have?
   Historical had 64. Too many or too few, and what does it say?
   **My answer:** 47.6 is the number of days a model is allowed to breach. Both models
   overshot, which tells us how accurate a 99% VaR actually is.
   **Feedback:** Mostly right. 47.6 is the *expected* number for a correct model (not
   a limit). Overshooting means VaR was too low: the models underestimated risk,
   parametric more so.
2. **Q:** A model has 0 breaches in 250 days. The traffic light says green, but Kupiec
   rejects it. Why would a bank be unhappy?
   **My answer:** It is likely to have large capital.
   **Feedback:** Half right. VaR is too high, so the bank holds too much capital,
   which is costly (it can't be lent or invested; limits too tight). The model isn't
   accurate either; it just errs on the safe side.
3. **Q:** 8 breaches in 2020, 1 in 2021. What can Kupiec miss?
   **My answer:** Clusters of losses won't be identified, as only the total count is
   checked.
   **Feedback:** Correct. Clustering means the model reacts too slowly when
   volatility jumps; Christoffersen's test checks independence.

## Next phase

**Phase 5: Breach report.** Turn this backtest into the daily deliverable a risk
team sends: an automated Excel workbook (openpyxl) with a summary sheet (breaches,
Kupiec, traffic light), a breach log (date, VaR, P&L, size of breach, and the asset
that drove the loss), and a VaR-vs-P&L chart.
