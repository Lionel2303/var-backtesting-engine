# VaR Model Validation & Backtesting Engine

A Python engine that computes **1-day 99% Value-at-Risk (VaR)** for a ₹60 lakh
multi-asset Indian portfolio, **validates** the models by backtesting 18 years of
daily forecasts against real profit and loss, and **auto-generates a daily Excel
breach report**. It's a small version of the daily VaR / stressed VaR validation
and reporting work done by a bank's Market Risk team.

## Headline results

_All numbers come from running the code on 23 Nov 2026 (data 18 Sep 2007 → 23 Nov 2026)._

| | Historical simulation | Parametric (normal) |
|---|---|---|
| VaR for the next trading day | ₹1.11 L (1.85% of ₹60 L) | ₹1.09 L (1.81%) |
| Expected Shortfall 99%, next trading day | ₹1.41 L (1.27× VaR) | ₹1.24 L (1.14× VaR) |
| Stressed VaR (worst 250-day window: COVID) | **₹3.41 L** (3.1× today) | ₹1.51 L |
| Breaches over 4,755 days (expected 47.6) | **64** (1.35%) | **82** (1.72%) |
| Kupiec POF test (5%) | p = 0.023, reject (narrowly) | p = 5.3 × 10⁻⁶, reject |
| Basel traffic light today | **Green** (3 in 250 days) | **Amber** (7) |
| Share of days in the red zone | 0% | 5.1% |

**In one paragraph:** both models underestimate risk, because real losses have fat
tails. Parametric VaR, which assumes a bell curve, is clearly worse: it has 72% too
many breaches and spent 5% of days in the Basel red zone. Historical simulation is
the better model: it was never red and is green today. Breaches cluster in crises
(2020: 8 historical, 11 parametric). Single stocks (Infosys, Reliance, HDFC Bank)
drove 135 of the 146 breaches. For this portfolio the worst year on record is
**COVID, not 2008**.

## Portfolio (constant exposure: ₹10 lakh in each, every day)

| Asset | Yahoo ticker | Role |
|---|---|---|
| Reliance Industries | `RELIANCE.NS` | Energy / conglomerate |
| HDFC Bank | `HDFCBANK.NS` | Banking |
| Infosys | `INFY.NS` | IT (earns in USD) |
| Nifty 50 | `^NSEI` | Broad Indian market |
| Gold in rupees | `GC=F` × `USDINR=X` | Safe-haven asset (see note) |
| USD/INR | `USDINR=X` | Gains when the rupee weakens (natural hedge) |

**Why gold is "COMEX gold × USD/INR" and not a Gold ETF:** Yahoo's history for the
Nippon Gold ETF (`GOLDBEES.NS`) starts only in Jan 2009, which would remove the 2008
crisis from the whole dataset. Gold in rupees tracks the ETF over the long run
(×8.32 vs ×8.06 since 2009, weekly correlation 0.75). It lines up loosely day to day
(correlation 0.34), because COMEX closes ~11 hours after NSE.

## Method

1. **Data:** Daily closing prices (Yahoo Finance) → simple returns → daily ₹ P&L.
   - Market holidays are forward-filled (0% return), and only days with a price for
     all six assets are kept.
   - An automatic check removes bad prints. It compares each price with the median
     of the 5 days around it, scaled by that asset's typical move at the time. This
     catches glitches that snap back without deleting real crash days.
2. **VaR models:** each forecast uses only the previous 250 days (no look-ahead).
   - *Historical simulation:* replay the last 250 days on today's holdings; VaR =
     the 3rd-worst P&L.
   - *Parametric:* VaR = z·σ − μ, with σ from the covariance matrix and z = 2.326.
   - Both share one `VaRModel.predict()` interface, so new models plug in without
     changing the backtest or report code.
3. **Stressed VaR:** today's portfolio on a **fixed** 250-day window: the one behind
   the highest historical VaR in the data (the Basel 2.5 idea).
4. **Backtesting:** breach = actual P&L < −VaR.
   - **Kupiec POF** likelihood-ratio test (χ², 1 degree of freedom) on the breach
     rate.
   - **Basel traffic light** on the rolling 250-day breach count: green 0–4, amber
     5–9, red 10+.
