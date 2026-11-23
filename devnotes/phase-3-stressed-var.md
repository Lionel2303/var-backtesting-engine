# Phase 3: Stressed VaR (2008 crisis vs COVID 2020)

_Completed 2026-11-23. Every number below comes from running `python run_stressed.py`
on 2026-11-23 (data up to 2026-11-23)._

## Goal

Compute **Stressed VaR (SVaR)**: the 1-day 99% VaR of *today's* portfolio if the
**worst 250-day period in history** happened again. Find that period
automatically, and compare the 2008 crisis with COVID 2020.

**Why a Market Risk team cares:** after 2008, regulators (Basel 2.5) required banks
to hold market-risk capital based on **VaR + Stressed VaR**. Normal VaR shrinks in
calm years (the ghost effect from Phase 2), and so would capital, just before the
next crisis. SVaR keeps a crisis permanently in the calculation.

## Concepts

### Normal VaR vs Stressed VaR
| | Normal VaR | Stressed VaR |
|---|---|---|
| Which 250 days | The last 250 (slides forward daily) | A fixed crisis period (never slides) |
| In a calm year | Small (e.g. ₹0.78L on 14 Feb 2020) | Still large: the crisis never ages out |
| Question it answers | "How risky is today?" | "How bad if the worst year hit today's book?" |

### Choosing the stressed window
The Basel idea: use the 12-month period that gives the **highest VaR for the
current portfolio**. Phase 2 already computed every rolling VaR, so the stressed
window is just the 250 days behind the highest forecast.
Example: the highest historical forecast is for 24 Mar 2020 → the stressed window
is the 250 trading days before it, 10 Apr 2019 → 23 Mar 2020.

### Why the two models disagree on a short, sharp crisis
A simplified COVID window: 240 calm days of about ±₹30,000 and 10 crash days of
about −₹3.5L.
- **Historical:** the 3rd-worst day ≈ **₹3.4L**. It looks straight at the crash days.
- **Parametric:** σ = √[(240 × 30,000² + 10 × 3,50,000²) ÷ 250] ≈ ₹75,900
  → VaR = 2.326 × 75,900 ≈ **₹1.77L**. The bell curve *averages* one month of panic
  into a calm year.

2008 was a long crisis with months of high volatility, so σ itself was high and
the two models agree. **COVID = short, sharp shock; 2008 = long grind.**

