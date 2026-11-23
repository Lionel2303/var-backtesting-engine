# Phase 8: Exponentially weighted VaR (EWMA and "Responsive VaR")

_Completed 2026-11-23. Every number below comes from running `python run_responsive.py`
on 2026-11-23 (data up to 2026-11-23)._

## Goal

Phases 2 and 4 found two problems with equal-weight models:
- They **react slowly** when volatility jumps (8 and 11 breaches in 2020).
- They **forget a crisis all at once** (the ghost-effect cliff: historical VaR −28% in
  one day in March 2021).

This phase gives recent days more weight and tests whether that fixes both. Two new
models behind the same interface:
- **EWMA (RiskMetrics):** parametric, with exponentially weighted volatility,
  λ = 0.94.
- **Responsive VaR:** exponentially weighted historical simulation, λ = 0.994 on 500
  days. This is the method in the FRAM reading material (Credit Suisse notes,
  section 4; PPT slides 23–30).

**Why a Market Risk team cares:** banks use weighted historical simulation in
practice, as the reading material shows. A model that's too slow under-reserves in a
crisis. One that's too fast under-reserves just before the next one.

## Concepts

### Exponential weights
The newest day gets λ⁰ = 1, the day before λ¹, then λ², …; all are normalised to sum
to 1. λ = 1 gives equal weights.

| λ = 0.94, 250 days | Weight |
|---|---|
| Yesterday | 6.0% (equal weighting: 0.4%) |
| 10 days ago | 3.2% |
| 50 days ago | 0.27% |
| 100 days ago | 0.012% |

**Half-life** = ln 0.5 / ln λ: **11 days** at 0.94, **115 days** at 0.994.
With λ = 0.994 on 500 days, yesterday's weight is 0.63% (equal weighting: 0.2%).

### Weighted historical simulation (the reading material's 4 steps)
1. Weight each day.
2. Sort the P&Ls worst-first, **each keeping its own weight**.
3. Add up the weights.
4. VaR = the loss where the running total reaches 1%; ES = the weighted average of
   those tail days.

Toy example (5 days, 20% tail): P&L −5, −3, −1, +2, +4 with weights 0.10, 0.15,
0.30, 0.25, 0.20. The running total 0.10, 0.25 passes 0.20 at the 2nd day, so
VaR = 3 and ES = (0.10×5 + 0.15×3)/0.25 = 3.8.

### EWMA volatility (RiskMetrics)
Covariance = Σ weight × r·rᵀ, with the mean taken as 0 (over one day it's tiny and
noisy). VaR = 2.326σ, ES = 2.665σ, the same as parametric but with weighted σ.

### Weighted data age ("WAOP") and the 130-day rule
Weighted average age = Σ (days back × weight). The reading material: with weighting,
this must be at least ~130 days (6 months). On a 2-year window that forces λ above
0.9932.

| Model | Weighted data age |
|---|---|
| Equal weights, 250 days | 124 days |
| Responsive (λ 0.994, 500 days) | **140 days** (passes) |
| EWMA (λ 0.94) | **16 days** (fails the rule as it stands) |

### The trade-off
Fast reaction = fast forgetting. After a crisis EWMA drops quickly, which is
accurate for today's market but leaves no memory of the crisis. That's why
regulators require **stressed VaR** alongside VaR.

**ML link:** like an exponential moving average of the loss, or momentum in gradient
descent. λ is a hyperparameter trading off responsiveness against stability (like a
learning rate).

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `models/base.py` → `exp_weights(n, λ)` | days, decay | n weights, oldest first, sum 1 | Shared by both new models; λ = 1 = equal weights |
| `models/base.py` → `weighted_age(n, λ)` | days, decay | weighted average age (days) | The reading material's WAOP; checks the 130-day rule |
| `models/weighted_historical.py` → `WeightedHistoricalVaR(holdings, conf, λ)` | — | VaR / ES | `_tail()` sorts with `np.argsort` keeping weights paired, `np.cumsum` adds them up, `np.searchsorted` finds where the total reaches 1% |
| `models/ewma.py` → `EWMAVaR(holdings, conf, λ)` | — | VaR / ES | `_sigma()`: `(r * w[:, None]).T @ r` = weighted covariance (zero mean) |
| `config.py` | — | `EWMA_LAMBDA = 0.94`, `RESPONSIVE_LAMBDA = 0.994`, `RESPONSIVE_WINDOW = 500` | All settings in one place |
| `run_responsive.py` | — | 4 tables; writes `outputs/responsive_var.csv` | All 4 models backtested on the **same dates** (`dropna`) |