5. **Report:** an openpyxl workbook with:
   - a Summary sheet (latest day, model validation table, colored zone)
   - a Breach Log with the asset that drove each loss
   - native Excel charts of P&L vs −VaR

## Results by phase

### Phase 1: Data
- **5,005 trading days** (18 Sep 2007 → 23 Nov 2026).
- **5 bad USD/INR prices** removed automatically (e.g. 52.49 on 31 Jan 2012, when
  the market was at ~49.5).
- Daily P&L: mean ₹2,994, standard deviation ₹53,120 (0.89% of ₹60 L).
- **Worst day: −₹4,19,227 on 23 Mar 2020**, a 7.9-standard-deviation move. That's
  evidence of fat tails. 4 of the 5 worst days are in March 2020; the other is
  24 Oct 2008 (−₹3,78,972).

### Phase 2: VaR models (4,755 daily forecasts, 2 Sep 2008 → 23 Nov 2026)
| Model | Average | Highest (date) |
|---|---|---|
| Historical simulation | ₹1.24 L | ₹3.41 L (24 Mar 2020) |
| Parametric | ₹1.09 L | ₹2.65 L (20 May 2009) |

- Historical VaR averages **1.13× parametric VaR**: the fat tails that the normal
  model misses.
- Parametric VaR peaked right after the **+₹6.0 L election-rally gain** (18 May
  2009): the normal model treats big gains as risk too.
- **Ghost effect:** historical VaR fell from ₹3.41 L to ₹1.78 L in six trading days
  (Feb–Mar 2021) as March 2020 aged out of the window, with no change in the market.

### Phase 3: Stressed VaR
| Stress window | Historical SVaR | Parametric SVaR |
|---|---|---|
| 2008 crisis (24 Jan 2008 → 7 Jan 2009) | ₹2.64 L (2.4× today) | ₹2.54 L |
| **COVID, the overall worst (10 Apr 2019 → 23 Mar 2020)** | **₹3.41 L (3.1× today)** | ₹1.51 L |

On COVID, parametric SVaR is under half of historical: the normal model averages
~10 crash days into a calm year. On 2008's longer crisis the two agree.

### Phase 4: Backtesting
| Zone (share of days) | Historical | Parametric |
|---|---|---|
| Green | 77.7% | 54.3% |
| Amber | 22.3% | 40.6% |
| Red | 0.0% | 5.1% |

Worst 250-day count: historical 9 (window ending 23 Mar 2020), parametric 12
(ending 4 May 2020). Biggest breach: 23 Mar 2020, parametric VaR ₹1.36 L vs a loss
of ₹4.19 L.

### Phase 5: Breach report
`outputs/var_breach_report_<date>.xlsx`, 4 sheets:
- **Summary:** latest day and model validation table
- **Breach Log:** 146 breaches with the driver asset
- **Charts:** 2 native charts
- **Chart Data:** the numbers behind the charts

Breach drivers: **Infosys 55, Reliance 51, HDFC Bank 29**, gold 8, Nifty 3, USD/INR
0. Example: 12 Apr 2013, historical VaR ₹86,625 vs a loss of ₹2,60,007, driven by
Infosys (−₹2,12,586 on its results day).

