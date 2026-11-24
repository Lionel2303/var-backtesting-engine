# Phase 11 (Stage 3): Monte Carlo VaR (normal and Student-t draws)

_Completed 2026-11-24. Every number below comes from running `python run_monte_carlo.py`
on 2026-11-24 (data up to 2026-11-24)._

## Goal

Build a simulation-based VaR. It does three things:
1. Simulate 10,000 correlated one-day outcomes for the 6 assets.
2. Value each one in rupees.
3. Read off the 1% loss.

The phase tests two questions:
- Does simulation by itself beat the parametric formula?
- Does changing the **distribution** of the draws (bell curve vs fat-tailed t) matter?

**Why a Market Risk team cares:** Monte Carlo is the standard engine for portfolios
with options and other non-linear products (Stage 4). Its sampling noise is a
model-validation topic of its own.

## Concepts

### Cholesky: turning independent draws into correlated returns
Σ = L × Lᵀ (L is lower-triangular, a "square root" of the covariance matrix).

Example: vols 1% and 2%, correlation 0.5, so Σ = [[1, 1], [1, 4]] (%²) and
L = [[1, 0], [1, 1.732]]. Draws z = (−2.0, +0.5) give:
- asset 1 = 1 × (−2.0) = **−2.0%**
- asset 2 = 1 × (−2.0) + 1.732 × 0.5 = **−1.13%**

The second asset inherits part of the first one's bad draw; that is the
correlation.

### Steps
1. Estimate μ and Σ from the last 250 days.
2. Draw Z (10,000 × 6, independent N(0, 1)).
3. Simulated returns = μ + Z Lᵀ.
4. Simulated P&L = returns × holdings.
5. VaR = the 100th-worst of 10,000; ES = the average of those 100.

### Normal vs Student-t draws
- **Normal draws** use the same assumptions as parametric VaR, so they give the same
  answer plus noise.
- **t draws (ν = 5)**: divide the normal draws by √(W/(ν−2)), with W ~ χ²(ν).
  - The variance is unchanged and the tails are fatter.
  - A small W makes **all assets jump together** on that day.
  - The 1% point is t.ppf(0.99, 5) × √(3/5) = **2.606σ vs 2.326σ** (+12%).

### Sampling noise falls with √N
10× the draws gives about 3× less noise, and 100× the draws gives 10× less.

**ML link:** this is the standard error σ/√n, and sampling from a fitted generative
model. The seed plays the role of `random_state`.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `models/monte_carlo.py` → `MonteCarloVaR(holdings, conf, n_sims, dist, df, seed)` | `dist="normal"` or `"t"` | VaR / ES | Same `VaRModel` interface, so `rolling_var` and `compare_models` work unchanged |
| `.simulate(window)` | 250-day window | 10,000 simulated rupee P&Ls | `np.linalg.cholesky`, `rng.standard_normal`, `rng.chisquare`; `z @ L.T` correlates the draws |
| `predict` / `predict_es` | window | VaR / ES | `np.quantile(..., method="lower")`, as historical simulation does |
| `config.py` | — | `MC_SIMS = 10_000`, `MC_SEED = 42`, `MC_T_DF = 5` | All settings in one place |
| `run_monte_carlo.py` | — | hand-checks, noise table, next-day, backtest (+ Christoffersen); `outputs/monte_carlo_var.csv` | Peers are the other 250-day models, so it uses the full Phase 4 period |

**New Python / numpy:**
- `np.random.default_rng(seed)`: a reproducible random generator
- `rng.standard_normal((n, k))` and `rng.chisquare(df, size)`
- `np.linalg.cholesky`
- `scipy.stats.t.ppf`
- `summary.loc[row, col] = ...`: adding rows to a table

**Fixed seed:** every call uses the same random numbers. Results are reproducible,
and VaR and ES come from the same simulated days.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Draws | 10,000 | 1,000 / 100,000 | A 2.4% spread (~₹2,600) is small next to model error; 100,000 takes 10× the time for 0.9% |
| Fat-tail distribution | Multivariate t, ν = 5 | Fit ν per window; bootstrap residuals | Simple and standard; ν = 5 was **set before the run, not fitted**; sensitivity is untested |
| Inputs | Equal-weight 250-day μ and Σ | EWMA or GARCH Σ | Isolates the effect of the distribution; a weighted Σ is a natural next step |
| Seed | Fixed (42), the same every day | A new seed each day | Reproducible; VaR and ES consistent |
| Backtest period | Full (4,756 days) | Common Phase 8 period | All peers use 250 days, so it's comparable with Phase 4 |

## Results (run of 2026-11-24)

