"""
run_monte_carlo.py — Phase 11: Monte Carlo VaR (normal and Student-t draws).

    python run_monte_carlo.py      (about 1 minute)

Prints: hand-checks (Cholesky, 1M-draw MC vs the parametric formula); how much
MC VaR wobbles with the number of draws (sampling noise); next-day VaR/ES; and a
backtest of MC-normal and MC-t against their 250-day peers (historical,
parametric) over the full period, with Kupiec and Christoffersen.
Saves outputs/monte_carlo_var.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from backtest import christoffersen, compare_models, find_breaches, kupiec_pof
from config import CONFIDENCE, HOLDINGS, MC_SEED, MC_SIMS, MC_T_DF, WINDOW
from data import load_data
from models import HistoricalVaR, MonteCarloVaR, ParametricVaR, rolling_var

OUTPUT = Path("outputs") / "monte_carlo_var.csv"
P = 1 - CONFIDENCE


def lakh(x):
    """Rupees -> lakh, 2 decimals (e.g. 341000 -> 3.41)."""
    return round(x / 1e5, 2)


def hand_checks(recent):
    """Check the simulation against formulas on the latest 250-day window."""
    cov = recent.cov().to_numpy()
    L = np.linalg.cholesky(cov)
    print(f"  Cholesky: largest |L @ L.T - cov| = {np.abs(L @ L.T - cov).max():.1e} (should be ~0)")

    para = ParametricVaR(HOLDINGS, CONFIDENCE)
    mu, sigma = para._mu_sigma(recent)
    big_normal = MonteCarloVaR(HOLDINGS, CONFIDENCE, 1_000_000, "normal", seed=MC_SEED)
    print(f"  1M normal draws: VaR Rs {big_normal.predict(recent):,.0f}  vs parametric formula "
          f"Rs {para.predict(recent):,.0f}")

    # Student-t with unit variance: 1% point = t.ppf(0.99, df) x sqrt((df - 2) / df)
    k = student_t.ppf(CONFIDENCE, MC_T_DF) * np.sqrt((MC_T_DF - 2) / MC_T_DF)
    big_t = MonteCarloVaR(HOLDINGS, CONFIDENCE, 1_000_000, "t", MC_T_DF, MC_SEED)
    print(f"  1M t({MC_T_DF}) draws:   VaR Rs {big_t.predict(recent):,.0f}  vs formula "
          f"{k:.3f} x sigma - mu = Rs {k * sigma - mu:,.0f}")
    # Simulated P&L must have the same sigma whichever distribution is used.
    print(f"  sigma of simulated P&L: normal Rs {big_normal.simulate(recent).std():,.0f}, "
          f"t Rs {big_t.simulate(recent).std():,.0f}, formula Rs {sigma:,.0f}\n")


def sampling_noise(recent):
    """VaR on the same window with different numbers of draws and 5 different seeds."""
    rows = {}
    for n in (1_000, 10_000, 100_000):
        vals = [MonteCarloVaR(HOLDINGS, CONFIDENCE, n, "normal", seed=s).predict(recent)
                for s in range(1, 6)]
        rows[f"{n:,} draws"] = {"lowest": lakh(min(vals)), "highest": lakh(max(vals)),
                                "spread_%": round((max(vals) - min(vals)) / np.mean(vals) * 100, 1)}
    return pd.DataFrame(rows).T


def nu_sensitivity(returns, pnl, nus=(3, 4, 5, 6, 8, 10, 30)):
    """
    How much does the CHOICE of df (nu) matter? nu = 5 is an assumption, not a fit.

    For each nu, VaR = k(nu) x sigma - mu every day, where k(nu) = the 1% point of a
    unit-variance t (e.g. nu 5 -> 2.606, nu 30 -> 2.374, normal -> 2.326).
    This is MC-t without the sampling noise (the hand-check shows they agree).
    Choosing nu by THIS table would be tuning on the test set, so it is a
    robustness check only.
    """
    para = ParametricVaR(HOLDINGS, CONFIDENCE)
    days = returns.index[WINDOW:]
    # mu and sigma of portfolio P&L on each trailing 250-day window (as parametric VaR)
    mu_sigma = [para._mu_sigma(returns.iloc[i - WINDOW:i]) for i in range(WINDOW, len(returns))]
    mu = pd.Series([m for m, _ in mu_sigma], index=days)
    sigma = pd.Series([s for _, s in mu_sigma], index=days)
    actual = pnl.reindex(days)
    rows = {}
    for nu in nus:
        k = student_t.ppf(CONFIDENCE, nu) * np.sqrt((nu - 2) / nu)   # unit-variance t quantile
        var = k * sigma - mu
        b = find_breaches(var, actual)
        rows[f"nu {nu}"] = {"k (x sigma)": round(k, 3), "breaches": int(b.sum()),
                            "kupiec_p": f"{kupiec_pof(int(b.sum()), len(days), P)['p_value']:.2g}",
                            "avg_VaR_L": lakh(var.mean())}
    return pd.DataFrame(rows).T


def main():
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    recent = returns.iloc[-WINDOW:]

    print("Hand-checks (latest 250-day window):")
    hand_checks(recent)

    print("Sampling noise: MC-normal VaR (Rs lakh) with 5 different seeds:")
    print(sampling_noise(recent).to_string(), "\n")

    models = [HistoricalVaR(HOLDINGS, CONFIDENCE), ParametricVaR(HOLDINGS, CONFIDENCE),
              MonteCarloVaR(HOLDINGS, CONFIDENCE, MC_SIMS, "normal", seed=MC_SEED),
              MonteCarloVaR(HOLDINGS, CONFIDENCE, MC_SIMS, "t", MC_T_DF, MC_SEED)]

    print(f"Next trading day (data to {returns.index[-1].date()}), Rs lakh:")
    for m in models:
        print(f"  {m.name:10s} VaR {lakh(m.predict(recent)):5.2f}   ES {lakh(m.predict_es(recent)):5.2f}")
    print()

    # All four use 250 days, so the full period from Phase 4 is available.
    var = pd.concat([rolling_var(m, returns, WINDOW) for m in models], axis=1)
    es = pd.concat([rolling_var(m, returns, WINDOW, "es", CONFIDENCE) for m in models], axis=1)
    actual = pnl.reindex(var.index)
    print(f"Backtest period: {var.index[0].date()} -> {var.index[-1].date()} "
          f"({len(var)} days; expected breaches {P * len(var):.1f})")
    summary, breaches = compare_models(var, es, actual, P)
    for n in var.columns:                       # add the Phase 10 tests
        c = christoffersen(breaches[n], P)
        summary.loc["independence_p", n] = f"{c['p_ind']:.2g}"
        summary.loc["cond_coverage_p", n] = f"{c['p_cc']:.2g}"
    print(summary.to_string(), "\n")

    ratio = (var["mc_normal"] / var["parametric"])
    print(f"MC-normal / parametric VaR, every day: average {ratio.mean():.3f}, "
          f"range {ratio.min():.3f} - {ratio.max():.3f}")
    ratio_t = (var["mc_t"] / var["mc_normal"])
    print(f"MC-t / MC-normal VaR, every day: average {ratio_t.mean():.3f}\n")

    print(f"Sensitivity to the t degrees of freedom (nu = {MC_T_DF} is an assumption):")
    print(nu_sensitivity(returns, pnl).to_string())

    out = var.join(es).assign(actual_pnl=actual)
    for n in var.columns:
        out[f"breach_{n}"] = breaches[n]
    OUTPUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUTPUT)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