### Phase 7 (Stage 2): Expected Shortfall
ES = the **average** loss on the days beyond VaR (Basel's FRTB uses 97.5% ES).

| | VaR 99% | ES 99% | ES 97.5% | Stressed ES 99% |
|---|---|---|---|---|
| Historical | ₹1.11 L | ₹1.41 L | ₹1.17 L | ₹3.77 L |
| Parametric | ₹1.09 L | ₹1.24 L | ₹1.09 L | ₹1.73 L |

- Over 18 years, historical ES averages **1.23× VaR** (a bell curve gives 1.15): the
  worst 2–3 days are fatter than normal. At 97.5% both models average 1.01× VaR 99%,
  so the fat tail is concentrated in very few days.
- **97.5% ES isn't always more conservative than 99% VaR:** on the COVID window it's
  ₹2.88 L vs SVaR ₹3.41 L.
- **ES was still too small on breach days:** the average loss was 11% above historical
  ES and 24% above parametric ES.

### Phase 8: Exponentially weighted VaR (EWMA and "Responsive VaR")
Recent days get more weight: **EWMA** (RiskMetrics, λ = 0.94, half-life 11 days) and
**Responsive VaR** (weighted historical simulation, λ = 0.994 on 500 days, half-life
115 days). All four models were backtested on the same period, **18 Aug 2009 → 23 Nov
2026 (4,505 days, 45.1 breaches expected)**:

| | Historical | Parametric | EWMA | **Responsive** |
|---|---|---|---|---|
| Breaches | 58 | 77 | 76 | **47** |
| Kupiec p | 0.063 | 1.4e-05 | 2.4e-05 | **0.77** |
| Breaches in 2020 | 8 | 11 | 8 | **6** |
| Biggest one-day VaR drop | −28% | −18% | **−3%** | −19% |

- **Responsive VaR is the best model so far:** its breach count matches 1%, it has
  the fewest 2020 breaches, and it was never in the red zone.
- On 9 Mar 2020 the weighted models forecast ₹1.39–1.43 L vs historical's ₹0.93 L
  (they react faster). By 30 Sep 2020 EWMA was back to ₹1.16 L while historical
  still said ₹3.41 L (EWMA forgets faster).
- EWMA's average data age is 16 days, far below the ~130-day minimum for weighted
  models; Responsive VaR's is 140 days.

### Phase 9: GARCH(1,1), with a normal tail and Filtered Historical Simulation
GARCH **fits** the volatility dynamics: σ²ₜ₊₁ = ω + α·r²ₜ + β·σ²ₜ. EWMA is the
special case ω = 0, α+β = 1. On the full history the fit is α 0.067, β 0.920
(half-life 53 days, long-run vol 0.83%/day). Parameters are re-fitted every 21 days
on 500 days. **FHS** scales the data's own standardised surprises by the GARCH σ.

Final 6-model backtest, **18 Aug 2009 → 24 Nov 2026 (4,506 days, 45.1 expected)**:

| | Historical | Parametric | EWMA | **Responsive** | GARCH | GARCH-FHS |
|---|---|---|---|---|---|---|
| Breaches | 58 | 77 | 76 | **47** | 70 | 53 |
| Kupiec p | 0.064 | 1.4e-05 | 2.5e-05 | **0.77** | 0.00055 | 0.25 |
| Breaches in 2020 | 8 | 11 | 8 | **6** | 13 | 7 |
| Average VaR | ₹1.17 L | ₹1.01 L | ₹0.97 L | ₹1.19 L | ₹0.97 L | ₹1.08 L |

- **Tail shape matters as much as volatility.** With the same σ, FHS had 53 breaches
  against 70 for the normal tail.
- **Parameter instability:**
  - Re-fitting daily let one crash day flip α from 0.00 to 0.22 and back
    (VaR −41% in one day on 11 Mar 2020).
  - Re-fitting monthly fixed that, but 24 of 215 fits on calm 500-day windows found
    α ≈ 0. The fit held through March 2020 froze GARCH VaR at ₹0.92 L while losses
    reached ₹4.19 L.
- **Responsive VaR remains the best model overall.**

### Phase 10 (Stage 3): Christoffersen tests (do breaches bunch?)
Kupiec counts breaches. Christoffersen asks whether a breach yesterday makes one today
more likely: π11 (after a breach) vs π01 (after a calm day), LR ~ χ²(1), and the
joint conditional-coverage test, χ²(2).

| | Historical | Parametric | EWMA | Responsive | GARCH | GARCH-FHS |
|---|---|---|---|---|---|---|
| π11 (after a breach) | 6.90% | 5.19% | **3.95%** | 6.38% | 5.71% | 5.66% |
| Independence p | 0.0069 | 0.054 | **0.19** | 0.013 | 0.028 | 0.027 |
| Conditional coverage p | 0.0047 | 1.2e-05 | 5.7e-05 | 0.045 | 0.00023 | 0.044 |

- **No model passes the joint test.** Responsive and GARCH-FHS get the count right
  but fail it narrowly on back-to-back breaches.
- **EWMA bunches least:** it reacts to yesterday's loss straight away.
- The pairs are mostly the same two-day market shocks for every model:
  - Infosys's CEO resigning (Aug 2017)
  - the rupee/crude sell-off (4 Oct 2018)
  - COVID (Mar 2020)
  - the US tariff sell-off (Apr 2025)

Full write-ups, with worked examples and decisions, are in [devnotes/](devnotes/).

## Limitations

- **Constant exposure:** ₹10 lakh per asset every day, not a real share-count book.
- **Breach driver** = the asset with the biggest loss that day. This is not a formal
  attribution like component VaR.
- **Independence is tested only one day back** (Christoffersen, Phase 10). Breaches a
  few days apart in a crisis look independent; a duration test is not yet added.
- **GARCH parameters are unstable on a 500-day window:** calm windows can give α ≈ 0
  (no reaction to shocks). A longer or expanding window, or a floor on α, is untested.
- **Data:** free Yahoo Finance data, which can revise the latest day's close for a
  while after the market shuts. The gold proxy uses COMEX, which closes after NSE.

## Planned next

- ~~Expected Shortfall~~ (Phase 7), ~~EWMA / weighted VaR~~ (Phase 8) and ~~GARCH(1,1) + FHS~~ (Phase 9) done
- ~~Christoffersen test~~ (Phase 10) done; Monte Carlo VaR next (Phase 11)
- Derivatives with Greeks-based P&L explain
- Stress scenarios (RBI rate shock, rupee fall)
- An ML volatility-forecasting layer
- Production setup (scheduler, database, dashboard)

## How to run

Tested on Python 3.14.

```bash
pip install -r requirements.txt
python data.py          # Phase 1: download data, remove glitches, P&L summary + worst days
python run_var.py       # Phase 2: daily VaR from both models -> outputs/var_forecasts.csv
python run_stressed.py  # Phase 3: stressed VaR (2008 vs COVID) -> outputs/stressed_var.csv
python run_backtest.py  # Phase 4: breaches, Kupiec test, traffic light -> outputs/backtest.csv
python report.py        # Phase 5: Excel breach report -> outputs/var_breach_report_<date>.xlsx
python run_es.py        # Phase 7: Expected Shortfall vs VaR -> outputs/es_forecasts.csv
python run_responsive.py  # Phase 8: EWMA + weighted VaR, 4-model backtest -> outputs/responsive_var.csv
python run_garch.py     # Phase 9: GARCH + FHS, 6-model backtest (~1.5 min) -> outputs/garch_var.csv
python run_christoffersen.py  # Phase 10: breach independence tests (~1.5 min) -> outputs/christoffersen.csv
```

Each script downloads fresh data, so numbers move slightly as new days arrive.

## Project structure

```
config.py        all settings (portfolio, dates, confidence, window)
data.py          prices -> glitch cleaning -> returns -> portfolio P&L
models/          one file per VaR model, all sharing one interface (predict = VaR, predict_es = ES)
                   (base.py: VaRModel, rolling_var, exp_weights; historical.py; parametric.py;
                    ewma.py; weighted_historical.py; garch.py: GARCHVaR, rolling_garch)
run_var.py       runs every model through history (Phase 2)
stressed.py      finds the stressed window and computes SVaR (Phase 3)
run_stressed.py  runs Phase 3
backtest.py      breaches, Kupiec POF test, Basel traffic light (Phase 4), ES size check (Phase 7),
                   compare_models (Phases 8-9), christoffersen (Phase 10)
run_backtest.py  runs Phase 4
report.py        automated Excel breach report (Phase 5)
run_es.py        Expected Shortfall vs VaR, stressed ES, ES size check (Phase 7)
run_responsive.py  EWMA and weighted VaR vs the originals on a common period (Phase 8)
run_garch.py     GARCH and GARCH-FHS, final 6-model comparison (Phase 9)
run_christoffersen.py  breach independence / conditional coverage for all 6 models (Phase 10)
outputs/         generated files (not committed)
devnotes/        one learning note per phase + CHANGELOG.md
```