**Hand-checks (all passed):**
- Cholesky: max |L Lᵀ − Σ| = 5.4 × 10⁻²⁰.
- 1M normal draws: VaR ₹1,08,288 vs the parametric formula ₹1,08,639 (0.3% apart).
- 1M t(5) draws: ₹1,21,493 vs the formula 2.606σ − μ = ₹1,21,430.
- σ of the simulated P&L: normal ₹45,650, t ₹45,634, formula ₹45,662.

**Sampling noise** (MC-normal VaR, latest window, 5 seeds):
| Draws | Lowest | Highest | Spread |
|---|---|---|---|
| 1,000 | ₹1.05 L | ₹1.13 L | 7.0% |
| 10,000 | ₹1.06 L | ₹1.09 L | 2.4% |
| 100,000 | ₹1.08 L | ₹1.09 L | 0.9% |

**Next trading day**, ₹ lakh, VaR / ES 99%:
- historical 1.11 / 1.41
- parametric 1.09 / 1.24
- MC-normal 1.09 / 1.22
- **MC-t 1.20 / 1.69**

**Backtest** (2 Sep 2008 → 24 Nov 2026, **4,756 days**, 47.6 expected):
| | Historical | Parametric | MC-normal | MC-t |
|---|---|---|---|---|
| Breaches | 64 (1.35%) | 82 (1.72%) | 82 (1.72%) | **45 (0.95%)** |
| Kupiec p | 0.023 REJECT | 5.3e-06 REJECT | 5.3e-06 REJECT | **0.71 pass** |
| Zone today | green | amber | amber | green |
| Red-zone days | 0% | 5.1% | 5.1% | 0% |
| Worst 250-day count | 9 | 12 | 12 | 8 |
| Breaches in 2020 | 8 | 11 | 11 | 7 |
| Average VaR | ₹1.24 L | ₹1.09 L | ₹1.09 L | ₹1.22 L |
| ES size ratio | 1.11 | 1.24 | 1.26 | 1.11 |
| Independence p | 0.0017 | 0.016 | 0.016 | 0.0088 |
| Conditional coverage p | 0.00054 | 1.8e-06 | 1.8e-06 | 0.03 |

- **Ratios:** MC-normal / parametric VaR every day: average 1.004, range
  0.987–1.021. MC-t / MC-normal: average 1.122.
- **Period effect:** the independence p-values differ from Phase 10 (e.g.
  historical 0.0017 vs 0.0069) because this is the full period, including 2008–09,
  not the common period.

**Verdict:**
- **Simulating a bell curve adds nothing:** 82 breaches, the same as parametric.
- **The fat tail alone fixes the count.** MC-t uses the same σ and window and goes
  from 82 to **45 breaches (p 0.71)**. It's the first 250-day model to pass Kupiec on
  the full period, with a lower average VaR than historical (₹1.22 L vs ₹1.24 L) and
  ES of the right size (1.11).
- **It still bunches** (independence p 0.0088). Tail shape and reaction speed are
  separate fixes.

## Bugs and fixes

None in the model. A setup slip: an `Edit` on `models/__init__.py` matched twice
(the import line also appears in the docstring) and was redone with more context.

## Interview questions (with model answers)

1. **How does Monte Carlo VaR generate correlated returns?**
   Cholesky-decompose the covariance matrix, Σ = LLᵀ, draw independent standard
   normals Z, and set returns = μ + ZLᵀ. Value each simulated day with today's
   holdings and take the 1% quantile.

2. **If MC with normal draws equals parametric VaR, why use it?**
   Flexibility. Swapping the distribution to Student-t(5) took my breaches from 82 to
   45 (Kupiec p 0.71) with no new formula. It also handles non-linear products
   (options are re-priced on each simulated day), many risk factors and multi-day
   paths.

3. **How many simulations do you need?**
   Noise falls with √N. On my portfolio the VaR spread across 5 seeds was 7.0% at
   1,000 draws, 2.4% at 10,000 and 0.9% at 100,000. 10,000 (about ₹2,600 of noise on
   ₹1.09 L) is small against model error. A fixed seed keeps results reproducible.

4. **Why does a t-distribution raise VaR when the variance is the same?**
   It puts more probability in the tails and less in the shoulders. At ν = 5 the 1%
   point is 2.61σ vs 2.33σ, 12% higher. That's close to the ~2.55σ seen in real
   standardised returns (GARCH-FHS, Phase 9).

5. **MC-t passes Kupiec. Is it a good model?**
   For the count, yes: 45 vs 47.6 expected. But it fails independence
   (p 0.0088) and the joint test (p 0.03), because equal 250-day weights react
   slowly. Combining a t tail with an EWMA or GARCH Σ is the next improvement. ν was
   chosen, not fitted, so it needs a sensitivity check.

## My check questions (2026-11-24)

