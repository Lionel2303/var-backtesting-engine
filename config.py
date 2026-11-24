"""
config.py — every setting the project uses, kept in ONE place.

Why a separate file?
    If you later want a different portfolio or date range, you change it here
    and nothing else. Hard-coding numbers inside functions is how projects
    become impossible to grow — and this project is meant to grow.
"""

# ---------------------------------------------------------------------------
# 1. WHAT WE HOLD
# ---------------------------------------------------------------------------
# Keys   = Yahoo Finance ticker symbols (".NS" = listed on NSE).
# Values = how many rupees we have invested in each, TODAY.
#
# We treat holdings as a fixed rupee amount ("constant exposure"). That means
# every day we pretend we still have Rs 10 lakh in Reliance. Real desks hold a
# number of shares, not rupees, but constant exposure keeps the maths simple
# and is a standard simplification for a first VaR model.

HOLDINGS = {
    "RELIANCE.NS": 1_000_000,   # Reliance Industries  (energy / conglomerate)
    "HDFCBANK.NS": 1_000_000,   # HDFC Bank            (banking)
    "INFY.NS":     1_000_000,   # Infosys              (IT, earns in USD)
    "^NSEI":       1_000_000,   # Nifty 50 index       (the broad market)
    "GOLD_INR":    1_000_000,   # Gold priced in rupees (safe-haven; see DERIVED)
    "USDINR=X":    1_000_000,   # US dollar vs rupee   (see note below)
}

# ---------------------------------------------------------------------------
# 1b. DERIVED ASSETS (built from other tickers instead of downloaded directly)
# ---------------------------------------------------------------------------
# Gold in rupees = world gold price in dollars x rupees per dollar.
#   e.g. $900 per ounce x Rs 48.5 per $ = Rs 43,650 per ounce
# "GC=F" is COMEX gold futures (USD). Why not the Gold ETF (GOLDBEES.NS)?
# Yahoo's GOLDBEES history only starts in Jan 2009, which would cut the
# 2008 crisis out of the whole dataset. GC=F and USDINR=X go back to 2007.
# Trade-off: COMEX closes ~11 hours after NSE, so day-to-day it lines up
# loosely with Indian assets (week-to-week it tracks well).
DERIVED = {
    "GOLD_INR": ("GC=F", "USDINR=X"),   # name -> (ticker A, ticker B); value = A x B
}
# Note on USDINR: the price is "rupees per 1 dollar". If it goes UP, the
# rupee got weaker. Holding Rs 10 lakh of "USDINR" means we effectively own
# dollars — we PROFIT when the rupee weakens. That often happens in a crash,
# so this position tends to cushion losses (a natural hedge).

# Underscores in numbers (1_000_000) are just for readability — Python
# ignores them. 1_000_000 == 1000000.

# ---------------------------------------------------------------------------
# 2. WHICH DATES
# ---------------------------------------------------------------------------
# Starting in 2007 means the 2008 global financial crisis is in our data.
# We need that for Stressed VaR in Phase 3.
START_DATE = "2007-01-01"
END_DATE = None          # None = "up to today"

# ---------------------------------------------------------------------------
# 3. VaR SETTINGS (used from Phase 2 onward)
# ---------------------------------------------------------------------------
CONFIDENCE = 0.99        # 99% — the level banks report under Basel rules
WINDOW = 250             # look back ~1 trading year (about 250 trading days)

# Expected Shortfall (Phase 7). Basel's newer rules (FRTB) use ES at 97.5%
# instead of VaR at 99%. We compute ES at both levels.
ES_CONFIDENCE = 0.975

# Exponential weighting (Phase 8): recent days count more than old ones.
EWMA_LAMBDA = 0.94         # RiskMetrics daily decay: weights halve every ~11 days
RESPONSIVE_LAMBDA = 0.994  # "Responsive VaR" (FRAM reading material): halve every ~115 days
RESPONSIVE_WINDOW = 500    # ...on a 2-year window, as in the reading material

# GARCH(1,1) (Phase 9): parameters are fitted on the last 500 days
# (250 is too few to estimate 3 parameters reliably; 500 also keeps the same
# backtest period as Phase 8).
GARCH_WINDOW = 500
# Re-fit the parameters every 21 trading days (~monthly); in between, hold them
# fixed and only update sigma. 1 = re-fit daily (unstable: see devnotes phase 9).
GARCH_REFIT_EVERY = 21