**Python / numpy used for the first time:**
- `super().__init__(...)`: runs the parent class's setup, then the child adds λ.
- `np.argsort`: the positions that would sort an array.
- `np.cumsum`: a running total.
- `np.searchsorted(a, x)`: the first position where sorted `a` reaches `x`.
- `w[:, None]`: turns a 1-D array into a column, so each row is scaled by its own
  weight.
- `scipy.optimize.brentq` (hand-check only): finds where a function equals 0.

**Hand-checks before the full run (all passed):**
- `exp_weights(3, 0.5)` = 0.14, 0.29, 0.57.
- λ = 1 weighted model = plain historical simulation **exactly**: VaR ₹1,10,728, ES
  99% ₹1,40,884, ES 97.5% ₹1,16,585.
- The λ giving a 130-day weighted age on 500 days = **0.9933**; the reading material
  says 0.9932.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Responsive λ, window | 0.994, 500 days | Our 250-day window | As in the reading material; passes the 130-day rule (140 days) |
| EWMA λ | 0.94 | Fit λ to data | The RiskMetrics standard; fitting is GARCH's job (Phase 9) |
| EWMA mean | 0 | Weighted mean | The RiskMetrics convention; the daily mean is tiny and noisy |
| Comparison period | Common dates (from 18 Aug 2009) | Each model on its own period | Fair comparison; but it drops 2008–09, which changes historical's Kupiec verdict (see Results) |
| Tail cutoff | First day where the running weight ≥ 1% | Interpolate between days | Matches our `method="lower"` rule (λ = 1 reproduces plain HS exactly) |

## Results (run of 2026-11-23)

**Common period:** 18 Aug 2009 → 23 Nov 2026, **4,505 days**, expected breaches 45.1.

**Next trading day**, ₹ lakh:
| | VaR 99% | ES 99% |
|---|---|---|
| Historical | 1.11 | 1.41 |
| Parametric | 1.09 | 1.24 |
| EWMA | 1.10 | 1.26 |
| Responsive | 1.04 | 1.30 |

**Backtest:**
| | Historical | Parametric | EWMA | Responsive |
|---|---|---|---|---|
| Breaches | 58 (1.29%) | 77 (1.71%) | 76 (1.69%) | **47 (1.04%)** |
| Kupiec p | 0.063 pass | 1.4e-05 REJECT | 2.4e-05 REJECT | **0.77 pass** |
| Zone today | green | amber | amber | green |
| Red-zone days | 0% | 5.4% | 0% | 0% |
| Worst 250-day count | 9 | 12 | 8 | 9 |
| Breaches in 2020 | 8 | 11 | 8 | **6** |
| Average VaR | ₹1.17 L | ₹1.01 L | ₹0.97 L | ₹1.19 L |
| ES size ratio (loss / ES on breach days) | 1.12 | 1.28 | 1.17 | 1.11 |

**Reaction around COVID** (VaR forecast, ₹ lakh):
| | 14 Feb | 9 Mar | 12 Mar | 16 Mar | 23 Mar | 30 Apr | 30 Sep |
|---|---|---|---|---|---|---|---|
| Historical | 0.78 | 0.93 | 1.60 | 1.95 | 2.94 | 3.41 | 3.41 |
| Parametric | 0.78 | 0.88 | 0.95 | 1.10 | 1.36 | 1.82 | 1.90 |
| EWMA | 0.81 | **1.39** | 1.79 | **2.61** | **3.58** | 3.16 | **1.16** |
| Responsive | 0.86 | **1.43** | **1.95** | 2.37 | 3.41 | 3.71 | 2.94 |
| Actual P&L | −0.17 | −2.37 | −3.41 | −3.71 | −4.19 | +1.00 | +0.04 |

