# Phase 1: Data layer (prices → returns → portfolio P&L)

_Completed 2026-11-18. Every number below comes from running `python data.py` on 2026-11-18._

## Goal

Build the foundation every later phase stands on: a clean daily **profit and loss
(P&L) series in rupees** for a ₹60 lakh portfolio, plus the daily returns of each
asset.

**Why a Market Risk team cares:** VaR is a statement about the *left tail* of the
P&L distribution (the worst days). If the data is wrong, the VaR is wrong. One
bad price (like the ₹0.34 Gold ETF print below) can show up as a ₹9.9 crore
"gain" and make a model useless. Data checks are a big part of the real job.

## Concepts

### Simple return vs log return
- **Simple:** (today − yesterday) / yesterday. Price 1,000 → 1,020: 1,020/1,000 − 1 = **+2%**.
- **Log:** ln(today / yesterday) = ln(1.02) = **+1.98%**.
- We use **simple** returns for P&L because ₹ P&L = ₹ held × simple return exactly.
  Log returns are useful for adding returns over time (later phases).

### Constant exposure
We pretend to hold **₹10 lakh in every asset every day**, topping back up after
gains or losses.
- HDFC falls 3% → P&L = ₹10,00,000 × (−0.03) = **−₹30,000**.
- Portfolio P&L = the sum of the 6 assets' P&L that day.

Real desks hold *shares*, so their rupee exposure drifts. Constant exposure is
the standard simplification for a first VaR model.

### Forward-fill on holidays
On Diwali NSE is shut but forex trades, so Indian stocks have no price that day.
`ffill()` copies the last price forward → **return 0%, P&L ₹0** that day.
The reasoning: the exchange is closed, so there's no new price and no move. Any
news during the holiday shows up in full on the day the market reopens.

### Data glitches and the rolling median
A glitch is a price that jumps away and snaps straight back. A rolling median
over 5 days ignores one or two odd values:
- Glitch: 33.5, 33.6, **0.34**, 0.34, 33.65 → median 33.5 → 0.34 is 99% away → flag.
- Real crash: 100, 100, **79**, 79, 79 → median 79 → 0% away → keep.

### Fat tails (links to the ML idea of the normal distribution)
The daily P&L standard deviation is **₹53,127**. The worst day (−₹4,19,227) is
**7.9 standard deviations** below average. If P&L followed a normal (bell-curve)
distribution, a 7.9σ day would essentially never happen, yet it did, along with
several more beyond 5σ. Real returns have **fat tails**. This is why Phase 2
compares a normal-distribution model (parametric VaR) with one that uses actual
history (historical simulation).

## Code walkthrough

### `config.py`
- `HOLDINGS`: ticker → ₹ held (₹10 lakh each). `GOLD_INR` replaces `GOLDBEES.NS` (see Decisions).
- `DERIVED`: assets built from other tickers. `GOLD_INR = GC=F × USDINR=X`.
- `START_DATE = "2007-01-01"`, `END_DATE = None` (today), `CONFIDENCE = 0.99`, `WINDOW = 250`.

### `data.py`
| Function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `get_prices(tickers, start, end)` | list of Yahoo tickers | table of daily closes (rows = dates) | `auto_adjust=True` removes fake split moves; `threads=False` avoids the "database is locked" empty download; stops with a clear error if a ticker returns nothing |
| `clean_prices(prices)` | price table | (cleaned table, log of every removal) | Flags a price more than 11× the *local* (3-month) typical move away from its 5-day median; prints every correction so a human can check it |
| `tickers_to_download(holdings, derived)` | holdings + derived map | list of tickers | Replaces `GOLD_INR` with its ingredients `GC=F`, `USDINR=X` (no duplicates) |
| `add_derived(prices, derived)` | cleaned prices | prices + derived columns | Multiplies ingredients **after** cleaning, so a USD/INR glitch can't leak into gold |
| `get_returns(prices, kind)` | prices | daily returns | `ffill` for holidays, `dropna` keeps only days where all assets have prices, then simple or log returns |
| `get_portfolio_pnl(simple_returns, holdings)` | returns + holdings | daily ₹ P&L | returns × ₹ held, summed across assets |

Running `python data.py` prints each asset's first date, the glitch log, a P&L
summary, and the worst 5 days broken down by asset.

## Decisions and trade-offs

