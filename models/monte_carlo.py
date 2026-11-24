"""
models/monte_carlo.py — Monte Carlo VaR: simulate many possible next days.

Steps, for each forecast:
    1. From the last 250 days, estimate each asset's average return (mu) and the
       6 x 6 covariance matrix (Sigma), exactly as parametric VaR does.
    2. Cholesky: split Sigma = L x L^T. L turns INDEPENDENT random numbers into
       CORRELATED asset returns.
       2-asset example: vols 1% and 2%, correlation 0.5 -> Sigma = [[1, 1], [1, 4]] (%^2)
           L = [[1, 0], [1, 1.732]]
           draws z = (-2.0, +0.5) -> returns = L x z = (-2.0%, 1x(-2.0) + 1.732x0.5 = -1.13%)
           the second asset inherits part of the first one's bad draw = correlation.
    3. Repeat n_sims times (10,000), value each simulated day in rupees with
       today's holdings, and read off VaR = the 1%-worst P&L (100th-worst of
       10,000) and ES = the average of the days at or below it.

dist="normal": bell-curve draws -> the same answer as parametric VaR, plus noise.
dist="t"     : Student-t draws with df degrees of freedom, scaled to the SAME
               covariance but with fatter tails. df = 5: the 1% point is
               2.61 sigma instead of 2.33 sigma (+12%).
               How: divide the normal draws by sqrt(W / (df - 2)) with W a
               chi-squared(df) draw. A small W (rare) makes a big day for ALL
               assets at once, the "everything crashes together" days.

A fixed seed means every call uses the same random numbers, so results are
reproducible and VaR and ES come from the same simulated days.
"""

import numpy as np

from models.base import VaRModel


class MonteCarloVaR(VaRModel):
    """1-day VaR and ES from simulated correlated asset returns."""

    def __init__(self, holdings, confidence, n_sims=10_000, dist="normal", df=5, seed=42):
        super().__init__(holdings, confidence)
        if dist not in ("normal", "t"):
            raise ValueError("dist must be 'normal' or 't'")
        if dist == "t" and df <= 2:
            raise ValueError("df must be above 2 (otherwise the variance is infinite)")
        self.n_sims, self.dist, self.df, self.seed = n_sims, dist, df, seed
        self.name = "mc_normal" if dist == "normal" else "mc_t"

    def simulate(self, returns_window):
        """n_sims simulated rupee P&Ls for tomorrow (one number per simulated day)."""
        mu = returns_window.mean().to_numpy()              # 6 average daily returns
        cov = returns_window.cov().to_numpy()              # 6 x 6 covariance matrix
        L = np.linalg.cholesky(cov)                        # lower-triangular, L @ L.T == cov

        rng = np.random.default_rng(self.seed)             # same seed -> same draws every call
        z = rng.standard_normal((self.n_sims, len(mu)))    # independent N(0, 1): rows = sims, cols = assets
        if self.dist == "t":
            w = rng.chisquare(self.df, size=(self.n_sims, 1))   # one chi-squared draw per simulated day
            z = z / np.sqrt(w / (self.df - 2))                  # fat tails, variance still 1
        sim_returns = mu + z @ L.T                         # correlated returns (row = one simulated day)

        h = self.holdings[returns_window.columns].to_numpy()   # rupees per asset, same column order
        return sim_returns @ h                             # rupee P&L of each simulated day

    def predict(self, returns_window):
        pnl = self.simulate(returns_window)
        return -np.quantile(pnl, 1 - self.confidence, method="lower")   # 100th-worst of 10,000

    def predict_es(self, returns_window, confidence=None):
        level = self._level(confidence)
        pnl = self.simulate(returns_window)
        cutoff = np.quantile(pnl, 1 - level, method="lower")
        return -pnl[pnl <= cutoff].mean()                  # average of the simulated tail days
