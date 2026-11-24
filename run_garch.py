"""
run_garch.py — Phase 9: GARCH(1,1) VaR, and the final comparison of all 6 models.

    python run_garch.py      (about 1 minute; GARCH re-fitted every 21 days)

Prints: GARCH parameters fitted on the whole history vs EWMA's fixed ones;
next-day VaR/ES for every model; the 6-model backtest on a common period;
reaction around COVID; the biggest one-day VaR drops; and how many GARCH fits
failed to converge. Saves outputs/garch_var.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from backtest import compare_models
from config import (CONFIDENCE, EWMA_LAMBDA, GARCH_REFIT_EVERY, GARCH_WINDOW, HOLDINGS,
                    RESPONSIVE_LAMBDA, RESPONSIVE_WINDOW, WINDOW)
from data import load_data
from models import (FIT_STATS, EWMAVaR, GARCHVaR, HistoricalVaR, ParametricVaR,
                    WeightedHistoricalVaR, fit_garch, rolling_garch, rolling_var)


def rolling(model, returns, window, measure="var"):
    """GARCH models use the re-fit-every-21-days loop; all others use rolling_var."""
    conf = None if measure == "var" else CONFIDENCE
    if isinstance(model, GARCHVaR):      # isinstance: "is this model a GARCHVaR?"
        return rolling_garch(model, returns, window, GARCH_REFIT_EVERY, measure, conf)
    return rolling_var(model, returns, window, measure, conf)

OUTPUT = Path("outputs") / "garch_var.csv"
P = 1 - CONFIDENCE


def lakh(x):
    """Rupees -> lakh, 2 decimals (e.g. 341000 -> 3.41)."""
    return round(x / 1e5, 2)


def describe_params(params):
    """omega, alpha, beta -> a readable line with persistence, half-life, long-run vol."""
    o, a, b = params["omega"], params["alpha[1]"], params["beta[1]"]
    persistence = a + b
    half_life = np.log(0.5) / np.log(persistence)      # days for a shock's effect to halve
    long_run = np.sqrt(o / (1 - persistence))          # % per day
    return (f"omega {o:.4f}  alpha {a:.3f}  beta {b:.3f}  | alpha+beta {persistence:.3f}"
            f"  half-life {half_life:.0f} days  long-run vol {long_run:.2f}%/day")


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    value = sum(HOLDINGS.values())

    # 1. GARCH fitted once on the WHOLE history, to compare with EWMA's fixed choice.
    port_pct = (returns @ pd.Series(HOLDINGS)[returns.columns]) / value * 100
    full = fit_garch(port_pct)
    print(f"GARCH(1,1) on the whole history ({len(port_pct)} days):")
    print("  " + describe_params(full["params"]))
    print(f"  EWMA (fixed): omega 0, alpha {1 - EWMA_LAMBDA:.2f}, beta {EWMA_LAMBDA:.2f}"
          f" | alpha+beta 1.00 (no long-run level)")
    latest = fit_garch(port_pct.iloc[-GARCH_WINDOW:])
    print(f"GARCH(1,1) on the latest {GARCH_WINDOW} days:")
    print("  " + describe_params(latest["params"]) + "\n")

    setup = [
        (HistoricalVaR(HOLDINGS, CONFIDENCE), WINDOW),
        (ParametricVaR(HOLDINGS, CONFIDENCE), WINDOW),
        (EWMAVaR(HOLDINGS, CONFIDENCE, EWMA_LAMBDA), WINDOW),
        (WeightedHistoricalVaR(HOLDINGS, CONFIDENCE, RESPONSIVE_LAMBDA), RESPONSIVE_WINDOW),
        (GARCHVaR(HOLDINGS, CONFIDENCE, "normal"), GARCH_WINDOW),
        (GARCHVaR(HOLDINGS, CONFIDENCE, "fhs"), GARCH_WINDOW),
    ]
    names = [m.name for m, _ in setup]

    # 2. Next trading day.
    print(f"Next trading day (data to {returns.index[-1].date()}), Rs lakh:")
    for m, win in setup:
        recent = returns.iloc[-win:]
        print(f"  {m.name:11s} VaR {lakh(m.predict(recent)):5.2f}   ES {lakh(m.predict_es(recent)):5.2f}")
    print()

    # 3. Rolling forecasts. VaR and ES are computed day by day, model by model;
    #    the two GARCH models share each day's fit through the cache.
    var = pd.concat([rolling(m, returns, w) for m, w in setup], axis=1).dropna()
    es = pd.concat([rolling(m, returns, w, "es") for m, w in setup], axis=1)
    es = es.loc[var.index]
    actual = pnl.reindex(var.index)
    print(f"Common backtest period: {var.index[0].date()} -> {var.index[-1].date()} "
          f"({len(var)} days; expected breaches at 1% = {P * len(var):.1f})")
    print(f"GARCH re-fit every {GARCH_REFIT_EVERY} days: {FIT_STATS['fits']} fits "
          f"({FIT_STATS['not_converged']} not converged), {FIT_STATS['fixed']} days with held parameters\n")

    summary, breaches = compare_models(var, es, actual, P)
    print("Backtest on the common period:")
    print(summary.to_string(), "\n")

    # 4. Reaction around COVID.
    days = ["2020-02-14", "2020-03-09", "2020-03-12", "2020-03-16", "2020-03-23",
            "2020-04-30", "2020-09-30"]
    react = (var.loc[days, names] / 1e5).round(2)
    react["actual_pnl"] = (actual.loc[days] / 1e5).round(2)
    react.index = react.index.date
    print("VaR forecast around COVID (Rs lakh) vs actual P&L that day:")
    print(react.to_string(), "\n")

    # 5. Calm-period floor: the LOWEST VaR each model ever forecast.
    print("Lowest VaR forecast (Rs lakh, date):")
    for n in names:
        print(f"  {n:11s} {lakh(var[n].min())}  ({var[n].idxmin().date()})")
    print()

    # 6. Ghost-effect cliffs: biggest one-day drop.
    print("Biggest one-day drop in VaR (Rs lakh):")
    for n in names:
        change = var[n].diff()
        d = change.idxmin()
        before = var[n].shift(1).loc[d]
        print(f"  {n:11s} {d.date()}: {lakh(before)} -> {lakh(var.loc[d, n])}  ({change.min() / before:.0%})")

    out = var.join(es).assign(actual_pnl=actual)
    for n in names:
        out[f"breach_{n}"] = breaches[n]
    OUTPUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUTPUT)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
