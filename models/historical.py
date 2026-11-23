"""
models/historical.py — Historical Simulation VaR.

Idea: "If one of the last 250 days happened again tomorrow, what would we lose?"
Replay each past day's returns on today's holdings, sort the 250 P&Ls, and read
off the loss at the worst-1% point. No assumption about the SHAPE of returns
(no bell curve): fat tails in the data show up automatically.
"""

import numpy as np   # np.quantile picks a value at a given position in sorted data

from models.base import VaRModel


class HistoricalVaR(VaRModel):
    """1-day VaR from the empirical distribution of past P&L."""

    name = "historical"

    def predict(self, returns_window):
        # One "what if this day repeated" P&L per past day (250 numbers).
        pnl = self.scenario_pnl(returns_window)

        # The 1% quantile = the P&L that only 1% of past days were worse than.
        # With 250 days, 1% = 2.5 days. method="lower" means: sort P&Ls from
        # worst to best, position 0.01 x (250 - 1) = 2.49, round DOWN to 2,
        # i.e. the 3rd-worst day (positions start at 0). Rounding toward the
        # worse side is the cautious choice.
        #   e.g. sorted P&L: -3.1L, -2.4L, -1.9L, -1.5L, ...  -> picks -1.9L
        worst_1pct = np.quantile(pnl, 1 - self.confidence, method="lower")

        # VaR is reported as a positive loss: -(-1.9 lakh) = 1.9 lakh.
        return -worst_1pct

    def predict_es(self, returns_window, confidence=None):
        """
        Expected Shortfall: the average of every replayed day at or beyond the
        VaR point.

        99%, 250 days: VaR point = 3rd-worst -> ES = average of the 3 worst.
            e.g. -4.0L, -2.5L, -1.5L -> VaR 1.5L, ES (4.0 + 2.5 + 1.5) / 3 = 2.67L
        97.5%: position 0.025 x 249 = 6.2 -> 7th-worst -> ES = average of the 7 worst.
        """
        level = self._level(confidence)
        pnl = self.scenario_pnl(returns_window)
        cutoff = np.quantile(pnl, 1 - level, method="lower")   # the VaR point (same rule as predict)
        # pnl[pnl <= cutoff] keeps only the days at or below the cutoff
        # (a True/False filter, called "boolean indexing").
        tail = pnl[pnl <= cutoff]
        return -tail.mean()                                    # average tail loss, as a positive number
