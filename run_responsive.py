"""
run_responsive.py — Phase 8: do exponentially weighted models react faster?

    python run_responsive.py

Four models, side by side:
    historical   equal weights, 250 days                (Phase 2)
    parametric   bell curve, equal weights, 250 days    (Phase 2)
    ewma         bell curve, RiskMetrics weights lam = 0.94, 250 days
    weighted_hs  "responsive VaR": historical with lam = 0.994, 500 days

All four are backtested on the SAME dates (the 500-day model starts ~1 year
later), so the comparison is fair. Prints: next-day VaR/ES, the backtest
(breaches, Kupiec, zones, 2020 cluster, ES size check), how fast each model
reacted in March 2020, the biggest one-day VaR drops (ghost-effect cliffs),
and each model's weighted data age. Saves outputs/responsive_var.csv.
"""

from pathlib import Path

import pandas as pd

from backtest import compare_models
from config import (CONFIDENCE, EWMA_LAMBDA, HOLDINGS, RESPONSIVE_LAMBDA,
                    RESPONSIVE_WINDOW, WINDOW)
from data import load_data
from models import (EWMAVaR, HistoricalVaR, ParametricVaR, WeightedHistoricalVaR,
                    rolling_var, weighted_age)

OUTPUT = Path("outputs") / "responsive_var.csv"
P = 1 - CONFIDENCE    # expected breach rate: 1%


def lakh(x):
    """Rupees -> lakh, 2 decimals (e.g. 341000 -> 3.41)."""
    return round(x / 1e5, 2)


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]

    # (model, its window, its decay factor; 1.0 = equal weights)
    setup = [
        (HistoricalVaR(HOLDINGS, CONFIDENCE), WINDOW, 1.0),
        (ParametricVaR(HOLDINGS, CONFIDENCE), WINDOW, 1.0),
        (EWMAVaR(HOLDINGS, CONFIDENCE, EWMA_LAMBDA), WINDOW, EWMA_LAMBDA),
        (WeightedHistoricalVaR(HOLDINGS, CONFIDENCE, RESPONSIVE_LAMBDA), RESPONSIVE_WINDOW,
         RESPONSIVE_LAMBDA),
    ]
    names = [m.name for m, _, _ in setup]

    # Rolling VaR and ES for every model, each with its own window.
    var = pd.concat([rolling_var(m, returns, win) for m, win, _ in setup], axis=1)
    es = pd.concat([rolling_var(m, returns, win, "es", CONFIDENCE) for m, win, _ in setup], axis=1)
    # Keep only dates where ALL models have a forecast (a fair, common test period).
    var = var.dropna()
    es = es.loc[var.index]
    actual = pnl.reindex(var.index)
    n_days = len(var)
    print(f"Common backtest period: {var.index[0].date()} -> {var.index[-1].date()} "
          f"({n_days} days; expected breaches at 1% = {P * n_days:.1f})\n")

    # 1. Next trading day.
    print(f"Next trading day (data to {returns.index[-1].date()}), Rs lakh:")
    for m, win, lam in setup:
        recent = returns.iloc[-win:]
        print(f"  {m.name:11s} VaR {lakh(m.predict(recent)):5.2f}   ES {lakh(m.predict_es(recent)):5.2f}"
              f"   (window {win}, lambda {lam}, weighted data age {weighted_age(win, lam):.0f} days)")
    print()

    # 2. Backtest every model on the common period (same scoring for every model).
    summary, breaches = compare_models(var, es, actual, P)
    print("Backtest on the common period:")
    print(summary.to_string(), "\n")

    # 3. Reaction speed: what each model forecast around the COVID crash.
    days = ["2020-02-14", "2020-03-09", "2020-03-12", "2020-03-16", "2020-03-23",
            "2020-04-30", "2020-09-30"]
    react = (var.loc[days, names] / 1e5).round(2)
    react["actual_pnl"] = (actual.loc[days] / 1e5).round(2)
    react.index = react.index.date
    print("VaR forecast around COVID (Rs lakh) vs actual P&L that day:")
    print(react.to_string(), "\n")

    # 4. Ghost-effect cliffs: the biggest one-day DROP in each model's VaR.
    print("Biggest one-day drop in VaR (Rs lakh):")
    for n in names:
        change = var[n].diff()
        d = change.idxmin()
        print(f"  {n:11s} {d.date()}: {lakh(var[n].shift(1).loc[d])} -> {lakh(var.loc[d, n])}"
              f"  ({change.min() / var[n].shift(1).loc[d]:.0%})")

    out = var.join(es).assign(actual_pnl=actual)
    for n in names:
        out[f"breach_{n}"] = breaches[n]
    OUTPUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUTPUT)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
