"""
data.py — Phase 1: get prices, turn them into returns, turn returns into P&L.

The pipeline:
    prices (Rs per share)  ->  returns (% moves)  ->  P&L (rupees gained/lost)

Everything later (VaR, backtests, reports) only needs the final P&L series
and the returns, so this file is the foundation.
"""

import numpy as np          # numerical maths: logs, arrays
import pandas as pd         # tables (DataFrames) with dates as the index
import yfinance as yf       # free market data from Yahoo Finance


# ---------------------------------------------------------------------------
# STEP 1 — Download prices
# ---------------------------------------------------------------------------
def get_prices(tickers, start, end=None):
    """
    Download daily closing prices for a list of tickers.

    Returns a DataFrame like:
                    RELIANCE.NS   INFY.NS   ...
        2007-01-02      560.1     1010.4
        2007-01-03      565.3     1002.9
    """
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,   # adjusts for splits & dividends (explained below)
        progress=False,     # hides the download progress bar
        threads=False,      # download one ticker at a time (see note below)
    )
    # Why threads=False:
    #   By default yfinance downloads all tickers at the SAME time. They all try
    #   to write to one small cache file, and on Windows one of them can get
    #   "database is locked" and silently come back EMPTY. One at a time is a
    #   few seconds slower but reliable.

    # yfinance returns several columns per ticker (Open, High, Low, Close,
    # Volume). We only need "Close" — the end-of-day price.
    prices = raw["Close"]

    # Fail loudly if any ticker came back with no prices at all.
    # prices.isna()        -> True wherever a price is missing
    # .all()               -> per column: True if EVERY row is missing
    # prices.columns[...]  -> keep only the names of those fully-empty columns
    empty = list(prices.columns[prices.isna().all()])
    if empty:
        # Without this check, one empty column makes dropna() later delete
        # EVERY row, and the script crashes with a confusing IndexError.
        raise RuntimeError(f"No data downloaded for: {empty}. Check the ticker or retry.")

    # Why auto_adjust=True matters:
    #   If a stock splits 1:2, its price halves overnight (Rs 2000 -> Rs 1000)
    #   but nobody actually lost money. Without adjustment that would look
    #   like a -50% crash and wreck our VaR. Adjusted prices rewrite history
    #   so the split doesn't show up as a fake move.
    return prices


# ---------------------------------------------------------------------------
# STEP 1b — Remove data glitches (bad prices that snap straight back)
# ---------------------------------------------------------------------------
GLITCH_WINDOW = 5      # compare each price with the median of 5 days around it
GLITCH_VOL_WINDOW = 61 # "how volatile was the market THEN": ~3 months around the day
GLITCH_K = 11          # flag if more than 11x the local typical daily move away
# Why 11: on this data every confirmed glitch is 12x-322x the local move and
# every real event checked (2008, 2009 election, COVID, 2024 election, Jan-2026
# gold spike) is 10.2x or less. The gap is narrow, so ALWAYS read the printed
# log after refreshing data. See devnotes/phase-1-data.md.


