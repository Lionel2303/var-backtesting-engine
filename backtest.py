"""
backtest.py — Phase 4: check whether VaR forecasts were right.

A 99% VaR claims "only 1% of days will lose more than me". Backtesting counts
the days that did (BREACHES) and asks whether there were too many.

Tools:
    find_breaches       : which days lost more than the VaR forecast
    kupiec_pof          : statistical test, "is the breach rate really 1%?"
    traffic_light       : Basel zone from breaches in the last 250 days
    rolling_zone        : the traffic-light zone for every day in history

ML link: this is evaluating a model on its test set. Each VaR forecast was
built only from earlier days; the actual P&L that day is the unseen answer.
"""

import pandas as pd
from scipy.special import xlogy   # x * log(y), defined as 0 when x = 0
from scipy.stats import chi2      # chi-squared distribution (for the test's p-value)


def find_breaches(var, pnl):
    """
    True on days when the loss was bigger than the VaR forecast.

    var : forecast VaR per day (positive rupees, e.g. 2,94,000)
    pnl : actual P&L per day (negative = loss, e.g. -4,19,227)

    A breach is pnl < -var.  Example: -4,19,227 < -2,94,000 -> True.
    """
    pnl = pnl.reindex(var.index)        # line the two series up by date
    return pnl < -var


def kupiec_pof(n_breaches, n_days, p=0.01):
    """
    Kupiec "proportion of failures" test.

    Question: if the model were right (true breach rate = p = 1%), how likely is
    it to see a breach rate as far from 1% as the one we saw?

    It compares two likelihoods (how well each rate explains what we saw):
        L(model)    using the claimed rate p      = 0.01
        L(observed) using the observed rate p_hat = n_breaches / n_days
    LR = -2 x ln( L(model) / L(observed) )   -> bigger LR = worse fit for 1%.
    If the model is right, LR follows a chi-squared distribution with 1 degree
    of freedom, which turns LR into a p-value.

    Worked example, 250 days:
        3 breaches  -> LR = 0.09,  p-value = 0.76    -> consistent with 1%: PASS
        10 breaches -> LR = 12.96, p-value = 0.0003  -> far too many: REJECT
    Rule: reject the model if p-value < 0.05 (equivalently LR > 3.84).

    Returns dict with LR, p_value and verdict.
    """
    x, t = n_breaches, n_days
    p_hat = x / t                                   # observed breach rate
    # log-likelihood of the data under a breach rate r:
    #   (t - x) x ln(1 - r) + x x ln(r)
    # xlogy(a, b) = a x ln(b), but returns 0 when a = 0 (no breaches), avoiding ln(0).
    ll_model = xlogy(t - x, 1 - p) + xlogy(x, p)
    ll_observed = xlogy(t - x, 1 - p_hat) + xlogy(x, p_hat)
    lr = -2 * (ll_model - ll_observed)
    p_value = chi2.sf(lr, df=1)                     # sf = 1 - cdf = "chance of an LR this big or bigger"
    return {"LR": lr, "p_value": p_value, "verdict": "pass" if p_value >= 0.05 else "REJECT"}


def traffic_light(n_breaches_250):
    """Basel zone from the number of breaches in the last 250 days."""
    if n_breaches_250 <= 4:
        return "green"     # 0-4: consistent with a correct 99% model
    if n_breaches_250 <= 9:
        return "amber"     # 5-9: suspicious; regulators raise the capital multiplier
    return "red"           # 10+: the model is almost certainly wrong


def es_severity(breaches, es, pnl):
    """
    Is ES the right SIZE? On the days VaR was breached, compare the average
    actual loss with the average ES forecast for those days.

    If ES is right, the two averages should be about equal (ratio ~ 1.0).
    Ratio > 1 -> losses beyond VaR were bigger than ES promised (ES too low).
    Example: 3 breach days, losses 2.0L, 3.0L, 4.0L (avg 3.0L), ES forecasts
             2.0L, 2.5L, 3.0L (avg 2.5L) -> ratio 1.2 -> ES 20% too small.

    This is a simple check, not a formal statistical test (formal ES backtests,
    e.g. Acerbi-Szekely, are a later item).
    """
    pnl = pnl.reindex(es.index)
    loss = -pnl[breaches]                 # actual losses on breach days (positive)
    forecast = es[breaches]               # what ES said for those same days
    return {"breach_days": int(breaches.sum()), "avg_loss": loss.mean(),
            "avg_es": forecast.mean(), "ratio": loss.mean() / forecast.mean()}


def rolling_zone(breaches, window=250):
    """
    For every day, count breaches in the 250 days ending that day and give its
    traffic-light zone. The first 249 days have no full window, so they are dropped.
    """
    counts = breaches.astype(int).rolling(window).sum().dropna().astype(int)
    return pd.DataFrame({"breaches_250d": counts, "zone": counts.map(traffic_light)})