| Decision | Chosen | Rejected alternatives | Why |
|---|---|---|---|
| Holiday gaps | Forward-fill (0% return) | Drop the day for everyone | Dropping would lose real moves in the assets that *did* trade (e.g. USD/INR on Diwali) |
| Exposure | Constant ₹10 lakh | Fixed share counts | Simpler, standard for a first model; each asset's risk stays comparable |
| Gold | **Gold in ₹ = COMEX gold ($) × USD/INR** | (A) keep the Gold ETF and start in 2009; (C) splice proxy 2007–08 with the ETF from 2009 | Yahoo's ETF history starts 2 Jan 2009. With the ETF, `dropna` would cut the 2008 crisis that Phase 3 needs. A splice joins two different series and is hard to defend |
| Glitch threshold | 11× the local 3-month typical move | 10× the 19-year typical move (first attempt) | The first version deleted real crisis days (see Bugs) |
| Download | One ticker at a time | yfinance's default parallel download | Parallel download returned USD/INR empty ("database is locked") |

**Known limitation of rupee gold:** COMEX closes about 11 hours after Mumbai, so
the same date can show different moves. Measured 2009–2026 against the Gold ETF:
**daily correlation 0.341, weekly 0.752**. Long run it's the same asset: since
2009 rupee gold grew **×8.32** and the ETF **×8.06**. Example: on 23 Mar 2020 the
ETF fell, but rupee gold rose (+₹62,426 on our position), because New York saw
the Fed's unlimited-QE news after Mumbai had closed.

## Results (run of 2026-11-18)

**Coverage:** 18 Sep 2007 → 18 Nov 2026, **5,002 trading days**. The start date is
set by Nifty 50 (`^NSEI`), whose Yahoo history begins 17 Sep 2007; the first
return is the next day.

| First price on Yahoo | Date |
|---|---|
| GC=F, HDFCBANK, INFY, RELIANCE | 2007-01-02 |
| USDINR=X | 2007-01-01 |
| ^NSEI | 2007-09-17 |
| (GOLDBEES.NS, no longer used) | 2009-01-02 |

**Glitches removed (5, all USD/INR):**

| Date | Bad price | Local median | Distance | × local move |
|---|---|---|---|---|
| 2012-01-27 | 52.4930 | 50.0000 | 5.0% | 14.9 |
| 2012-01-31 | 52.4930 | 49.5000 | 6.0% | 18.1 |
| 2023-11-02 | 85.1940 | 83.2772 | 2.3% | 21.9 |
| 2023-12-29 | 82.3020 | 83.2026 | 1.1% | 13.8 |
| 2026-08-26 | 93.5461 | 95.4704 | 2.0% | 12.0 |

(While the Gold ETF was still in use, the same rule also caught its ₹0.34 prints
on 19–20 Dec 2019, at 306× and 322× the local move.)

**Daily portfolio P&L:**

| Statistic | Value |
|---|---|
| Mean | ₹3,007 |
| Median | ₹2,617 |
| Standard deviation | ₹53,127 (0.89% of ₹60 lakh) |
| Share of up days | 52.8% |
| Worst day | −₹4,19,227 (23 Mar 2020) |
| Best day | +₹6,00,524 (18 May 2009) |

**Worst 5 days (₹, by asset):**

| Date | Reliance | HDFC Bank | Infosys | Nifty | Gold ₹ | USD/INR | Total | Event |
|---|---|---|---|---|---|---|---|---|
| 2020-03-23 | −1,31,539 | −1,26,069 | −1,00,393 | −1,29,805 | +62,426 | +6,152 | **−4,19,227** | COVID crash, Nifty's worst day |
| 2008-10-24 | −1,62,731 | −94,345 | −28,950 | −1,22,029 | +25,655 | +3,428 | **−3,78,972** | Post-Lehman global sell-off |
| 2020-03-16 | −81,064 | −65,713 | −92,162 | −76,121 | −37,836 | −18,539 | **−3,71,435** | COVID panic after the Fed's emergency cut |
| 2020-03-12 | −78,497 | −83,049 | −79,883 | −83,019 | −24,499 | +7,479 | **−3,41,469** | Day after WHO declared a pandemic |
| 2020-03-18 | −39,187 | −1,00,708 | −37,211 | −55,565 | −45,944 | −15,203 | **−2,93,816** | COVID sell-off continues |

Gold cushioned the losses on 2 of the 5 worst days (USD/INR on 3), but **gold fell
alongside stocks on the other 3**. Hedges aren't guaranteed in a panic.

**Best day:** 18 May 2009 (general-election result). Reliance +21.4%, HDFC +16.3%,
Infosys +13.0%, Nifty +17.7%. Gold −4.7% and USD/INR −3.7% (the rupee strengthened).

## Bugs and fixes

1. **USD/INR came back empty → crash.** yfinance downloads tickers in parallel,
   and one hit `database is locked` (a shared cache file). The empty column made
   `dropna()` delete every row, so the script crashed with an `IndexError`.
   **Fix:** `threads=False`, plus a check that stops with a clear message if any
   ticker has no data.
2. **Two kinds of data glitch.** Gold ETF ₹0.34 on 19–20 Dec 2019 (a 1/100
   decimal error; Yahoo lists no split), which would have shown −₹9.9 lakh and
   then +₹9.9 crore. Bad USD/INR prints in 2012, 2023 and 2026.
   **Fix:** `clean_prices`.