def clean_prices(prices, window=GLITCH_WINDOW, vol_window=GLITCH_VOL_WINDOW, k=GLITCH_K):
    """
    Find prices that are obviously wrong and blank them out (set to NaN).

    Rule: a price is a glitch if it is far from the MEDIAN of the prices
    around it. "Far" means more than k times that asset's typical daily move
    AT THAT TIME (measured over the ~3 months around the day).

    Why the median works:
        Glitch:      33.5, 33.6, 0.34, 0.34, 33.65  -> median 33.5 -> 0.34 is 99% away -> FLAG
        Real crash: 100,  100,   79,   79,   79     -> median 79   -> 79 is 0% away   -> keep
    A real crash STAYS down, so the median moves with it. A glitch snaps back.

    Why "at that time": in a crisis, prices swing 5-10% a day and bounce back.
    Compared with a CALM-period yardstick (~1%/day) a real crisis day looks like
    a glitch. Compared with the crisis's own volatility (~3%/day) it doesn't.

    Returns (cleaned_prices, log) where log is a table of every price removed,
    so each correction can be checked and explained.
    """
    cleaned = prices.copy()        # work on a copy so the original is untouched
    log_rows = []                  # one entry per removed price

    for ticker in prices.columns:  # check each asset separately
        # Use only the days this asset actually traded (drop holiday gaps),
        # otherwise the gaps would distort the "5 days around it".
        s = prices[ticker].dropna()

        # rolling(window, center=True) looks at 2 days before, the day itself,
        # and 2 days after. .median() takes the middle value of those 5.
        # min_periods=3 lets the first/last days use fewer neighbours.
        median = s.rolling(window, center=True, min_periods=3).median()

        # How far is each price from its local median, as a fraction?
        # e.g. 0.34 vs 33.5 -> |0.34/33.5 - 1| = 0.99 (99% away)
        distance = (s / median - 1).abs()

        # "Typical daily move" for this asset AROUND each day:
        #   s.pct_change().abs()  -> size of each daily % change
        #   .rolling(61, center=True).median() -> middle value over ~3 months
        # Using the median (not the average) means a glitch can't inflate it.
        # Calm USD/INR: ~0.1-0.3%/day. Shares in March 2020: ~3%/day.
        typical_move = (s.pct_change().abs()
                        .rolling(vol_window, center=True, min_periods=20).median())

        # A glitch: more than k times the local typical move away from the median.
        is_glitch = distance > k * typical_move

        for date in s.index[is_glitch]:          # record every flagged price
            log_rows.append({
                "date": date.date(),
                "ticker": ticker,
                "bad_price": round(s[date], 4),
                "local_median": round(median[date], 4),
                "distance": f"{distance[date]:.1%}",
                "x_local_move": round(distance[date] / typical_move[date], 1),
            })
            cleaned.loc[date, ticker] = np.nan   # blank it; ffill fixes it later

    log = pd.DataFrame(log_rows)   # turn the list of records into a table
    return cleaned, log


# ---------------------------------------------------------------------------
# STEP 1c — Derived assets (e.g. gold in rupees = gold in $ x rupees per $)
# ---------------------------------------------------------------------------
def tickers_to_download(holdings, derived):
    """
    List the Yahoo tickers we must download.

    Real holdings are downloaded directly. A derived holding (like GOLD_INR)
    is not a Yahoo ticker, so we download its ingredients instead.
    e.g. holdings has GOLD_INR, derived says GOLD_INR = GC=F x USDINR=X
         -> download GC=F and USDINR=X (USDINR=X only once).
    """
    tickers = []
    for name in holdings:                     # go through every holding
        parts = derived.get(name, (name,))    # derived -> its 2 ingredients; real -> itself
        for t in parts:
            if t not in tickers:              # avoid downloading the same ticker twice
                tickers.append(t)
    return tickers


def add_derived(prices, derived):
    """
    Add a column for each derived asset: value = ticker A x ticker B.

    Runs AFTER clean_prices, so a glitch in an ingredient (e.g. a bad USD/INR
    print) is removed before it can leak into the derived price.
    """
    out = prices.copy()
    for name, (a, b) in derived.items():
        # ffill() first: COMEX and the forex market have different holidays,
        # so on some days one ingredient is missing. Carrying the last price
        # forward means "no new price that day" instead of a blank result.
        filled = prices[[a, b]].ffill()
        out[name] = filled[a] * filled[b]     # e.g. 900 $ x 48.5 Rs/$ = 43,650 Rs
    return out


# ---------------------------------------------------------------------------
# STEP 2 — Clean prices and compute returns
# ---------------------------------------------------------------------------
def get_returns(prices, kind="log"):
    """
    Turn a price table into a table of daily returns.

    kind="log"    -> ln(P_today / P_yesterday)
    kind="simple" -> (P_today - P_yesterday) / P_yesterday
    """
    # --- Cleaning -----------------------------------------------------------
    # Different markets close on different holidays. On Diwali, NSE is shut
    # but the forex market may trade, so the NSE columns show NaN (missing).
    #
    # ffill() = "forward fill": copy yesterday's price into today's gap.
    # Meaning: "the market was closed, so the price didn't change" -> return
    # of 0 that day. That's the honest assumption — no trading, no move.
    prices = prices.ffill()

    # The first rows can still be NaN (e.g. a ticker that started trading
    # later than 2007). dropna() removes any row with a missing value, so
    # every row we keep has a price for EVERY asset.
    prices = prices.dropna()

    # --- Returns ------------------------------------------------------------
    # prices.shift(1) slides every column down one row, so on each date we
    # can see "yesterday's price" next to "today's price".
    #
    #   date    price   shift(1)
    #   Mon     100     NaN
    #   Tue     102     100      -> simple return = 102/100 - 1 = +2%
    #   Wed      99     102      -> simple return =  99/102 - 1 = -2.94%
    if kind == "log":
        returns = np.log(prices / prices.shift(1))
    elif kind == "simple":
        returns = prices / prices.shift(1) - 1
    else:
        raise ValueError("kind must be 'log' or 'simple'")

    # The very first row has no "yesterday", so its return is NaN. Drop it.
    return returns.dropna()


