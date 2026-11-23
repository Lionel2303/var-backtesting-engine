"""
run_backtest.py — Phase 4: backtest every VaR model.

    python run_backtest.py

For each model: count breaches over the whole history, run the Kupiec test,
give the Basel traffic-light zone for the latest 250 days, show how often the
model sat in each zone, and when the breaches happened. Saves
outputs/backtest.csv (git-ignored).
"""

from pathlib import Path

import pandas as pd

from backtest import find_breaches, kupiec_pof, rolling_zone
from config import CONFIDENCE, HOLDINGS, WINDOW
from data import load_data
from models import HistoricalVaR, ParametricVaR, rolling_var

OUTPUT = Path("outputs") / "backtest.csv"
P = 1 - CONFIDENCE   # expected breach rate: 1%


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    models = [HistoricalVaR(HOLDINGS, CONFIDENCE), ParametricVaR(HOLDINGS, CONFIDENCE)]

    # Daily VaR forecasts (exactly as in Phase 2) and the actual P&L each day.
    var = pd.concat([rolling_var(m, returns, WINDOW) for m in models], axis=1)
    var["actual_pnl"] = pnl.reindex(var.index)
    names = [m.name for m in models]
    n_days = len(var)

    print(f"Backtest period: {var.index[0].date()} -> {var.index[-1].date()} "
          f"({n_days} forecast days; expected breaches at 1% = {P * n_days:.1f})\n")

    summary, zones = {}, {}
    for n in names:
        b = find_breaches(var[n], var["actual_pnl"])      # True on breach days
        var[f"breach_{n}"] = b
        k = kupiec_pof(int(b.sum()), n_days, P)
        z = rolling_zone(b, 250)                          # zone for every day
        zones[n] = z
        summary[n] = {
            "breaches": int(b.sum()),
            "expected": round(P * n_days, 1),
            "breach_rate": f"{b.mean():.2%}",
            "kupiec_LR": round(k["LR"], 2),
            "p_value": f"{k['p_value']:.2g}",   # 2 significant figures, e.g. 0.023 or 5.3e-06
            "kupiec": k["verdict"],
            "last_250d_breaches": int(z["breaches_250d"].iloc[-1]),
            "zone_today": z["zone"].iloc[-1],
        }
    print("Whole-period backtest:")
    print(pd.DataFrame(summary).to_string(), "\n")

    # How much of the time was each model green / amber / red?
    print("Share of days in each traffic-light zone (rolling 250-day count):")
    share = pd.DataFrame({n: zones[n]["zone"].value_counts(normalize=True)
                          for n in names}).reindex(["green", "amber", "red"]).fillna(0)
    print((share * 100).round(1).astype(str).add("%").to_string())
    for n in names:
        z = zones[n]
        worst = z["breaches_250d"].idxmax()
        print(f"  {n}: worst 250-day count = {z['breaches_250d'].max()} "
              f"(window ending {worst.date()})")
    print()

    # When did breaches happen? Breaches per calendar year.
    by_year = pd.DataFrame({n: var[f"breach_{n}"].groupby(var.index.year).sum()
                            for n in names})
    by_year["days"] = var.groupby(var.index.year).size()
    print("Breaches per year:")
    print(by_year.T.to_string(), "\n")

    # The 5 biggest breaches: how far the loss went beyond the forecast.
    for n in names:
        hit = var[var[f"breach_{n}"]]
        excess = (-hit["actual_pnl"] - hit[n]).nlargest(5)   # loss minus VaR
        print(f"Biggest breaches, {n} (Rs lakh: VaR -> actual loss, excess):")
        for d, e in excess.items():
            print(f"  {d.date()}: {hit.loc[d, n] / 1e5:.2f} -> "
                  f"{-hit.loc[d, 'actual_pnl'] / 1e5:.2f}  (+{e / 1e5:.2f})")
    OUTPUT.parent.mkdir(exist_ok=True)
    var.to_csv(OUTPUT)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
