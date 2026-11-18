# Phase 2: VaR models (historical simulation and parametric)

_Completed 2026-11-18. Every number below comes from running `python run_var.py` on 2026-11-18._

## Goal

Every trading day, forecast **1-day 99% Value-at-Risk** for the ₹60 lakh portfolio
using only the previous 250 days. Do it with two standard models that share one
interface, so later models (GARCH, ML) can plug in without rework.

**What VaR means:** "We're 99% confident tomorrow's loss won't exceed ₹X." A worse
day should happen about 1 day in 100 (2–3 days a year).

**Why a Market Risk team cares:** VaR sets trading limits and regulatory capital.
Running more than one model shows how much the answer depends on the method.
Phase 4 then tests which one is right more often.

## Concepts

### Historical simulation
"If one of the last 250 days happened again tomorrow, what would we lose?"
1. Replay each past day's returns on today's holdings (₹10 lakh each).
   One past day: Reliance −2% → −₹20,000, Gold +1% → +₹10,000, … → total P&L.
2. Sort the 250 P&Ls from worst to best.
3. At 99%: 1% of 250 = 2.5 days → round to the worse side → **the 3rd-worst**.
   Worst four −₹3.0L, −₹2.5L, **−₹2.2L**, −₹1.9L → VaR = ₹2.2L.

There's no assumption about the shape of returns, so fat tails are captured
automatically.

### Parametric (variance-covariance)
Assume daily P&L follows a normal (bell-curve) distribution.
- **σ** (standard deviation of daily P&L in ₹) comes from the **covariance matrix**:
  each asset's volatility *and* how assets move together.
- **VaR = z × σ − average P&L**, with z = 2.326 for 99%.
  σ = ₹40,000 and average ≈ 0 → VaR = 2.326 × 40,000 = **₹93,040**.
- **Diversification:** two assets of ₹10L, daily vols 2% and 1%, correlation 0.3:
  σ² = 20,000² + 10,000² + 2 × 0.3 × 20,000 × 10,000 = 62 crore → **σ = ₹24,900**,
  less than 20,000 + 10,000 = ₹30,000, because they don't always move together.

### Why a *gain* can raise parametric VaR
σ squares each day's distance from the average, so +₹6L counts the same as −₹6L.
249 ordinary days of ±₹40k plus one +₹6L day: variance ≈ (249 × 160 crore +
6,00,000²) ÷ 250 ≈ 303 crore → σ ≈ ₹55,100 → VaR ≈ ₹1.28L (vs ₹93k without it).
Historical VaR is unchanged: the gain sits at the *best* end of the sorted list.
**ML link:** mean squared error also squares errors, so +10 and −10 count the
same and one outlier inflates the score.

### Rolling window = train/test split
The forecast for day *t* uses only days *t−250* to *t−1*, then gets compared with
what really happened on day *t* (Phase 4). The model never sees the day it's
forecasting, just like test data in ML.

### Ghost effect (VaR "cliffs")
Historical VaR uses the last 250 days. When an old crash day turns 251 days old,
it **leaves the window** and VaR can drop sharply on a quiet day.
Like a rolling average of your last 5 test marks: 80, 80, **20**, 80, 80 →
average 68; once the 20 is too old to count → 80, with no change in you.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `models/base.py` → `VaRModel(holdings, confidence)` | ₹ per asset, 0.99 | a model object | One shared shape: every model only implements `predict` |
| `VaRModel.scenario_pnl(returns_window)` | past returns (rows = days) | one ₹ P&L per past day | `returns_window @ weights` = Σ(return × ₹ held) per row |
| `models/base.py` → `rolling_var(model, returns, window)` | any model, all returns, 250 | VaR per forecast date | `returns.iloc[i-250:i]` stops *before* row i, so no peeking |
| `models/historical.py` → `HistoricalVaR.predict` | 250 days of returns | ₹ VaR (positive) | `np.quantile(pnl, 0.01, method="lower")` = 3rd-worst of 250 |
| `models/parametric.py` → `ParametricVaR.predict` | 250 days of returns | ₹ VaR (positive) | σ = √(w·Cov·w), μ = mean·w, `norm.ppf(0.99)` = 2.326 |
| `models/__init__.py` | — | — | lets other files write `from models import HistoricalVaR` |
| `data.py` → `load_data()` (new) | — | returns, P&L, glitch log, first dates | the Phase 1 pipeline in one reusable call |
| `run_var.py` | — | prints summary; writes `outputs/var_forecasts.csv` | runs every model through all of history |