3. **The first glitch rule deleted real crisis days.** Version 1 compared each
   price with 10× the asset's 19-year typical move (~10% for shares) and removed
   23 Mar 2020 (COVID), 24 Oct 2008 (Lehman) and 18 May 2009 (election), among 23
   "glitches". In a crisis, prices crash and bounce within days, which looks like
   a glitch against a calm-times yardstick.
   **Fix:** use the typical move of the surrounding ~3 months (61 trading days).
   The threshold was set at 11× after checking every flagged case: confirmed
   glitches sit at 12×–322×, real events at ≤10.2×. **Lesson:** print every
   automatic correction and read it.
4. **Gold ETF history starts in 2009.** This would silently cut the 2008 crisis.
   **Fix:** rupee gold (Decisions).

## Interview questions (with model answers)

1. **Why simple returns for P&L?**
   ₹ P&L = ₹ held × simple return, exactly. Log returns add up nicely over time,
   but they'd slightly misstate one-day rupee P&L, especially on big days.
2. **How do you handle market holidays across different markets?**
   Forward-fill the closed market's price, so its return that day is 0. Dropping
   the whole day would throw away real moves in the markets that were open.
3. **How did you clean the data, and how did you avoid deleting real crashes?**
   A price is flagged if it's far from the median of the 5 surrounding days,
   relative to the volatility of the surrounding 3 months. A crash that persists
   moves the median with it, and crisis-level volatility raises the threshold.
   Every correction is logged and was checked by hand. My first version used a
   whole-history threshold and wrongly deleted the COVID crash day.
4. **Why is gold priced as COMEX × USD/INR rather than an Indian gold ETF?**
   Yahoo's ETF history only starts in 2009, which would remove the 2008 crisis
   needed for stressed VaR. Rupee gold matches the ETF long-run (×8.32 vs ×8.06
   since 2009, weekly correlation 0.75). The cost is a timing mismatch (daily
   correlation 0.34) because COMEX closes 11 hours later.
5. **What does the P&L distribution tell you before building any VaR model?**
   It has fat tails: the worst day was a 7.9-standard-deviation move, which a
   normal distribution says is practically impossible. So a VaR model that
   assumes normality will likely underestimate tail risk. Phase 2 tests that.

## My check questions (2026-11-18)

1. **Q:** You hold ₹10 lakh of HDFC Bank and it falls 3%. What's the P&L? On a
   day NSE is shut but forex trades, what return does forward-fill give HDFC, and
   why is that reasonable?
   **My answer:** −₹30,000. With forward-fill the loss stays at 0; reasonable
   because banks aren't operational on such days and we assume it continues
   where it left off.
   **Feedback:** Correct. Precisely: that day's *return* is 0%, so that day's P&L
   is ₹0. It's the exchange (NSE) that's closed, not banks; forex still trades.
   Holiday news shows up in full on the reopening day.
2. **Q:** Why did the first glitch rule wrongly delete 23 Mar 2020, and what fixed it?
   **My answer:** The calm-times yardstick assumes such events are near-impossible,
   so it was overlooked.
   **Feedback:** Half right. The calm (19-year) yardstick made a ~10% crisis move
   look like a glitch, and the March 2020 V-shaped crash-and-bounce matched the
   "snaps back" pattern, so the day was *deleted*. The fix: measure the typical
   move over the surrounding 3 months (~3%/day in March 2020), so the threshold
   rises in a crisis.
3. **Q:** Why replace the Gold ETF with gold in rupees? What would have happened
   otherwise, and what's a downside of the substitute?
   **My answer:** Yahoo has no ETF records until 2008 (2009), hence rupee gold.
   The downside is the timing gap between international markets.
   **Feedback:** Correct. Without it, `dropna` would have deleted all 2007–08
   rows, including the 2008 crisis. The downside isn't really a delay: the two
   prices are taken at different times of day (Mumbai 3:30 pm vs COMEX ~2:30 am
   IST), so same-date moves can differ (daily correlation 0.34, weekly 0.75).

## Next phase

**Phase 2: VaR models.** Using the returns from this phase, compute 1-day 99% VaR
each day from the previous 250 days, in two ways:
- **Historical simulation:** apply each of the last 250 days' returns to today's
  holdings and take the 1st percentile of those 250 P&Ls (1% of 250 = 2.5,
  so it falls between the 2nd- and 3rd-worst day; the exact rule is set in Phase 2).
- **Parametric:** assume returns are normal and use the mean and covariance.

Both models will share one interface (`predict(returns_window) -> float`), so
later models (GARCH, ML) plug in without rework. The fat tails found here suggest
parametric VaR will be too low in crises, and Phase 4's backtest will check that.
