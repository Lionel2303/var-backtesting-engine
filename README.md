# VaR Model Validation & Backtesting Engine

A Python engine that computes **1-day 99% Value-at-Risk (VaR)** for a ₹60 lakh
multi-asset Indian portfolio, **validates** the models by backtesting them against
real profit and loss, and **auto-generates a daily breach report**. It's a small
version of the daily VaR/SVaR validation and reporting work done by a bank's
Market Risk team.

## Portfolio (constant exposure: ₹10 lakh in each, every day)

| Asset | Yahoo ticker | Why it's in the portfolio |
|---|---|---|
| Reliance Industries | `RELIANCE.NS` | Energy / conglomerate |
| HDFC Bank | `HDFCBANK.NS` | Banking |
| Infosys | `INFY.NS` | IT (earns in USD) |
| Nifty 50 | `^NSEI` | Broad Indian market |
| Gold in rupees | `GC=F` × `USDINR=X` | Safe-haven asset (see note) |
| USD/INR | `USDINR=X` | Gains when the rupee weakens (natural hedge) |

Data: daily closing prices from Yahoo Finance, **18 Sep 2007 → present** (the 2008
crisis is included).

**Why gold is "COMEX gold × USD/INR" and not a Gold ETF:** Yahoo's history for the
Nippon Gold ETF (`GOLDBEES.NS`) starts only in Jan 2009, which would remove the 2008
crisis from the whole dataset. Gold in rupees tracks the ETF over the long run
(×8.32 vs ×8.06 since 2009, weekly correlation 0.75). It lines up loosely day to day
(correlation 0.34), because COMEX closes ~11 hours after NSE.

## Progress (Stage 1)

- [x] Phase 1: Data layer (prices → returns → portfolio P&L), with automatic glitch cleaning
- [x] Phase 2: Historical simulation and parametric VaR (rolling 250-day window)
- [x] Phase 3: Stressed VaR (2008 crisis vs March 2020)
- [x] Phase 4: Backtesting (breach count, Kupiec POF test, Basel traffic light)
- [x] Phase 5: Automated Excel breach report
- [ ] Phase 6: Final README with results and how to run

## Results

_Every number here comes from code that has actually been run._

### Phase 1: data (run of 2026-11-18)
- **5,002 trading days** (18 Sep 2007 → 18 Nov 2026).
- **5 bad prices** detected and removed automatically, all USD/INR (e.g. 52.49 on
  31 Jan 2012, when the market was at ~49.5). The same check caught a ₹0.34
  (1/100) print in the Gold ETF series, which would have shown as a ₹9.9 crore
  one-day gain.
- Daily portfolio P&L: mean **₹3,007**, standard deviation **₹53,127** (0.89% of
  ₹60 lakh), up on 52.8% of days.
- **Worst day: −₹4,19,227 on 23 Mar 2020** (COVID crash), a 7.9-standard-deviation
  move. That's evidence of fat tails, which a normal-distribution VaR would
  underestimate.
- 4 of the 5 worst days are in March 2020. The other is 24 Oct 2008 (post-Lehman,
  −₹3,78,972). Gold cushioned losses on 2 of those 5 days and fell alongside
  stocks on the other 3.

Details: [devnotes/phase-1-data.md](devnotes/phase-1-data.md).

### Phase 2: VaR models (run of 2026-11-18)
Daily 1-day 99% VaR forecasts for **4,752 days** (2 Sep 2008 → 18 Nov 2026). Each
day's forecast uses only the previous 250 days.

| Model | Next-day VaR (19 Nov 2026) | Average | Highest (date) |
|---|---|---|---|
| Historical simulation | ₹1.11 L (1.85%) | ₹1.24 L | ₹3.41 L (24 Mar 2020) |
| Parametric (variance-covariance) | ₹1.08 L (1.80%) | ₹1.09 L | ₹2.65 L (20 May 2009) |

- Historical VaR averages **1.13× parametric VaR**: fat tails that the normal
  model misses.
- Parametric VaR peaked right after the **+₹6.0 L election-rally gain** (18 May
  2009): the normal model treats big gains as risk too.
- Both models were breached on 24 Oct 2008 (loss ₹3.79 L) and 23 Mar 2020 (loss
  ₹4.19 L vs VaR ₹2.94 L historical / ₹1.36 L parametric).
- **Ghost effect:** historical VaR fell **₹3.41 L → ₹1.78 L in six trading days**
  (Feb–Mar 2021) as March 2020 aged out of the window, with no change in the market.

