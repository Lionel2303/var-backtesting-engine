"""
models/ewma.py — EWMA (RiskMetrics) parametric VaR.

Same bell-curve formula as parametric VaR (VaR = z x sigma), but sigma is built
from an EXPONENTIALLY WEIGHTED covariance matrix: yesterday counts most, and a
day's weight halves about every 11 days (lam = 0.94, the RiskMetrics value for
daily data).

Weights with lam = 0.94: yesterday 6.0%, 10 days ago 3.2%, 50 days ago 0.3%,
100 days ago 0.01%. Days older than ~250 have weight ~0, so a 250-day window is
enough.

RiskMetrics convention: the average daily return is taken as 0 (over one day it
is tiny next to sigma, and estimating it adds noise), so VaR = z x sigma.
"""

import numpy as np
from scipy.stats import norm

from models.base import VaRModel, exp_weights


class EWMAVaR(VaRModel):
    """Parametric 1-day VaR with exponentially weighted (RiskMetrics) volatility."""

    name = "ewma"

    def __init__(self, holdings, confidence, lam):
        super().__init__(holdings, confidence)
        self.lam = lam                            # decay factor, e.g. 0.94

    def _sigma(self, returns_window):
        """Portfolio standard deviation in rupees from the EWMA covariance matrix."""
        r = returns_window.to_numpy()             # rows = days (oldest first), columns = assets
        w = exp_weights(len(r), self.lam)         # one weight per day, summing to 1
        # Weighted covariance with zero mean: sum over days of weight x r_day x r_day'.
        # (r * w[:, None]) multiplies each day's row by that day's weight;
        # "[:, None]" turns the weights into a column so each row gets its own weight.
        cov = (r * w[:, None]).T @ r              # 6 x 6 matrix
        h = self.holdings[returns_window.columns].to_numpy()   # rupees held, same order
        return np.sqrt(h @ cov @ h)               # sqrt(w' cov w), as in parametric.py

    def predict(self, returns_window):
        return norm.ppf(self.confidence) * self._sigma(returns_window)   # 2.326 x sigma

    def predict_es(self, returns_window, confidence=None):
        level = self._level(confidence)
        z = norm.ppf(level)
        return self._sigma(returns_window) * norm.pdf(z) / (1 - level)  # 2.665 x sigma at 99%
