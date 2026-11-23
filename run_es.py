"""
run_es.py — Phase 7: Expected Shortfall (ES) next to VaR.

    python run_es.py

VaR = the loss we exceed only 1% of the time (a threshold).
ES  = the AVERAGE loss on those worst days (how bad "bad" is).

Prints: next-day VaR and ES for every model; how much bigger ES is than VaR on
average; ES 97.5% (Basel's newer FRTB measure) vs VaR 99%; stressed ES on the
worst window; and a check of whether ES had the right size on breach days.
Saves outputs/es_forecasts.csv (git-ignored).
"""

from pathlib import Path

import pandas as pd

from backtest import es_severity, find_breaches
from config import CONFIDENCE, ES_CONFIDENCE, HOLDINGS, WINDOW
from data import load_data
from models import HistoricalVaR, ParametricVaR, rolling_var
from stressed import find_stress_window

OUTPUT = Path("outputs") / "es_forecasts.csv"


def lakh(x):
    """Rupees -> lakh, 2 decimals, for printing (e.g. 341000 -> 3.41)."""
    return round(x / 1e5, 2)


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    models = [HistoricalVaR(HOLDINGS, CONFIDENCE), ParametricVaR(HOLDINGS, CONFIDENCE)]
    names = [m.name for m in models]

    # Rolling forecasts for every model: VaR 99%, ES 99%, ES 97.5%.
    cols = {}
    for m in models:
        cols[f"{m.name}_var99"] = rolling_var(m, returns, WINDOW, "var")
        cols[f"{m.name}_es99"] = rolling_var(m, returns, WINDOW, "es", CONFIDENCE)
        cols[f"{m.name}_es975"] = rolling_var(m, returns, WINDOW, "es", ES_CONFIDENCE)
    table = pd.DataFrame(cols)
    table["actual_pnl"] = pnl.reindex(table.index)
    print(f"Forecast days: {table.index[0].date()} -> {table.index[-1].date()} ({len(table)} days)\n")

    # 1. Next trading day: VaR vs ES from the latest 250 days.
    latest = returns.iloc[-WINDOW:]
    print(f"Next trading day (window ending {returns.index[-1].date()}), Rs lakh:")
    rows = {}
    for m in models:
        v, e99, e975 = (m.predict(latest), m.predict_es(latest),
                        m.predict_es(latest, ES_CONFIDENCE))
        rows[m.name] = {"VaR 99%": lakh(v), "ES 99%": lakh(e99), "ES / VaR": round(e99 / v, 2),
                        "ES 97.5%": lakh(e975), "ES97.5 / VaR99": round(e975 / v, 2)}
    print(pd.DataFrame(rows).T.to_string(), "\n")

    # 2. Over the whole history: how much bigger is ES than VaR, on average?
    print("Average over all forecast days:")
    for n in names:
        es_ratio = (table[f"{n}_es99"] / table[f"{n}_var99"]).mean()
        frtb_ratio = (table[f"{n}_es975"] / table[f"{n}_var99"]).mean()
        print(f"  {n:11s} ES99 / VaR99 = {es_ratio:.2f}   ES97.5 / VaR99 = {frtb_ratio:.2f}")
    print("  (a perfect bell curve gives 1.15 and 1.01)\n")

    # 3. Stressed ES: ES on the same fixed crisis window as Phase 3's stressed VaR.
    stress = find_stress_window(table["historical_var99"], returns, WINDOW)
    w = stress["returns"]
    print(f"Stressed window {stress['start'].date()} -> {stress['end'].date()}, Rs lakh:")
    for m in models:
        print(f"  {m.name:11s} SVaR 99% {lakh(m.predict(w))}   stressed ES 99% {lakh(m.predict_es(w))}"
              f"   stressed ES 97.5% {lakh(m.predict_es(w, ES_CONFIDENCE))}")
    print()

    # 4. Was ES the right size? Average loss on VaR-breach days vs average ES then.
    print("On VaR-breach days: average actual loss vs average ES 99% forecast (Rs lakh):")
    for n in names:
        b = find_breaches(table[f"{n}_var99"], table["actual_pnl"])
        s = es_severity(b, table[f"{n}_es99"], table["actual_pnl"])
        print(f"  {n:11s} {s['breach_days']} days: loss {lakh(s['avg_loss'])} vs ES "
              f"{lakh(s['avg_es'])}  -> ratio {s['ratio']:.2f}")
    print()

    # 5. Key day: what VaR and ES said before 23 Mar 2020.
    d = "2020-03-23"
    print(f"{d} (COVID crash): actual loss {lakh(-table.loc[d, 'actual_pnl'])} L")
    for n in names:
        print(f"  {n:11s} VaR {lakh(table.loc[d, f'{n}_var99'])}   ES {lakh(table.loc[d, f'{n}_es99'])}")

    OUTPUT.parent.mkdir(exist_ok=True)
    table.to_csv(OUTPUT)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
