"""
models/base.py — the common "shape" every VaR model must have, plus the
rolling engine that runs any model day by day.

Why a shared shape (a "base class")?
    Historical, parametric, and later GARCH or ML models all answer the same
    question: "given the past N days of returns, what is tomorrow's VaR?"
    If every model has the same predict() method, the backtest and report code
    can use ANY model without changes. New model = new file, nothing else.
"""

import numpy as np    # arrays (for the exponential weights)
import pandas as pd   # tables with dates as the index


def exp_weights(n, lam):
    """
    Exponentially decaying weights for n days, OLDEST first, summing to 1.

    The newest day gets lam^0 = 1, the day before lam^1, then lam^2, ... and
    all are divided by their total so they add up to 1 (normalised weights).
    e.g. n = 3, lam = 0.5: raw 0.25, 0.5, 1 -> normalised 0.14, 0.29, 0.57
    lam = 1 gives equal weights (1/n each): plain historical simulation.
    """
    # np.arange(n - 1, -1, -1) = n-1, n-2, ..., 0 = "days back" for each row
    # (row 0 is the oldest, n-1 days back; the last row is today, 0 days back).
    raw = lam ** np.arange(n - 1, -1, -1)
    return raw / raw.sum()


def weighted_age(n, lam):
    """
    Weighted average age of the data in days (the reading material's "WAOP").
    Basel's rule: with weighting, this must be at least ~6 months (~130 days).
    e.g. lam = 1, n = 500 -> 249.5 days (equal weights: the middle of the window).
    """
    ages = np.arange(n - 1, -1, -1)            # days back, oldest first (same order as exp_weights)
    return float(ages @ exp_weights(n, lam))   # sum of age x weight


class VaRModel:
    """
    Parent class for every VaR model.

    Create a model with:
        holdings   : dict of ticker -> rupees held (e.g. {"INFY.NS": 1_000_000, ...})
        confidence : e.g. 0.99 for 99% VaR

    Every model must implement predict(returns_window):
        returns_window : table of past daily SIMPLE returns, one row per day,
                         one column per asset (e.g. the last 250 days)
        returns        : tomorrow's 1-day VaR in rupees, as a POSITIVE number
                         meaning "a loss of this many rupees"
    """

    name = "base"   # each model overrides this with its own short name

    def __init__(self, holdings, confidence):
        # Store holdings as a pandas Series (a labelled list of numbers) so we
        # can line them up with the return columns by ticker name.
        self.holdings = pd.Series(holdings, dtype=float)
        self.confidence = confidence   # 0.99 -> look at the worst 1% of outcomes

    def scenario_pnl(self, returns_window):
        """
        "If each past day's returns happened again with TODAY's holdings,
        what would the portfolio P&L be?" One rupee number per past day.

        Example (one past day, 2 assets):
            Reliance -2% on Rs 10 lakh = -20,000
            Gold     +1% on Rs 10 lakh = +10,000   -> scenario P&L = -10,000
        """
        # Put the holdings in the same order as the return columns.
        weights = self.holdings[returns_window.columns]
        # "@" is matrix multiplication: for every row (day) it computes
        # sum(return of each asset x rupees in that asset) -> one P&L per day.
        return returns_window @ weights

    def predict(self, returns_window):
        """Each specific model must replace this with its own VaR formula."""
        raise NotImplementedError("each VaR model must define predict()")

    def predict_es(self, returns_window, confidence=None):
        """
        Expected Shortfall: the AVERAGE loss on days worse than VaR (positive rupees).
        confidence=None means "use the model's own level" (0.99).
        Each specific model must replace this with its own ES formula.
        """
        raise NotImplementedError("each VaR model must define predict_es()")

    def _level(self, confidence):
        """The confidence to use: the one asked for, or the model's own (0.99)."""
        return self.confidence if confidence is None else confidence


def rolling_var(model, returns, window, measure="var", confidence=None):
    """
    Run a model day by day through history ("rolling window").

    measure    : "var" -> model.predict (VaR, the model's own confidence)
                 "es"  -> model.predict_es (Expected Shortfall at `confidence`)
    The Series is named after the model ("historical") for VaR, and
    "<model>_es" for ES, so the two can sit side by side in one table.

    For each day t, the forecast uses ONLY the `window` days BEFORE t
    (t-window ... t-1), never day t itself. That is exactly like keeping test
    data out of training in ML: we forecast day t, then (in Phase 4) check it
    against what really happened on day t.

    Returns a Series of VaR values indexed by the day each forecast is FOR.

    Example with window=3 and days d1..d5:
        forecast for d4 uses d1, d2, d3
        forecast for d5 uses d2, d3, d4
    """
    if measure == "var":
        forecast, name = model.predict, model.name
    elif measure == "es":
        # lambda = a tiny unnamed function: "given past, call predict_es(past, confidence)"
        forecast, name = (lambda past: model.predict_es(past, confidence)), f"{model.name}_es"
    else:
        raise ValueError("measure must be 'var' or 'es'")

    forecasts = {}                                  # date -> forecast in rupees
    for i in range(window, len(returns)):           # first forecastable day is row `window`
        past = returns.iloc[i - window:i]           # rows i-window ... i-1 (day i excluded)
        forecasts[returns.index[i]] = forecast(past)
    return pd.Series(forecasts, name=name)
