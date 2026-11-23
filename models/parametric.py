"""
models/parametric.py — Parametric (variance-covariance) VaR.

Idea: assume daily portfolio P&L follows a normal (bell-curve) distribution.
Then VaR only needs two numbers from the past 250 days:
    mu    = average daily P&L (rupees)
    sigma = standard deviation of daily P&L (rupees)
and VaR(99%) = z x sigma - mu, where z = 2.326 (99% of a bell curve lies
below 2.326 standard deviations).

sigma comes from the covariance matrix: how much each asset moves AND how the
assets move together. Assets that don't move together cancel out part of each
other's risk (diversification).
"""

import numpy as np          # matrix maths (@) and square root
from scipy.stats import norm  # the normal distribution (bell curve)

from models.base import VaRModel


class ParametricVaR(VaRModel):
    """1-day VaR assuming normally distributed portfolio P&L."""

    name = "parametric"

    def predict(self, returns_window):
        mu, sigma = self._mu_sigma(returns_window)

        # z for 99%: norm.ppf(0.99) = 2.326 ("ppf" = inverse of the bell-curve
        # cumulative probability: which z leaves 99% of the curve below it?).
        z = norm.ppf(self.confidence)

        # The worst-1% point of a bell curve centred on mu is mu - z x sigma.
        # VaR is reported as a positive loss, so flip the sign.
        return z * sigma - mu

    def predict_es(self, returns_window, confidence=None):
        """
        Expected Shortfall under a bell curve: ES = sigma x phi(z) / (1 - level) - mu

        phi(z) = norm.pdf(z) = the HEIGHT of the bell curve at z.
        99%:   z = 2.326, phi = 0.0267 -> ES = 0.0267 / 0.01  = 2.665 sigma (VaR = 2.326 sigma)
        97.5%: z = 1.960, phi = 0.0584 -> ES = 0.0584 / 0.025 = 2.338 sigma
        e.g. sigma = Rs 50,000, mu = 0: VaR99 = Rs 1.16 L, ES99 = Rs 1.33 L
        """
        level = self._level(confidence)
        mu, sigma = self._mu_sigma(returns_window)
        z = norm.ppf(level)
        return sigma * norm.pdf(z) / (1 - level) - mu

    def _mu_sigma(self, returns_window):
        """Average daily rupee P&L (mu) and its standard deviation (sigma), from the covariance matrix."""
        # Rupees held per asset, in the same order as the return columns.
        w = self.holdings[returns_window.columns].to_numpy()

        # Covariance matrix (6 x 6 here): diagonal = each asset's variance,
        # off-diagonal = how pairs of assets move together.
        cov = returns_window.cov().to_numpy()

        # Portfolio variance in rupees^2 = w' x cov x w ("w transpose cov w").
        # Two-asset example, Rs 10 lakh each, daily vol 2% and 1%, correlation 0.3:
        #   var = (10L x 2%)^2 + (10L x 1%)^2 + 2 x 0.3 x (10L x 2%) x (10L x 1%)
        #       = 20,000^2 + 10,000^2 + 2 x 0.3 x 20,000 x 10,000
        #       = 62 crore  -> sigma = sqrt(62 crore) = Rs 24,900
        #   (without diversification it would be 20,000 + 10,000 = Rs 30,000)
        sigma = np.sqrt(w @ cov @ w)

        # Average daily rupee P&L over the window (usually small vs sigma).
        mu = returns_window.mean().to_numpy() @ w
        return mu, sigma
