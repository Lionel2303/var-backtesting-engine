"""
run_christoffersen.py — Phase 10: do VaR breaches bunch together?

    python run_christoffersen.py      (about 1.5 minutes: it rebuilds the 6 models)

Kupiec (Phase 4) asked "is the NUMBER of breaches right?". Christoffersen asks
"are they spread out, or does one breach make the next more likely?".
For each of the 6 models on the common period it prints: breach counts, the
day-after-breach table (n01, n11, pi01, pi11), the independence test, the joint
conditional-coverage test, and the longest streak of back-to-back breaches.
Saves outputs/christoffersen.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from backtest import christoffersen, find_breaches, kupiec_pof, longest_run
from config import CONFIDENCE
from data import load_data
from run_garch import six_model_forecasts

OUTPUT = Path("outputs") / "christoffersen.csv"
P = 1 - CONFIDENCE


def hand_check():
    """The toy example from the docstring: 5 breaches in 250 days, spread vs bunched."""
    spread = np.zeros(250, dtype=bool)
    spread[[30, 80, 130, 180, 230]] = True     # breaches 50 days apart
    bunched = np.zeros(250, dtype=bool)
    bunched[120:125] = True                    # 5 breaches in a row
    for label, b in [("spread out", spread), ("bunched", bunched)]:
        c = christoffersen(pd.Series(b), P)
        print(f"  {label:10s} n11 {c['n11']}  pi11 {c['pi11']:.0%}  LR_ind {c['LR_ind']:.2f}"
              f"  p {c['p_ind']:.2g}  -> {c['ind']}")


def main():
    print("Hand-check (expected: spread LR 0.20 pass; bunched LR 30.98 REJECT):")
    hand_check()
    print()

    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    var, _ = six_model_forecasts(returns)     # ES not needed here
    actual = pnl.reindex(var.index)
    n_days = len(var)
    print(f"Common period: {var.index[0].date()} -> {var.index[-1].date()} "
          f"({n_days} days; expected breaches {P * n_days:.1f})\n")

    rows = {}
    for n in var.columns:
        b = find_breaches(var[n], actual)
        c = christoffersen(b, P)
        k = kupiec_pof(int(b.sum()), n_days, P)
        rows[n] = {
            "breaches": int(b.sum()),
            "breach->breach (n11)": c["n11"],
            "pi01 (after calm)": f"{c['pi01']:.2%}",
            "pi11 (after breach)": f"{c['pi11']:.2%}",
            "longest_streak": longest_run(b),
            "kupiec_p": f"{k['p_value']:.2g}",
            "LR_ind": round(c["LR_ind"], 2),
            "ind_p": f"{c['p_ind']:.2g}",
            "independence": c["ind"],
            "LR_cc": round(c["LR_cc"], 2),
            "cc_p": f"{c['p_cc']:.2g}",
            "cond_coverage": c["cc"],
        }
    table = pd.DataFrame(rows)
    print("Christoffersen tests on the common period:")
    print(table.to_string(), "\n")

    # Where did the back-to-back breaches happen? (dates of every breach -> breach pair)
    print("Back-to-back breach days (the second day of each pair):")
    for n in var.columns:
        b = find_breaches(var[n], actual)
        second = b & b.shift(1, fill_value=False)   # breach today AND yesterday
        dates = [d.strftime("%Y-%m-%d") for d in b.index[second]]
        print(f"  {n:11s} {', '.join(dates) if dates else '-'}")

    OUTPUT.parent.mkdir(exist_ok=True)
    table.T.to_csv(OUTPUT)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
