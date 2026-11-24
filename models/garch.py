"""
models/garch.py — GARCH(1,1) VaR, with two ways to get the tail.

GARCH(1,1) says tomorrow's variance is built from three parts:
    sigma2_tomorrow = omega + alpha x (today's return)^2 + beta x sigma2_today
        omega : a small constant -> pulls volatility towards a long-run level
        alpha : reaction to today's surprise
        beta  : memory of today's volatility
Example (in %): omega 0.02, alpha 0.07, beta 0.89, today's sigma 0.7%:
    calm day (+0.5%)  -> sqrt(0.02 + 0.07 x 0.25 + 0.89 x 0.49) = 0.69%
    crash day (-5%)   -> sqrt(0.02 + 0.07 x 25   + 0.89 x 0.49) = 1.48%  (doubles)
EWMA (Phase 8) is the special case omega = 0, alpha = 1 - lambda, beta = lambda.

omega, alpha and beta are FITTED to the last 500 days (maximum likelihood: the
values that make the returns we saw most probable). rolling_garch() re-fits them
only every 21 trading days (monthly) and, in between, plugs each new return into
the formula with the parameters held FIXED. Re-fitting daily let one extreme
day flip the parameters (9 Mar 2020: alpha 0.00 -> 0.22 -> 0.04 on three days
in a row), so VaR jumped up and then fell 41% in the middle of the crash.

The model works on the PORTFOLIO's daily return (constant exposure means the
weights never change, so the portfolio can be treated as one asset).

Two tails:
    tail="normal" : VaR = 2.326 x sigma_tomorrow (bell curve)
    tail="fhs"    : Filtered Historical Simulation. Divide each past return by
                    its own GARCH sigma that day ("standardised surprises",
                    in sigma units), take the 1%-worst of those, and scale it by
                    sigma_tomorrow. Fat tails come from the data, speed from GARCH.
                    e.g. 5th-worst of 500 surprises = -2.9, sigma = Rs 42,000
                         -> VaR = 2.9 x 42,000 = Rs 1.22 L
"""

import warnings

import numpy as np
import pandas as pd
from arch import arch_model          # the standard Python GARCH library
from scipy.stats import norm

from models.base import VaRModel

# Both GARCH models fit the SAME GARCH to the same window, and predict() and
# predict_es() each need it. Fitting takes ~40 ms, so remember recent fits
# instead of repeating them (a "cache"): key = (first date, last date, days).
_FIT_CACHE = {}
# fits: real optimiser fits; not_converged: fits that failed; fixed: days run with held parameters
FIT_STATS = {"fits": 0, "not_converged": 0, "fixed": 0}


def fit_garch(port_pct, params=None):
    """
    GARCH(1,1) (zero mean, normal likelihood) on daily portfolio returns in %.

    params=None : FIT omega, alpha, beta to this window (the optimiser runs).
    params=(omega, alpha, beta) : do NOT fit; just run the sigma formula through
                  the window with these numbers held fixed (fast, no optimiser).

    Returns a dict: sigma_next (next-day sigma, in %), std_resid (each day's return
    divided by its sigma that day), params (omega, alpha, beta).
    """
    # The same window can be fitted or fixed with different params, so they are part of the key.
    fixed = None if params is None else tuple(float(x) for x in params)
    key = (port_pct.index[0], port_pct.index[-1], len(port_pct), fixed)
    if key in _FIT_CACHE:
        return _FIT_CACHE[key]
    # Keep every result: ~4 KB each, so ~4,500 windows = ~20 MB. This lets the second
    # GARCH model (and every ES call) reuse them instead of recomputing.
    if len(_FIT_CACHE) > 10_000:     # safety limit only
        _FIT_CACHE.clear()

    # mean="Zero": the average daily return is taken as 0, as in EWMA/RiskMetrics.
    model = arch_model(port_pct, mean="Zero", vol="GARCH", p=1, q=1, dist="normal")
    if fixed is None:
        with warnings.catch_warnings():  # arch warns on hard fits; we COUNT those instead
            warnings.simplefilter("ignore")
            res = model.fit(disp="off")  # disp="off" hides the optimiser's progress printout
        FIT_STATS["fits"] += 1
        if res.convergence_flag != 0:    # 0 = the optimiser found a proper answer
            FIT_STATS["not_converged"] += 1
    else:
        res = model.fix(list(fixed))     # same model, parameters given instead of estimated
        FIT_STATS["fixed"] += 1

    out = {
        # forecast(horizon=1): tomorrow's variance; sqrt -> sigma in %
        "sigma_next": float(np.sqrt(res.forecast(horizon=1).variance.iloc[-1, 0])),
        "std_resid": res.std_resid.to_numpy(),      # return_t / sigma_t for each past day
        "params": res.params,                       # omega, alpha[1], beta[1]
    }
    _FIT_CACHE[key] = out
    return out


