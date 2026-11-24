# Phase 10 (Stage 3): Christoffersen tests for breach independence

_Completed 2026-11-24. Every number below comes from running `python run_christoffersen.py`
on 2026-11-24 (data up to 2026-11-24)._

## Goal

Kupiec (Phase 4) checks only the **number** of breaches. A model with the right count
can still be dangerous if its breaches arrive **back to back**: it didn't learn from
the first loss. FRAM PPT slide 34 calls this "bunching": "exceptions are not evenly
spread throughout the back testing period".

This phase adds Christoffersen's tests and runs them on all 6 models:
- the **independence** test
- the joint **conditional-coverage** test (right count AND independent)

**Why a Market Risk team cares:** clustered breaches mean losses pile up exactly when
capital is under strain. Model validation reports both coverage and independence.

## Concepts

### Example first
Two banks each have 5 breaches in 250 days, so Kupiec scores them the same.

| | A: spread out (days 30, 80, ...) | B: bunched (5 days in a row) |
|---|---|---|
| n00 / n01 / n10 / **n11** | 239 / 5 / 5 / **0** | 243 / 1 / 1 / **4** |
| π01 = breach chance after a calm day | 2.05% | 0.41% |
| **π11 = breach chance after a breach** | **0%** | **80%** |
| LR_ind, p | 0.20, p 0.65: **pass** | 30.98, p 2.6 × 10⁻⁸: **REJECT** |

### The test
- Count the day → next-day transitions: n00, n01, n10, n11.
- **H0 (independent):** one breach probability π for every day.
- **H1 (depends on yesterday):** π01 after a calm day, π11 after a breach.
- LR_ind = −2 ln(L_H0 / L_H1), checked against χ²(1).
- **Conditional coverage:** LR_cc = LR_Kupiec + LR_ind, checked against χ²(2).

**Important:** the test compares **π11 with π01**, not with 1%. A model with many
scattered breaches (a high π01) can pass.

**Limitation:** the test only looks one day back. Breaches 3 days apart look
independent. The fixes are a **duration test** (Christoffersen–Pelletier: days
between breaches, about 100 on average if the model is correct) or a rolling count
like the Basel traffic light.

**ML link:** this checks whether a model's errors are **autocorrelated**. Errors that
predict each other mean the model has more to learn. The two-state table is a
first-order **Markov chain**.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `backtest.py` → `christoffersen(breaches, p)` | breach flags, 1% | n00..n11, π01, π11, LR_ind, p_ind, LR_cc, p_cc, verdicts | `b[:-1]` / `b[1:]` pair each day with the next; `xlogy` handles zero counts; LR_cc reuses `kupiec_pof` |
| `backtest.py` → `longest_run(breaches)` | breach flags | longest streak | Simple loop: extend the streak or reset it |
| `run_garch.py` → `model_setup()`, `six_model_forecasts(returns)` | returns | VaR and ES tables on the common period | Moved out of `main()` so Phase 10 reuses the same 6 models without copying them |
| `run_christoffersen.py` | — | hand-check, test table, back-to-back dates; `outputs/christoffersen.csv` | `b & b.shift(1)` = "breach today AND yesterday" |

**New Python:**
- `b[:-1]` / `b[1:]`: everything except the last element / except the first element
- `Series.shift(1, fill_value=False)`: yesterday's value lined up with today
- a function imported from another script (`from run_garch import six_model_forecasts`)

**Hand-check (passed):** the toy example reproduces LR 0.20 (pass) and LR 30.98,
p 2.6 × 10⁻⁸ (REJECT).

**Regression:** `run_garch.py` after the refactor gives the same backtest table as
Phase 9.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Test | First-order Markov independence + conditional coverage | Duration test; multi-lag tests | The standard regulatory pair; uses existing breach flags; duration test noted as next |
| Period | Phase 8–9 common period (4,506 days) | Each model's own period | Same dates for every model (Phase 8 lesson: verdicts depend on the period) |
| Reuse | Import `six_model_forecasts` from `run_garch.py` | Read `outputs/garch_var.csv` | Doesn't depend on a generated file being present and up to date |
| Phase order | Christoffersen before Monte Carlo | Monte Carlo first | Quick, and it scores all 6 existing models; Monte Carlo then gets both tests |

## Results (run of 2026-11-24)

**Common period:** 18 Aug 2009 → 24 Nov 2026, **4,506 days**, 45.1 breaches expected.

| | Historical | Parametric | EWMA | Responsive | GARCH | GARCH-FHS |
|---|---|---|---|---|---|---|
| Breaches | 58 | 77 | 76 | 47 | 70 | 53 |
| Back-to-back pairs (n11) | 4 | 4 | 3 | 3 | 4 | 3 |
| π01 (after calm) | 1.21% | 1.65% | 1.65% | 0.99% | 1.49% | 1.12% |
| π11 (after breach) | 6.90% | 5.19% | **3.95%** | 6.38% | 5.71% | 5.66% |
| Longest streak | 2 | 2 | 2 | 2 | 2 | 2 |
| Kupiec p | 0.064 | 1.4e-05 | 2.5e-05 | 0.77 | 0.00055 | 0.25 |
| LR_ind (p) | 7.30 (0.0069) | 3.72 (0.054) | 1.75 (0.19) | 6.13 (0.013) | 4.84 (0.028) | 4.89 (0.027) |
| Independence | REJECT | pass | **pass** | REJECT | REJECT | REJECT |
| LR_cc (p) | 10.74 (0.0047) | 22.58 (1.2e-05) | 19.54 (5.7e-05) | 6.21 (0.045) | 16.77 (0.00023) | 6.23 (0.044) |
| Conditional coverage | REJECT | REJECT | REJECT | REJECT | REJECT | REJECT |