1. **Q:** MC-normal had the same 82 breaches as parametric. Why build a Monte Carlo
   engine?
   **My answer:** It would still have fewer breaches with the added noise, since it
   would have a higher VaR.
   **Feedback:** Not quite. Noise moves VaR both ways (ratio 0.987–1.021, average
   1.004), so the count was identical. The reason is flexibility: swap the
   distribution (t: 82 → 45), re-price options on each simulated day (Stage 4), and
   handle many factors and multi-day paths.

2. **Q:** Where do MC-t's 37 fewer breaches come from, and why didn't it fix the
   bunching?
   **My answer:** A higher VaR due to the added noise, but it doesn't account for when
   the shocks occurred.
   **Feedback:** The second half is right. The higher VaR comes from the **fatter
   tail** (2.61σ vs 2.33σ), not from noise, which averages out. Bunching is about
   reaction speed, a separate fix.

3. **Q:** How many draws cut a 2.4% spread to 0.24%, and why might a bank not bother?
   **My answer:** I don't know.
   **Feedback:** Noise falls with √N, so 10× less noise needs 100× the draws:
   1,000,000. That's 100× the compute for about ₹2,600 of noise, against model error
   worth dozens of breaches.

## Addendum (2026-11-24): how much does ν = 5 matter?

**Why ν = 5:** an assumption, not a fit.
- Studies of daily stock returns usually find ν ≈ 3–6.
- ν must be above 4 for kurtosis to be finite.
- It's a common default.

`run_monte_carlo.py` now prints a sensitivity table via `nu_sensitivity()`. For each
ν it computes VaR = k(ν)·σ − μ every day. That is MC-t without the noise; the
hand-check showed they agree within 0.05%.

| ν | k (× σ) | Breaches | Kupiec p | Average VaR |
|---|---|---|---|---|
| 3 | 2.622 | 44 | 0.60 | ₹1.23 L |
| 4 | 2.649 | 43 | 0.50 | ₹1.24 L |
| **5** | 2.606 | 45 | 0.71 | ₹1.22 L |
| 6 | 2.566 | 50 | 0.72 | ₹1.20 L |
| 8 | 2.508 | 63 | 0.032 | ₹1.17 L |
| 10 | 2.472 | 66 | 0.011 | ₹1.16 L |
| 30 | 2.374 | 77 | 8.2e-05 | ₹1.11 L |

- **The result holds for ν = 3–6 and fails from ν = 8.** "A fat tail fixes the count"
  is robust, but only if the tail is quite fat.
- **k isn't monotonic:** ν = 4 gives the largest multiplier. With the variance fixed,
  a very fat tail moves probability into the far tail *and* the centre, so the 1%
  point can move inwards.
- **Choosing ν from this table would be tuning on the test set.** It's a robustness
  check only.

**Fitting ν instead.** These numbers come from a scratch analysis on 2026-11-24 and
are not in the committed code.
- **Fitted on each trailing 250-day window** (227 monthly fits):
  - median 6.6, 10th–90th percentile 3.5–14.8
  - calm years ~13–15 (2011: 15.1, 2017: 13.9); 2020: 1.9 (infinite variance;
    floored at 2.1)
  - backtest with the fitted ν, held monthly: **60 breaches** (Kupiec p 0.081),
    worse than fixed ν = 5
- **Why:** the same as GARCH's α = 0 in Phase 9. Calm short windows contain too few
  extreme days to identify the tail.
- **Whole history** (5,000 days): MLE ν = **3.1**, excess kurtosis 9.6. Using it for
  past forecasts would be look-ahead.

**Decision:** keep ν = 5 as a **documented assumption with this sensitivity table**,
which is standard validation practice. An expanding-window fit (all data up to that
day) is a possible follow-up.

**Check questions on the addendum:**
1. **Q:** Why not pick ν because it gave the breach count closest to 47.6?
   **My answer:** You'd be using the test data as training data.
   **Feedback:** Correct. That's tuning on the test set.
2. **Q:** Why is a fitted ν ≈ 13 in calm years dangerous?
   **My answer:** It shows very low volatility.
   **Feedback:** Close, but ν is tail **shape**, not volatility (σ). ν ≈ 13 means
   "extreme days are very rare" (thin tails), so VaR is too low when the shock comes.
   It's the same small-calm-sample problem as GARCH's α = 0.
3. **Q:** Is the Monte Carlo result reliable?
   **My answer:** Yes, but it depends on what metric it's tested on.
   **Feedback:** Good instinct. Reliable for the **count** (it passes Kupiec for any
   ν from 3 to 6, fails from 8); not for **timing** (independence p 0.0088).

## Next phase

Stage 3 is complete. Possible follow-ups:
- an expanding-window fit of ν
- MC with an EWMA or GARCH Σ (fat tail + fast reaction)
- a duration test

**Stage 4: derivatives and Greeks-based P&L explain.** Add an option position,
re-price it on each simulated day (full revaluation) and compare that with the
delta-gamma approximation.
