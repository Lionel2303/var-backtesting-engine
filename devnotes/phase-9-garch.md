# Phase 9: GARCH(1,1) VaR, with a normal tail and Filtered Historical Simulation

_Completed 2026-11-24. The final numbers come from running `python run_garch.py` on
2026-11-24 (data up to 2026-11-24). The daily re-fit numbers come from the first
version, run on 2026-11-23 (data up to 2026-11-23)._

## Goal

Phase 8 fixed λ by hand (0.94, 0.994). GARCH instead **fits** the volatility dynamics
to the data. This phase answers three questions:
- Does a fitted volatility model beat the fixed-weight ones?
- Does the tail shape (bell curve vs real data) matter once volatility is right?
- How stable are the fitted parameters when you re-estimate them through history?

This is the last model of Stage 2, so the result is a final **6-model backtest on one
common period**.

**Why a Market Risk team cares:** GARCH and Filtered Historical Simulation (FHS) are
standard in bank risk engines. Whether model parameters stay stable is a core
model-validation question.

## Concepts

### GARCH(1,1)
Tomorrow's variance = ω + α × (today's return)² + β × (today's variance).
- **ω** pulls volatility towards a long-run level.
- **α** is the reaction to today's surprise (the model's "eyes").
- **β** is the memory of today's volatility.

Example (in %): ω 0.02, α 0.07, β 0.89, today's σ 0.7%.
- After a calm day (+0.5%): σ = √(0.02 + 0.07×0.25 + 0.89×0.49) = **0.69%**
- After a crash day (−5%): σ = √(0.02 + 0.07×25 + 0.89×0.49) = **1.48%**

Derived quantities:
- **Persistence** = α + β.
- **Half-life of a shock** = ln 0.5 / ln(α+β).
- **Long-run volatility** = √(ω / (1 − α − β)).

**EWMA is the special case** ω = 0, α = 1 − λ, β = λ. That means α+β = 1 and there is
no long-run level, so EWMA never pulls back towards an average.

### Fitting (maximum likelihood)
Choose ω, α, β so that the returns actually seen are as probable as possible. The
`arch` library does the optimising.

**ML link:** this is training a model by maximising log-likelihood, like fitting a
logistic regression.

### Two tails on the same σ
- **Normal:** VaR = 2.326σ, ES = 2.665σ.
- **FHS (Filtered Historical Simulation):**
  1. Divide each past return by its own GARCH σ that day. These are the
     "standardised surprises" ε, in σ units.
  2. VaR = −(1%-worst ε) × σ_tomorrow.
  3. ES = −(average ε in the tail) × σ_tomorrow.

  So the **speed** comes from GARCH and the **fat tails** from the data. Example: the
  5th-worst of 500 surprises is −2.55, and σ = ₹42,000, so VaR = 2.55 × 42,000 =
  ₹1.07 L.

### Re-fit schedule
- **Daily re-fit:** estimate ω, α, β again every day.
- **Monthly re-fit (final):** estimate them every 21 trading days and **hold them
  fixed** in between, so only σ moves with each new return. This is common bank
  practice.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `models/garch.py` → `fit_garch(port_pct, params=None)` | portfolio returns in %, optional held params | `sigma_next`, `std_resid`, `params` | `params=None` fits with `arch_model(..., mean="Zero").fit()`; given params, `model.fix(params)` runs the formula with no optimiser. Results are cached by (dates, length, params) |
| `GARCHVaR(holdings, conf, tail)` | `tail="normal"` or `"fhs"` | VaR / ES | Same `predict`/`predict_es` interface, with an extra optional `params` argument |
| `GARCHVaR.fit_params(window)` | 500-day window | ω, α, β | Used on re-fit days |
| `rolling_garch(model, returns, window, refit_every, ...)` | as `rolling_var` | Series of VaR or ES | Same dates and no-look-ahead windows as `rolling_var`; `(i - window) % refit_every == 0` decides re-fit days |
| `backtest.py` → `compare_models(var, es, actual)` | VaR/ES tables | summary table + breach flags | The same scoring for any number of models; `run_responsive.py` now uses it too |
| `config.py` | — | `GARCH_WINDOW = 500`, `GARCH_REFIT_EVERY = 21` | 1 = daily re-fit |
| `run_garch.py` | — | 6-model tables; `outputs/garch_var.csv` | The `rolling()` helper sends GARCH models to `rolling_garch` and the others to `rolling_var` |

**New Python / libraries:**
- `arch_model(...).fit(disp="off")` and `.fix(params)`
- `res.forecast(horizon=1).variance` and `res.std_resid`
- `warnings.catch_warnings()`: silences warnings while still counting failed fits
- a dict used as a **cache** (memoisation)
- `isinstance(model, GARCHVaR)`
- `%` (remainder)

