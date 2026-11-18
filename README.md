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
| Gold ETF (Nippon GoldBeES) | `GOLDBEES.NS` | Safe-haven asset |
| USD/INR | `USDINR=X` | Gains when the rupee weakens (natural hedge) |

Data: daily closing prices from Yahoo Finance, from 2007 (so the 2008 crisis is included).

## Progress (Stage 1)

- [ ] Phase 1: Data layer (prices → returns → portfolio P&L)
- [ ] Phase 2: Historical simulation and parametric VaR (rolling 250-day window)
- [ ] Phase 3: Stressed VaR (2008 crisis vs March 2020)
- [ ] Phase 4: Backtesting (breach count, Kupiec POF test, Basel traffic light)
- [ ] Phase 5: Automated Excel breach report
- [ ] Phase 6: Final README with results and how to run

## Results

_None yet. Every number here will come from code that has actually been run._

## How to run

```bash
pip install -r requirements.txt
python data.py        # Phase 1: download data, show portfolio P&L summary
```

## Project structure

```
config.py      all settings (portfolio, dates, confidence, window)
data.py        prices -> returns -> portfolio P&L
models/        one file per VaR model, all sharing one interface
backtest.py    VaR forecast vs next-day P&L, Kupiec test, traffic light
report.py      Excel breach report
outputs/       generated reports (not committed)
devnotes/      one learning note per phase + CHANGELOG.md
```
