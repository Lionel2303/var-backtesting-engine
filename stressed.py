"""
stressed.py — Phase 3: Stressed VaR (SVaR).

Normal VaR uses the LAST 250 days, so it forgets a crisis once it is 251 days
old (the ghost effect, Phase 2). Stressed VaR uses a FIXED 250-day crisis
window instead: "what would our VaR be if the worst year happened again, with
today's positions?"

How the window is chosen (the Basel 2.5 idea): pick the 12-month period that
gives the HIGHEST VaR for the current portfolio. We already have every rolling
VaR forecast from Phase 2, so the stressed window is simply the 250 days that
the highest forecast was trained on.
"""


def find_stress_window(selector_var, returns, window, start=None, end=None):
    """
    Find the 250-day window behind the highest VaR forecast in a period.

    selector_var : Series of rolling VaR forecasts (date -> rupees), e.g. the
                   historical-simulation VaR from Phase 2
    returns      : the full table of daily returns (the forecasts were made from it)
    window       : 250
    start, end   : only consider forecast dates in this period
                   (e.g. "2008-09-01", "2009-06-30"); None = no limit

    Returns a dict with the peak forecast date, its VaR, and the window's
    returns, first date and last date.

    Example: if the highest forecast in the period is for 24 Mar 2020, the
    stressed window is the 250 trading days just BEFORE 24 Mar 2020, i.e. the
    exact days that forecast was built from.
    """
    period = selector_var.loc[start:end]            # forecasts dated inside the period
    peak_date = period.idxmax()                     # the day with the highest VaR forecast
    i = returns.index.get_loc(peak_date)            # that day's row number in the returns table
    window_returns = returns.iloc[i - window:i]     # the 250 rows before it (same slice as rolling_var)
    return {
        "peak_forecast_date": peak_date,
        "peak_var": period.max(),
        "start": window_returns.index[0],
        "end": window_returns.index[-1],
        "returns": window_returns,
    }


def stressed_var(models, window_returns):
    """
    Stressed VaR from every model on one fixed crisis window.

    Because every model has the same predict() method (Phase 2), this works for
    historical, parametric, and any model added later, with no changes here.
    Returns a dict: model name -> SVaR in rupees.
    """
    return {m.name: m.predict(window_returns) for m in models}