**Biggest one-day VaR drop:** historical −28% (1 Mar 2021, the March 2020 window
exit); parametric −18% (5 May 2010); **EWMA −3%** (30 Mar 2020); responsive −19%
(21 Oct 2020). Responsive's drop was not a window exit, since March 2020 was only 7
months old. Weighted HS is still a sort-and-pick, so VaR can step from one scenario
to the next.

**Verdict:**
- **Responsive VaR is the best model so far.** It's the only one with a breach count
  matching 1% (47 vs 45.1, p = 0.77), with the fewest 2020 breaches (6), never red,
  and the most accurate ES (11% short).
- **EWMA** reacts fastest and has no cliffs, but forgets fast (₹1.16 L by Sep 2020),
  has the lowest average VaR and is still a thin-tailed bell curve, so it has 76
  breaches. It also fails the 130-day data-age rule.
- **Historical's Kupiec verdict flipped** (Phase 4 p = 0.023 → here 0.063) only
  because this period excludes Sep 2008–Aug 2009 (64 → 58 breaches). Kupiec verdicts
  depend on the test period.

## Bugs and fixes

None. The λ = 1 equivalence test confirmed the weighted code before the full run,
and the Phase 5 report was rerun afterwards with identical results (64 / 82
breaches).

## Interview questions (with model answers)

1. **What is exponentially weighted historical simulation, and why use it?**
   Historical simulation where each past day's weight decays by λ per day, so recent
   days count more. It reacts faster to volatility changes and avoids the cliff when
   an old crisis leaves the window. On my portfolio, with λ = 0.994 on 2 years, it
   had 47 breaches vs 45.1 expected (Kupiec p = 0.77), against 58 for equal weights.
2. **How do you choose λ?**
   A trade-off between responsiveness and stability. Regulation sets a minimum: the
   weighted average data age must be at least ~6 months, which on a 2-year window
   means λ > 0.9932. RiskMetrics' 0.94 has a half-life of 11 days and an average age
   of 16 days: good for daily risk monitoring, too short for capital.
3. **EWMA reacted fastest in March 2020, so why did it backtest badly?**
   It forgets fast, so its VaR is low in calm periods (average ₹0.97 L) and the first
   shock out of calm breaches it. It's also still a normal distribution with thin
   tails. 76 breaches vs 45 expected.
4. **After a crisis, would you report the fast or the slow VaR?**
   Neither extreme. The slow one overstates (historical still ₹3.41 L six months
   later, then a cliff); the fast one forgets (EWMA ₹1.16 L). A weighted model is the
   middle ground (₹2.94 L), and stressed VaR keeps the crisis in the capital number.
5. **Why did your historical model pass Kupiec here but fail earlier?**
   A different test period: this one starts in Aug 2009, dropping 6 breaches from the
   2008 crash. The model sits near the 5% boundary, so the verdict depends on the
   sample. Always state the backtest period.

## My check questions (2026-11-23)

1. **Q:** 30 Sep 2020: historical VaR ₹3.41 L, EWMA ₹1.16 L. Which would you report,
   and what's the danger of each?
   **My answer:** EWMA forgot the major loss, while historical VaR overstated it.
   **Feedback:** The dangers are right, but pick one: a weighted middle ground
   (responsive ₹2.94 L), with stressed VaR covering the forgotten crisis.
2. **Q:** EWMA reacts fastest, so why 76 breaches?
   **My answer:** EWMA reacts fast but forgets fast too, so it can miss shock events
   where the loss was extraordinary.
   **Feedback:** Mostly right. Low VaR in calm periods means the first shock out of
   calm breaches (no model sees day 1 coming). Also a bell curve: thin tails, ES 17%
   short.
3. **Q:** Historical passes Kupiec here (0.063) but failed in Phase 4 (0.023). What
   changed?
   **My answer:** Weights were given to 250 days and the rest got 0 weight.
   **Feedback:** Not quite. The **test period** changed: it starts 18 Aug 2009
   (responsive needs 500 days), dropping 6 of the 2008–09 breaches (64 → 58). The
   verdict depends on the sample.

## Next phase

**Phase 9: GARCH(1,1).** Instead of fixing λ, *fit* the volatility dynamics to the
data (σ²ₜ = ω + α·r²ₜ₋₁ + β·σ²ₜ₋₁). EWMA is the special case ω = 0, α = 1 − λ,
β = λ. Then a final 5-model backtest.