**Library functions used for the first time:**
- `np.quantile(x, q, method="lower")`: the value at position q in the sorted data, rounding down.
- `DataFrame.cov()`: the covariance matrix.
- `@`: matrix multiplication.
- `scipy.stats.norm.ppf(p)`: the z that leaves probability p of the bell curve below it.
- `pd.concat([...], axis=1)`: puts Series side by side as columns.
- `Series.reindex(index)`: lines one series up with another's dates.
- `Series.diff()`: today minus yesterday.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Which day historical VaR picks | 3rd-worst of 250 (`method="lower"`) | interpolate between 2nd and 3rd (numpy's default would interpolate between 3rd and 4th) | Simple to explain; rounds toward the worse loss (cautious) |
| Mean in parametric VaR | Include it (VaR = zσ − μ) | Assume μ = 0 (common at banks) | Historical simulation implicitly includes the mean, so this keeps the two comparable. μ is small (~₹3k vs zσ ~₹1L) |
| Holdings | Built into the model at creation; `predict(returns_window)` takes only returns | Pass holdings to every `predict` call | Matches the planned interface `predict(returns_window) -> float` |
| Window | 250 rows | 500 days, exponential weighting | Basel standard (≈1 trading year). Note: rows include Indian holidays when forex traded, so 250 rows ≈ 11.5 months |
| Pipeline reuse | `load_data()` in `data.py` | Copy the pipeline into each script | One source of truth; Phase 1 output is unchanged |

## Results (run of 2026-11-18)

**Coverage:** forecasts for **4,752 days**, 2 Sep 2008 → 18 Nov 2026 (the first 250
days of data are only used for training). Runtime about 19 seconds.

**Hand-checks passed** (run before using real data):

| Check | Expected | Got |
|---|---|---|
| Historical VaR on P&Ls −1k … −250k | ₹2,48,000 (3rd-worst) | ₹2,48,000 |
| Parametric σ, 2 assets (vols 2% / 1%, corr 0.3) | ≈ ₹24,900 | ₹24,982 (random sample of 200,000 days) |
| Covariance route vs plain std of P&L | equal | ₹24,982 vs ₹24,966 |
| Forecast never uses its own day | 0 for the −50% day | 0 |

**VaR for the next trading day** (window ending 18 Nov 2026):

| Model | VaR | % of ₹60 lakh |
|---|---|---|
| Historical | ₹1.11 L | 1.85% |
| Parametric | ₹1.08 L | 1.80% |

**VaR over the whole period (₹ lakh):**

| Model | Average | Lowest (date) | Highest (date) |
|---|---|---|---|
| Historical | 1.24 | 0.58 (2017-07-03) | 3.41 (2020-03-24) |
| Parametric | 1.09 | 0.57 (2018-01-17) | 2.65 (2009-05-20) |

On average, **historical VaR = 1.13 × parametric VaR** (fat tails).
Parametric peaked two days after the **+₹6.0L election-rally gain** of 18 May 2009.

**Key days (₹ lakh; VaR forecast vs actual P&L):**

| Day | Historical | Parametric | Actual |
|---|---|---|---|
| 2008-10-24 (post-Lehman) | 2.21 | 2.30 | −3.79 (both breached) |
| 2020-02-14 (calm) | 0.78 | 0.78 | −0.17 |
| 2020-03-23 (COVID crash) | 2.94 | 1.36 | −4.19 (both breached) |

**Biggest one-day drops in VaR (ghost effect):**
- Historical: 24 Feb → 3 Mar 2021, **₹3.41L → ₹2.94L → ₹2.11L → ₹1.78L** as the
  March 2020 crash days aged out. Also 12 Oct 2009: ₹2.64L → ₹2.30L.
- Parametric: 5 May 2010, ₹1.41L → ₹1.15L (the 18 May 2009 *gain* aging out);
  8 Mar 2021, ₹1.60L → ₹1.46L.

## Bugs and fixes

1. **The "cliff" demo looked at the wrong day.** I first printed VaR on the day
   23 Mar 2020 left the window, expecting a big drop, but it barely moved
   (₹1.78L → ₹1.73L): the other March 2020 crash days were still in the window
   and took its place as the 3rd-worst. **Fix:** print the biggest one-day drops
   automatically. They're in late Feb–early Mar 2021, when the cluster of crash
   days aged out.
2. **Duplicate pipeline code.** `run_var.py` needed the same cleaned returns as
   `data.py`. **Fix:** moved the pipeline into `load_data()`; `data.py`'s own output
   is unchanged.

## Interview questions (with model answers)

1. **Walk me through historical-simulation VaR.**
   Take today's positions, replay each of the last 250 days' returns on them,
   sort the 250 P&Ls, and take the 1% point. With 250 days that's the 3rd-worst.
   It needs no distribution assumption, so fat tails are captured. But it's only
   as good as the last 250 days, and it suffers from cliffs.
2. **What does parametric VaR assume, and where does it fail?**
   That portfolio P&L is normal, so VaR = 2.326σ − μ, with σ from the covariance
   matrix. It understates fat-tailed risk (historical VaR averaged 1.13× higher
   here), and it treats big gains as risk: our parametric VaR peaked after the
   +₹6L election-rally day.
3. **What's the ghost effect?**
   An extreme day dropping out of the window makes historical VaR jump even
   though nothing happened. Ours fell from ₹3.41L to ₹1.78L in six trading days in
   early 2021 as March 2020 aged out. Remedies: exponential weighting (recent days
   count more; old ones fade) and stressed VaR.
4. **How do you avoid look-ahead bias?**
   Each forecast uses only data up to the previous day (`iloc[i-250:i]`), and it's
   then compared with the next day's actual P&L, like a train/test split.
5. **Why build models behind one interface?**
   The backtest and report only call `predict(returns_window)`. Adding GARCH or an
   ML model means adding one file, with no changes elsewhere.

## My check questions (2026-11-18)

1. **Q:** With 250 days at 99%, which replayed day does historical VaR use? Worst
   four are −₹3.0L, −₹2.5L, −₹2.2L, −₹1.9L. What's the VaR?
   **My answer:** ₹2.2L.
   **Feedback:** Correct. It's the 3rd-worst (2.5 days, rounded to the worse side).
2. **Q:** σ = ₹40,000, average ≈ 0. What's the 99% parametric VaR? Why did parametric
   VaR peak right after the 18 May 2009 gain?
   **My answer:** Didn't know at first.
   **Explanation given:** 2.326 × 40,000 = ₹93,040. σ squares distances in both
   directions, so a huge gain widens the spread and raises VaR (worked example in
   Concepts).
   **Re-check:** "σ = ₹50k, record ₹8L gain yesterday: does parametric VaR go up or
   down; does historical change?" **My answer:** historical unchanged, parametric
   increases. **Correct.**
3. **Q:** Why did historical VaR fall from ₹3.41L to ₹1.78L in early 2021 when
   markets were calm, and why is that a problem?
   **My answer:** Didn't know at first (also on the follow-up "VaR drops 40% on a
   quiet day, why?").
   **Explanation given:** the ghost effect, via the 5-test rolling-average analogy.
   It's a problem because VaR should measure today's risk; limits and capital
   would swing because of the calendar.
   **Re-check (fill in the blanks):** "uses the last ___ days; when an old crash day
   becomes ___ days old, it ___ the window." **My answer:** 250, 251 (third blank:
   "leaves"). **Correct.**

## Next phase

**Phase 3: Stressed VaR.** Regulators' answer to the ghost effect is to also
compute VaR on a **fixed crisis window** that never ages out. We'll find the worst
250-day period in the data automatically (expected: 2008), compare it with March
2020, and compute stressed VaR with both models through the same interface.