**Back-to-back breach days** (the second day of each pair; the driver is the asset
with the biggest loss):

| Day | Models | Driver (₹ L) | Event (verified in news reports) |
|---|---|---|---|
| 10 Apr 2017 | EWMA, FHS | Infosys −0.29 | — |
| 21 Aug 2017 | all except EWMA | Infosys −0.54 (−0.96 on 18 Aug) | CEO Vishal Sikka resigned 18 Aug; Infosys −9.6% on the BSE |
| 4 Oct 2018 | all 6 | Reliance −0.69 | Sensex −806 points: the rupee hit a record low and Brent a 4-year high; Reliance ~−7% |
| 9 Mar 2020 | historical, parametric, GARCH | Reliance −1.23 | COVID crash |
| 7 Apr 2025 | all except FHS | Infosys −0.38 | US tariff sell-off; Nifty −3.24%, Nifty IT ~−7% |

**Verdict:**
- **No model passes conditional coverage.** Responsive (p 0.045) and GARCH-FHS
  (0.044) fail only just: their count is right, but they have too many pairs.
- **EWMA bunches least** (π11 3.95%, 2.4× π01), the benefit of its fast reaction. It
  was the one weighted model to avoid the 9 Mar 2020 pair.
- **Parametric passes independence only borderline (p 0.054).** Its breaches are
  frequent and scattered, so π01 is already high.
- **My prediction was partly wrong.** I expected the slow models to bunch most, but
  Responsive VaR failed independence and parametric passed.
- **Small sample:** every verdict rests on 3–4 pairs, mostly the **same market events
  for all models**. These were two-day shocks, so this is partly the market, not one
  model's flaw.

## Bugs and fixes

None. The hand-check matched the toy example before the real run.

## Interview questions (with model answers)

1. **What does the Christoffersen test add to Kupiec?**
   Kupiec checks the number of breaches; Christoffersen checks whether they're
   independent: is a breach more likely the day after a breach? On my data
   Responsive VaR passes Kupiec (47 vs 45.1, p 0.77) but fails independence
   (p 0.013). π11 = 6.4% vs π01 = 1.0%.

2. **How is the independence test built?**
   Count the transitions n00, n01, n10, n11 and estimate π01 and π11. Compare the
   likelihood of one breach rate against two rates, LR ~ χ²(1). Conditional coverage
   adds the Kupiec LR, ~ χ²(2).

3. **A model fails Kupiec but passes independence. Is that possible?**
   Yes, they test different things. My parametric model has 77 breaches (Kupiec
   p 1.4e-05), but they're scattered, so π11/π01 is only 3.1× and independence
   passes (p 0.054). It still fails the joint test.

4. **What can the test miss?**
   It only looks one day back. My historical model had 8 breaches in 2020 but one
   consecutive pair. A duration test, using the days between breaches, or a rolling
   250-day count catches clustering over weeks.

5. **Which model bunched least, and why?**
   EWMA (λ 0.94): π11 3.95%. Yesterday's loss carries a 6% weight vs 0.4% under equal
   weights, so VaR jumps immediately after a big loss. The trade-off is that it
   forgets quickly and has too many breaches overall (76).

## My check questions (2026-11-24)

1. **Q:** Parametric fails Kupiec but passes independence; historical passes Kupiec
   but fails independence. How?
   **My answer:** Historical's autocorrelation puts far too much weight on yesterday,
   while parametric fails to detect shocks because it assigns the same standard
   deviation to each day.
   **Feedback:** Not quite. Historical gives every day the same weight (0.4%). The
   tests measure different things: Kupiec = **how many** (77 too many, 58 close to
   45); independence = **when** (parametric's breaches are scattered, π11/π01 3.1×;
   historical's pair up, 5.7×).

2. **Q:** Historical had 8 breaches in 2020 but one back-to-back pair. Why is that
   missed, and how would you catch it?
   **My answer:** If the breaches aren't consecutive it treats them as independent
   events; reduce the window size or use a sliding window.
   **Feedback:** The first part is right: it's lag-1 only. Shrinking the VaR window
   changes the model, not the test. A sliding count of breaches is valid; that's the
   Basel traffic light. The formal fix is a duration test (days between breaches).

3. **Q:** Why is EWMA least likely to be breached the day after a breach?
   **My answer:** EWMA gives the most recent day more weight, so it reacts faster.
   **Feedback:** Correct. Yesterday's loss counts 15× more (6% vs 0.4%), so VaR rises
   the next morning.

## Next phase

**Phase 11: Monte Carlo VaR.** Simulate thousands of correlated one-day portfolio
outcomes from the covariance matrix (Cholesky decomposition), read the 1% loss, and
backtest it with Kupiec and Christoffersen alongside the 6 models.

Possible follow-up: a duration-based independence test.