# ---------------------------------------------------------------------------
# STEP 3 — Turn returns into rupee P&L for the whole portfolio
# ---------------------------------------------------------------------------
def get_portfolio_pnl(simple_returns, holdings):
    """
    Daily profit/loss of the whole portfolio, in rupees.

    For each asset:  P&L = rupees held  x  that day's SIMPLE return
    Portfolio P&L    = sum of every asset's P&L that day

    Example: Rs 10,00,000 in Infosys, Infosys falls 2%
             -> P&L = 10,00,000 x (-0.02) = -Rs 20,000
    """
    # Turn the holdings dict into a pandas Series, ordered to match the
    # columns of the returns table, so each return lines up with its holding.
    weights = pd.Series(holdings)[simple_returns.columns]

    # Multiply each column by its holding (row by row), then add across the
    # row (axis=1 means "sum across columns").
    pnl_by_asset = simple_returns * weights
    pnl = pnl_by_asset.sum(axis=1)
    pnl.name = "portfolio_pnl"
    return pnl


# ---------------------------------------------------------------------------
# STEP 4 — The whole pipeline in one call (used by every later phase)
# ---------------------------------------------------------------------------
def load_data():
    """
    Run the full Phase 1 pipeline and return everything later phases need.

    Returns a dict with:
        "returns"     : daily SIMPLE returns, one column per asset we hold
        "pnl"         : daily portfolio P&L in rupees
        "glitch_log"  : table of every bad price removed
        "first_dates" : first date each downloaded ticker has a price
    """
    # Imported here (not at the top) so data.py's functions can be used with
    # any settings; the pipeline itself reads the project's config.py.
    from config import DERIVED, END_DATE, HOLDINGS, START_DATE

    # Download real holdings + the ingredients of derived ones (GC=F for gold).
    prices = get_prices(tickers_to_download(HOLDINGS, DERIVED), START_DATE, END_DATE)

    # Where each ticker's history starts (dropna later keeps the LATEST start).
    first_dates = {t: prices[t].first_valid_index().date() for t in prices.columns}

    # Remove glitches (every correction is recorded in glitch_log).
    prices, glitch_log = clean_prices(prices)

    # Build GOLD_INR from its cleaned ingredients, then keep ONLY the assets we
    # hold (GC=F was just an ingredient; we don't hold it on its own).
    prices = add_derived(prices, DERIVED)[list(HOLDINGS)]

    returns = get_returns(prices, kind="simple")
    pnl = get_portfolio_pnl(returns, HOLDINGS)
    return {"returns": returns, "pnl": pnl, "glitch_log": glitch_log,
            "first_dates": first_dates}


# ---------------------------------------------------------------------------
# Run this file directly to try it:   python data.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # "if __name__ == '__main__'" means: only run this block when you run
    # THIS file directly — not when another file does "import data".
    from config import HOLDINGS

    d = load_data()
    simple, pnl, glitch_log = d["returns"], d["pnl"], d["glitch_log"]

    print("First available price per asset:")
    for ticker, first in d["first_dates"].items():
        print(f"  {ticker:12s} {first}")
    print()

    print(f"Glitches removed: {len(glitch_log)}")
    if len(glitch_log):
        print(glitch_log.to_string(index=False))
    print()

    print(f"Data from {pnl.index[0].date()} to {pnl.index[-1].date()} "
          f"({len(pnl)} trading days)\n")
    print(pnl.describe().round(0))

    # Worst 5 days, with each asset's share of the loss, so we can see which
    # asset drove it (the breach report in Phase 5 needs the same idea).
    worst = pnl.nsmallest(5).index
    by_asset = simple.loc[worst] * pd.Series(HOLDINGS)[simple.columns]
    by_asset["TOTAL"] = pnl.loc[worst]
    print("\nWorst 5 days (Rs, per asset):")
    print(by_asset.round(0).to_string())