**Hand-checks (all passed):**
- σ computed by hand from the fitted ω, α, β = 0.7138%, the same as `arch`'s forecast.
- Normal VaR = exactly 2.326σ.
- FHS VaR = 5th-worst ε (−2.55) × σ. The worst ε was −4.59, a fat tail.
- Regression: `run_responsive.py` after the `compare_models` refactor still gives
  58 / 77 / 76 / 47 breaches.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Window | 500 days | 250 | 3 parameters need more data; it also keeps Phase 8's common period |
| Mean | Zero | Constant mean | Same as EWMA/RiskMetrics; the daily mean is tiny and noisy |
| Likelihood | Normal | Student-t | The tail comes from FHS instead; Student-t is a possible extension |
| Asset level | Portfolio return (one series) | Multivariate GARCH (DCC) | Constant exposure makes the portfolio one asset; DCC is far heavier |
| **Re-fit schedule** | **Every 21 days, held between** | Daily; 1,000-day window | Removes day-to-day parameter flips, is realistic, and is 2× faster. It does **not** cure α = 0 fits (see Bugs) |

## Results (run of 2026-11-24)

**Fitted parameters:**
| Sample | ω | α | β | α+β | Half-life | Long-run vol |
|---|---|---|---|---|---|---|
| Whole history (5,006 days) | 0.0089 | 0.067 | 0.920 | 0.987 | 53 days | 0.83%/day |
| Latest 500 days | 0.0190 | 0.073 | 0.889 | 0.962 | 18 days | 0.71%/day |
| EWMA (fixed) | 0 | 0.06 | 0.94 | 1.00 | 11 days | none |

**Next trading day**, ₹ lakh, VaR / ES 99%:
- historical 1.11 / 1.41
- parametric 1.09 / 1.24
- EWMA 1.06 / 1.21
- responsive 1.01 / 1.20
- **GARCH 0.97 / 1.12**
- **GARCH-FHS 1.07 / 1.40**

**Backtest.** Common period 18 Aug 2009 → 24 Nov 2026, **4,506 days**, 45.1 breaches
expected. There were 217 GARCH fits, none failed to converge.

| | Historical | Parametric | EWMA | Responsive | GARCH | GARCH-FHS |
|---|---|---|---|---|---|---|
| Breaches | 58 | 77 | 76 | **47** | 70 | 53 |
| Kupiec p | 0.064 pass | 1.4e-05 REJECT | 2.5e-05 REJECT | **0.77 pass** | 0.00055 REJECT | 0.25 pass |
| Zone today | green | amber | amber | green | amber | green |
| Red-zone days | 0% | 5.4% | 0% | 0% | 5.6% | 1.5% |
| Worst 250-day count | 9 | 12 | 8 | 9 | 13 | 10 |
| Breaches in 2020 | 8 | 11 | 8 | **6** | 13 | 7 |
| Average VaR | ₹1.17 L | ₹1.01 L | ₹0.97 L | ₹1.19 L | ₹0.97 L | ₹1.08 L |
| ES size ratio | 1.12 | 1.28 | 1.17 | **1.11** | 1.33 | 1.17 |

**Daily re-fit version (run of 2026-11-23, 4,505 days, 4,507 fits):**
- GARCH-normal: 69 breaches (p 0.00088, REJECT), 10 in 2020.
- GARCH-FHS: **48 breaches (p 0.66)**, 4 in 2020, worst 250-day count 6, never red.

Those better-looking FHS numbers include days where the parameter flip-flop happened
to help.

**COVID reaction** (VaR, ₹ lakh, monthly re-fit):
| | 9 Mar | 12 Mar | 16 Mar | 23 Mar | 30 Apr | Actual on 23 Mar |
|---|---|---|---|---|---|---|
| GARCH | 0.92 | 0.92 | 0.92 | **0.92** | 2.75 | −4.19 |
| GARCH-FHS | 0.98 | 1.16 | 1.62 | 1.95 | 3.90 | −4.19 |
| EWMA (for comparison) | 1.39 | 1.79 | 2.61 | 3.58 | 3.16 | −4.19 |

**Verdict:**
- **Responsive VaR (Phase 8) remains the best model:** 47 breaches, p 0.77, the
  fewest in 2020, never red.
- **GARCH-FHS passes Kupiec** with a 9% lower average VaR than responsive, but on
  this 500-day window its parameters are unreliable.
- **GARCH-normal fails** under either schedule (69–70 breaches): a bell-curve tail
  misses even with fitted volatility.
- **FHS beats normal on the same σ:** 53 vs 70 breaches, and an ES ratio of 1.17 vs
  1.33. The tail shape matters as much as the volatility.

## Bugs and fixes

1. **The cache was too small.** The first version cleared the cache after 8 entries,
   so every model and measure re-fitted (about 18,000 fits). Keeping all results
   (safety limit 10,000) gave 4,507 fits in about 3 minutes.