class GARCHVaR(VaRModel):
    """1-day VaR from a GARCH(1,1) volatility forecast, with a normal or FHS tail."""

    def __init__(self, holdings, confidence, tail="normal"):
        super().__init__(holdings, confidence)
        if tail not in ("normal", "fhs"):
            raise ValueError("tail must be 'normal' or 'fhs'")
        self.tail = tail
        self.name = "garch" if tail == "normal" else "garch_fhs"

    def _port_pct(self, returns_window):
        """Portfolio return in % per day (arch fits best on numbers around 1, not 0.01)."""
        return self.scenario_pnl(returns_window) / self.holdings.sum() * 100

    def fit_params(self, returns_window):
        """Fit omega, alpha, beta to this window (used on re-fit days)."""
        return fit_garch(self._port_pct(returns_window))["params"]

    def _fit(self, returns_window, params=None):
        """Tomorrow's sigma in RUPEES, and the standardised surprises.
        params=None fits this window; otherwise uses the given (held) parameters."""
        fit = fit_garch(self._port_pct(returns_window), params)
        return fit["sigma_next"] / 100 * self.holdings.sum(), fit["std_resid"]   # % -> rupees

    def predict(self, returns_window, params=None):
        sigma, eps = self._fit(returns_window, params)
        if self.tail == "normal":
            return norm.ppf(self.confidence) * sigma                # 2.326 x sigma
        q = np.quantile(eps, 1 - self.confidence, method="lower")   # e.g. 5th-worst of 500
        return -q * sigma

    def predict_es(self, returns_window, confidence=None, params=None):
        level = self._level(confidence)
        sigma, eps = self._fit(returns_window, params)
        if self.tail == "normal":
            return sigma * norm.pdf(norm.ppf(level)) / (1 - level)  # 2.665 x sigma at 99%
        q = np.quantile(eps, 1 - level, method="lower")
        return -eps[eps <= q].mean() * sigma                        # average tail surprise x sigma


def rolling_garch(model, returns, window, refit_every, measure="var", confidence=None):
    """
    Like rolling_var (same dates, same no-look-ahead windows), but GARCH's
    parameters are re-fitted only every `refit_every` days and held fixed between.

    Example with refit_every = 21:
        forecast 1  : FIT omega, alpha, beta on its 500-day window -> keep them
        forecasts 2-21 : same parameters; sigma updated with each new return
        forecast 22 : FIT again, and so on.
    refit_every = 1 re-fits every day (the first version of Phase 9).
    Every GARCH model uses the same schedule, so their fits are shared via the cache.
    """
    if measure not in ("var", "es"):
        raise ValueError("measure must be 'var' or 'es'")
    forecasts, params = {}, None
    for i in range(window, len(returns)):            # same loop as rolling_var
        past = returns.iloc[i - window:i]            # rows i-window ... i-1 (day i excluded)
        if (i - window) % refit_every == 0:          # % = remainder: 0 on days 1, 22, 43, ...
            params = model.fit_params(past)
        if measure == "var":
            forecasts[returns.index[i]] = model.predict(past, params)
        else:
            forecasts[returns.index[i]] = model.predict_es(past, confidence, params)
    name = model.name if measure == "var" else f"{model.name}_es"
    return pd.Series(forecasts, name=name)
