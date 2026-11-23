"""
run_stressed.py — Phase 3: find crisis windows and compute Stressed VaR.

    python run_stressed.py

Prints the stressed window for the 2008 crisis, for COVID 2020, and the
overall worst; SVaR from every model on each; and how SVaR compares with
today's normal VaR. Saves outputs/stressed_var.csv (git-ignored).
"""

from pathlib import Path

import pandas as pd

from config import CONFIDENCE, HOLDINGS, WINDOW
from data import load_data
from models import HistoricalVaR, ParametricVaR, rolling_var
from stressed import find_stress_window, stressed_var

OUTPUT = Path("outputs") / "stressed_var.csv"

# Periods to search. The dates limit which FORECAST days are considered; the
# window itself is the 250 days before the chosen forecast day.
PERIODS = {
    "2008 crisis": ("2008-09-01", "2009-06-30"),   # Lehman (Sep 2008) to mid-2009
    "COVID 2020": ("2020-03-01", "2020-12-31"),
    "Overall worst": (None, None),                 # anywhere in the data
}


def lakh(x):
    """Rupees -> lakh, rounded, for tables (e.g. 341000 -> 3.41)."""
    return round(x / 1e5, 2)


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    models = [HistoricalVaR(HOLDINGS, CONFIDENCE), ParametricVaR(HOLDINGS, CONFIDENCE)]

    # The window is chosen by HISTORICAL VaR (it reads the real loss tail; see
    # devnotes for why). Recompute its rolling forecasts from Phase 2.
    selector = rolling_var(models[0], returns, WINDOW)

    # For comparison only: the window PARAMETRIC VaR would pick for itself.
    param_selector = rolling_var(models[1], returns, WINDOW)

    # Today's normal VaR (last 250 days), to compare SVaR against.
    current = {m.name: m.predict(returns.iloc[-WINDOW:]) for m in models}

    # Each entry: label -> (which rolling VaR picks the window, start, end).
    searches = {label: (selector, s, e) for label, (s, e) in PERIODS.items()}
    searches["Overall worst (picked by parametric)"] = (param_selector, None, None)

    rows = []
    for label, (sel, start, end) in searches.items():
        w = find_stress_window(sel, returns, WINDOW, start, end)
        svar = stressed_var(models, w["returns"])

        # The 3 worst actual portfolio days inside this window, for context.
        window_pnl = pnl.loc[w["start"]:w["end"]]
        worst3 = window_pnl.nsmallest(3)

        row = {
            "period": label,
            "window_start": w["start"].date(),
            "window_end": w["end"].date(),
            "peak_forecast_for": w["peak_forecast_date"].date(),
        }
        for name, value in svar.items():
            row[f"svar_{name}_L"] = lakh(value)
            row[f"svar_vs_today_{name}"] = round(value / current[name], 2)
        row["worst_3_days"] = ", ".join(f"{d.date()} ({lakh(v)}L)" for d, v in worst3.items())
        rows.append(row)

    table = pd.DataFrame(rows).set_index("period")
    OUTPUT.parent.mkdir(exist_ok=True)
    table.to_csv(OUTPUT)

    print(f"Today's normal VaR (250 days ending {returns.index[-1].date()}, Rs lakh): "
          + ", ".join(f"{k} {lakh(v)}" for k, v in current.items()) + "\n")

    print("Stressed windows (chosen by the highest VaR in each period):")
    print(table[["window_start", "window_end", "peak_forecast_for"]].to_string(), "\n")

    print("Stressed VaR (Rs lakh) and how many times today's VaR it is:")
    cols = [c for c in table.columns if c.startswith("svar_")]
    print(table[cols].to_string(), "\n")

    print("Worst 3 actual days inside each window (Rs lakh):")
    for label, r in table.iterrows():
        print(f"  {label:14s} {r['worst_3_days']}")

    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
