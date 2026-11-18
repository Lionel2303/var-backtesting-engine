"""
run_var.py — Phase 2: compute daily 1-day 99% VaR with every model.

    python run_var.py

For each trading day, each model forecasts that day's VaR using only the
previous 250 days. Results are printed and saved to outputs/var_forecasts.csv
(git-ignored; regenerate any time by rerunning).
"""

from pathlib import Path   # file paths that work on Windows and Mac/Linux

import pandas as pd

from config import CONFIDENCE, HOLDINGS, WINDOW
from data import load_data
from models import HistoricalVaR, ParametricVaR, rolling_var

PORTFOLIO_VALUE = sum(HOLDINGS.values())   # Rs 60 lakh
OUTPUT = Path("outputs") / "var_forecasts.csv"


def lakh(x):
    """Format rupees in lakh for printing, e.g. 123456 -> 'Rs 1.23 L'."""
    return f"Rs {x / 1e5:.2f} L"


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]

    # One object per model, all built the same way (same interface).
    models = [HistoricalVaR(HOLDINGS, CONFIDENCE), ParametricVaR(HOLDINGS, CONFIDENCE)]

    # Run each model day by day, then put them side by side in one table:
    # one row per forecast day, one column per model.
    var = pd.concat([rolling_var(m, returns, WINDOW) for m in models], axis=1)

    # Keep the actual P&L next to the forecasts (Phase 4 compares them).
    var["actual_pnl"] = pnl.reindex(var.index)
    OUTPUT.parent.mkdir(exist_ok=True)       # create outputs/ if it isn't there
    var.to_csv(OUTPUT)

    names = [m.name for m in models]
    print(f"Forecast days: {var.index[0].date()} -> {var.index[-1].date()} "
          f"({len(var)} days; the first {WINDOW} days of data are only used for training)\n")

    # VaR for the NEXT trading day, from the most recent 250 days of data.
    latest = returns.iloc[-WINDOW:]
    print(f"VaR for the next trading day (window ending {returns.index[-1].date()}):")
    for m in models:
        v = m.predict(latest)
        print(f"  {m.name:11s} {lakh(v)}  ({v / PORTFOLIO_VALUE:.2%} of Rs 60 lakh)")

    # How VaR moved over time.
    print("\nVaR over the whole period (Rs lakh):")
    summary = pd.DataFrame({
        "average": var[names].mean(),
        "lowest": var[names].min(),
        "lowest on": var[names].idxmin().dt.date,
        "highest": var[names].max(),
        "highest on": var[names].idxmax().dt.date,
    })
    for col in ("average", "lowest", "highest"):
        summary[col] = (summary[col] / 1e5).round(2)
    print(summary.to_string())

    ratio = (var["historical"] / var["parametric"]).mean()
    print(f"\nOn average, historical VaR = {ratio:.2f} x parametric VaR")

    # VaR around key events (what each model said BEFORE the day happened).
    events = {
        "2008-10-24 (post-Lehman crash day)": "2008-10-24",
        "2020-02-14 (calm, before COVID)": "2020-02-14",
        "2020-03-23 (COVID crash day)": "2020-03-23",
    }
    print("\nVaR forecast on key days (Rs lakh) vs the actual P&L that day:")
    rows = {label: [var.loc[d, n] / 1e5 for n in names] + [var.loc[d, "actual_pnl"] / 1e5]
            for label, d in events.items()}
    print(pd.DataFrame(rows, index=names + ["actual P&L"]).T.round(2).to_string())

    # "Cliffs": the biggest one-day DROPS in each model's VaR. These happen when
    # an extreme day from 250 days ago leaves the window, not because of
    # anything that happened in the market that day (the "ghost effect").
    print("\nBiggest one-day drops in VaR (Rs lakh):")
    for n in names:
        change = var[n].diff()                        # today's VaR minus yesterday's
        for d in change.nsmallest(3).index:           # the 3 largest falls
            before = var[n].shift(1).loc[d]           # yesterday's VaR
            print(f"  {n:11s} {d.date()}: {before / 1e5:.2f} -> {var.loc[d, n] / 1e5:.2f}")

    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