2. **Daily re-fit parameter flips: VaR −41% in one day, in the middle of the crash
   (11 Mar 2020).**

   | Window ends | ω | α | β | VaR next day |
   |---|---|---|---|---|
   | 6 Mar | 0.004 | **0.000** | 0.991 | ₹0.91 L |
   | 9 Mar (the −3.96% day) | 0.262 | **0.217** | 0.165 | ₹2.72 L |
   | 10 Mar | 0.013 | 0.040 | 0.935 | ₹1.60 L |

   One extreme last observation flipped the maximum-likelihood fit for a single day.
   This is a model artefact, not a market move.
   **Fix:** re-fit every 21 days and hold the parameters fixed in between.

3. **The monthly re-fit exposed a deeper problem: α = 0 fits.**
   - In **24 of 215** monthly fits (calm windows such as 2016–17, late 2019 and
     2023–24) the fit found α ≈ 0, meaning "volatility is constant".
   - The fit on 4 Mar 2020 (α 0.000, β 0.994) was held through the crash, so GARCH
     VaR sat at **₹0.92 L from 9 to 23 Mar** while losses were ₹2.4–4.2 L.
   - The whole-history fit (α 0.067) never shows this. 500 calm days don't contain
     enough shocks to identify α.
   - **Not fixed. Documented as a limitation.** Candidate fixes: an expanding or
     1,000-day window, a floor on α, or a Student-t likelihood.

## Interview questions (with model answers)

1. **What is GARCH(1,1), and how does it relate to EWMA?**
   σ²ₜ₊₁ = ω + α·r²ₜ + β·σ²ₜ. EWMA is the special case ω = 0, α = 1−λ, β = λ, so
   α+β = 1 and there is no long-run level. On my portfolio's full history:
   α 0.067, β 0.920, persistence 0.987, half-life 53 days, long-run vol 0.83%/day.

2. **What is Filtered Historical Simulation, and why did it beat GARCH-normal?**
   Divide past returns by their GARCH σ to get standardised surprises, then scale
   their empirical 1% quantile by tomorrow's σ. The volatility is the same; only the
   tail differs. The real 1% surprise is about 2.5σ, not 2.33σ, so FHS had 53
   breaches against 70 for the normal tail.

3. **How often should you re-estimate GARCH parameters?**
   Daily re-fitting is unstable: on 9 Mar 2020 one crash day flipped α from 0.00 to
   0.22 and back the next day, a −41% VaR swing. Periodic re-fitting with daily σ
   updates is standard. But holding a bad fit is worse: an α = 0 fit held through
   March 2020 froze VaR at ₹0.92 L. What matters most is enough data to identify α.

4. **Why would a GARCH fit give α = 0?**
   In a calm window there's no evidence of volatility clustering, so the likelihood
   is maximised with no reaction to shocks. 24 of 215 of my 500-day fits did this;
   the 5,000-day fit doesn't. Use a longer or expanding window, put a floor on α, or
   check parameter stability as part of model validation.

5. **Which of your six models would you put in production?**
   Responsive VaR (weighted HS): 47 breaches vs 45.1 expected, p 0.77, never red, the
   most accurate ES, and transparent. GARCH-FHS is a strong challenger with a lower
   average VaR (₹1.08 L vs ₹1.19 L), but only after its parameter estimation is
   stabilised.

## My check questions (2026-11-24)

1. **Q:** On 4 Mar 2020 the fit gave α = 0.000, β = 0.994. What happens to σ after a
   −5% day, and why was GARCH VaR flat in the crash?
   **My answer:** I don't know.
   **Feedback:**
   - σ² = 0.003 + **0** × 25 + 0.994 × 0.436 = 0.436, so σ stays at 0.66%. With
     α = 0 the r² term is multiplied by zero and the model can't see today's return.
   - α is the model's "eyes"; β is only its memory. Held for 21 days, the model was
     blind through the crash.

2. **Q:** Normal and FHS use the same σ. Why did FHS have 53 breaches and normal 70?
   **My answer:** FHS does not fit to the bell curve.
   **Feedback:** Correct. FHS reads the cutoff from its own surprises (about
   2.5–2.6σ) instead of the bell curve's 2.33σ. Same σ, bigger multiplier.

3. **Q:** Why does the whole history rarely give α = 0 when a 500-day calm window
   often does?
   **My answer:** A 5,000-day window has more shocks to learn from; a 500-day window
   doesn't.
   **Feedback:** Correct. It's too little signal in the training data: 2008, 2013,
   2016 and 2020 make α clearly visible in the long sample. A short calm sample makes
   the estimate unreliable, not just noisy.

## Next phase

**Stage 3: Monte Carlo VaR and the Christoffersen test.**
- Simulate thousands of correlated portfolio paths (Cholesky decomposition of the
  covariance matrix).
- Test whether breaches **cluster in time**, which Kupiec cannot see.
- Possible follow-up for GARCH: an expanding window or a floor on α.