### Constant exposure → SVaR is one fixed number
We always hold ₹10L in each asset, so replaying the same crisis window always
gives the same SVaR. A real desk's positions change daily, so its SVaR changes
daily even with the same window.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `stressed.py` → `find_stress_window(selector_var, returns, window, start, end)` | rolling VaR forecasts, all returns, 250, a period | peak forecast date, its VaR, the window's returns, start and end | `selector_var.loc[start:end].idxmax()` finds the peak forecast; `returns.iloc[i-250:i]` is exactly the slice that forecast was trained on (same as `rolling_var`) |
| `stressed.py` → `stressed_var(models, window_returns)` | list of models, the fixed window | {model name: SVaR in ₹} | One line, because every model shares `predict()` (Phase 2's interface) |
| `run_stressed.py` | — | prints windows, SVaR and comparisons; writes `outputs/stressed_var.csv` | Searches the 2008 period (forecasts Sep 2008 – Jun 2009), COVID (Mar – Dec 2020) and all dates, plus the window parametric would pick for itself |

**Library functions used for the first time:**
- `Series.loc[start:end]`: rows between two dates (inclusive; `None` means no limit).
- `Series.idxmax()`: the index (date) of the largest value.
- `Index.get_loc(date)`: the row number of a date.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| How to pick the window | Highest rolling **historical** VaR | Highest parametric VaR; worst 250-day cumulative P&L; a fixed regulator-style 2008 window | Historical VaR measures the loss tail directly. Parametric VaR picked a window whose peak came from the +₹6L election-rally **gain** (19 May 2009), which is a poor definition of "stress" |
| Search periods | 2008 (forecasts 1 Sep 2008 – 30 Jun 2009), COVID (1 Mar – 31 Dec 2020), all dates | Hand-picked calendar years | Lets the data choose the worst window inside each crisis, so it isn't guessed |
| Exposure | Constant ₹10L each (from Phase 1) | Real share holdings | Consistent with Phases 1–2; makes SVaR a single number (stated openly) |

## Results (run of 2026-11-23)

**Today's normal VaR** (250 days ending 2026-11-23): historical **₹1.11L**, parametric **₹1.09L**.

**Stressed windows:**

| Search | Window | Peak forecast for | Historical SVaR (× today's VaR) | Parametric SVaR (× today's VaR) |
|---|---|---|---|---|
| 2008 crisis | 24 Jan 2008 → 7 Jan 2009 | 8 Jan 2009 | ₹2.64L (2.39×) | ₹2.54L (2.34×) |
| COVID 2020 | 10 Apr 2019 → 23 Mar 2020 | 24 Mar 2020 | **₹3.41L (3.08×)** | ₹1.51L (1.39×) |
| Overall worst | same as COVID | 24 Mar 2020 | **₹3.41L (3.08×)** | ₹1.51L (1.39×) |
| Overall worst, picked by parametric | 4 Jun 2008 → 19 May 2009 | 20 May 2009 | ₹2.64L (2.39×) | ₹2.65L (2.45×) |

**Worst 3 actual days inside each window:**
- 2008 crisis: 24 Oct 2008 (−₹3.79L), 7 Jan 2009 (−₹2.79L), 11 Nov 2008 (−₹2.64L)
- COVID 2020: 23 Mar 2020 (−₹4.19L), 16 Mar 2020 (−₹3.71L), 12 Mar 2020 (−₹3.41L)

**Takeaways:**
1. For this portfolio the worst year is **COVID, not 2008**. Stressed VaR (historical)
   = **₹3.41L, 3.1× today's VaR**.
2. On the COVID window, parametric SVaR is less than half of historical (₹1.51L vs
   ₹3.41L): the normal model dilutes a short crash.
3. On 2008's longer crisis the models agree (₹2.64L vs ₹2.54L).

## Bugs and fixes

1. **"Today's VaR" moved between runs.** Phase 2 reported parametric ₹1.08L (data to
   18 Nov); Phase 3 reports ₹1.09L (data to 23 Nov), because `END_DATE = None`
   downloads up to today. Not a bug, but unlabelled numbers were confusing.
   **Fix:** the output now states the window's end date. Every devnote records its
   run date.
2. **Ugly number printing** (`np.float64(1.11)`). **Fix:** format the values as plain
   text.
3. **The parametric SVaR on the COVID window looked "too low".** Not a bug: it's the
   dilution effect explained in Concepts. Added the "picked by parametric" row so the
   effect of the selection method is visible.

## Interview questions (with model answers)

1. **What is stressed VaR and why was it introduced?**
   VaR computed on a fixed 12-month crisis window with today's positions. After 2008,
   regulators saw that normal VaR, based on recent calm data, made capital too small
   before a crisis. Basel 2.5 bases capital on VaR + SVaR.
2. **How did you choose the stress period?**
   As the 250-day window giving the highest historical VaR for the portfolio, searched
   automatically within the 2008 and COVID periods and overall. For this book it's
   10 Apr 2019 – 23 Mar 2020 (COVID), not 2008.
3. **Why do historical and parametric SVaR differ so much on COVID but not 2008?**
   COVID was about 10 extreme days in an otherwise calm year. The normal model's σ
   averages them away (₹1.51L), while historical simulation reads them directly
   (₹3.41L). 2008 was months of high volatility, so both agree (~₹2.6L).
4. **Why not let parametric VaR pick the stress window?**
   It picked the window containing the +₹6L election-rally gain, because σ counts
   gains as risk. A stress window should reflect losses.
5. **Your SVaR never changes. Is that right?**
   Yes, for constant exposure: same positions × same crisis window = same number. At
   a bank, positions change daily, so SVaR changes daily even with a fixed window.

## My check questions (2026-11-23)

1. **Q:** In one sentence, why do regulators want stressed VaR when we already have
   normal VaR?
   **My answer:** To gauge how well the system of banks / the world economy can hold
   up against a 1-in-100-odd event.
   **Feedback:** Partly right. "1 in 100" describes every 99% VaR, and SVaR is about
   the bank's own portfolio. The key point: normal VaR forgets crises after 250 days,
   so in calm years it and the capital based on it become too small; SVaR fixes the
   window on the worst year so capital always covers a crisis.
2. **Q:** On the COVID window, historical SVaR is ₹3.41L but parametric only ₹1.51L.
   Why?
   **My answer:** Of the 250 days, 240 were calm, which averages the shock.
   **Feedback:** Correct.
3. **Q:** Why would SVaR change every day at a real bank?
   **My answer:** Positions change daily at a real bank.
   **Feedback:** Correct.

## Next phase

**Phase 4: Backtesting.** Compare each day's VaR forecast with that day's actual
P&L, count the breaches (loss > VaR), and test the models:
- **Kupiec POF test:** is the breach rate consistent with 1%?
- **Basel traffic light:** breaches in 250 days: green 0–4, amber 5–9, red 10+.

Phase 2 already showed both models breached on 24 Oct 2008 and 23 Mar 2020; Phase 4
counts all breaches and decides which model passes.