Details: [devnotes/phase-2-var-models.md](devnotes/phase-2-var-models.md).

### Phase 3: Stressed VaR (run of 2026-11-23)
VaR of today's portfolio on a **fixed** 250-day crisis window (the window giving the
highest historical VaR). Today's normal VaR: ₹1.11 L (historical), ₹1.09 L (parametric).

| Stress window | Historical SVaR | Parametric SVaR |
|---|---|---|
| 2008 crisis (24 Jan 2008 → 7 Jan 2009) | ₹2.64 L (2.4× today) | ₹2.54 L |
| **COVID, the overall worst (10 Apr 2019 → 23 Mar 2020)** | **₹3.41 L (3.1× today)** | ₹1.51 L |

- The worst year for this portfolio is **COVID, not 2008**.
- On COVID, parametric SVaR is under half of historical: the normal model averages
  ~10 crash days into a calm year. On 2008's long crisis the two agree.

Details: [devnotes/phase-3-stressed-var.md](devnotes/phase-3-stressed-var.md).

### Phase 4: Backtesting (run of 2026-11-23)
Each day's VaR forecast vs that day's actual P&L, **4,755 days** (2 Sep 2008 → 23 Nov
2026). A correct 99% model would breach about **47.6** times.

| | Historical | Parametric |
|---|---|---|
| Breaches | 64 (1.35%) | 82 (1.72%) |
| Kupiec POF (5%) | p = 0.023, reject (narrowly) | p = 5.3e-06, reject |
| Basel zone today (last 250 days) | **Green** (3) | **Amber** (7) |
| Days in red zone, 2008–2026 | 0% | 5.1% |

- Both models underestimate risk. Parametric is much worse (72% too many breaches):
  the normal distribution misses fat tails.
- Historical simulation is the better model: green today and never red.
- Breaches **cluster** in crises (2020: 8 historical, 11 parametric), which Kupiec
  can't detect (that needs the Christoffersen test).

Details: [devnotes/phase-4-backtesting.md](devnotes/phase-4-backtesting.md).

### Phase 5: Breach report (run of 2026-11-23)
`python report.py` builds `outputs/var_breach_report_<date>.xlsx`, with 4 sheets:
- **Summary:** latest day's forecast vs actual P&L and breach flag, then per model:
  next-day VaR, stressed VaR, breaches vs expected, Kupiec, Basel zone (colored).
- **Breach Log:** all **146 breaches** (64 historical + 82 parametric), each with
  the asset that drove the loss.
- **Charts:** native Excel charts of P&L vs −VaR (last 250 days and full history),
  with breaches as red dots.
- **Chart Data:** the numbers behind the charts.

Who drove the breaches: **Infosys 55, Reliance 51, HDFC Bank 29**, gold 8, Nifty 3,
USD/INR 0. Single stocks drove 135 of 146 (concentration risk), and USD/INR never
did (natural hedge). Example: 12 Apr 2013, historical VaR ₹86,625 vs loss ₹2,60,007,
driven by Infosys (−₹2,12,586).

Details: [devnotes/phase-5-breach-report.md](devnotes/phase-5-breach-report.md).

## How to run

```bash
pip install -r requirements.txt
python data.py        # Phase 1: download data, remove glitches, show P&L summary + worst days
python run_var.py     # Phase 2: daily VaR from both models -> outputs/var_forecasts.csv
python run_stressed.py  # Phase 3: stressed VaR (2008 vs COVID) -> outputs/stressed_var.csv
python run_backtest.py  # Phase 4: breaches, Kupiec test, traffic light -> outputs/backtest.csv
python report.py        # Phase 5: Excel breach report -> outputs/var_breach_report_<date>.xlsx
```

## Project structure

```
config.py      all settings (portfolio, dates, confidence, window)
data.py        prices -> returns -> portfolio P&L
models/        one file per VaR model, all sharing one interface
                 (base.py: VaRModel + rolling_var; historical.py; parametric.py)
run_var.py     runs every model through history (Phase 2)
stressed.py    finds the stressed window and computes SVaR (Phase 3)
run_stressed.py  runs Phase 3
backtest.py    breaches, Kupiec POF test, Basel traffic light (Phase 4)
run_backtest.py  runs Phase 4
report.py      automated Excel breach report (Phase 5)
outputs/       generated reports (not committed)
devnotes/      one learning note per phase + CHANGELOG.md
```
