"""
models/weighted_historical.py — "Responsive VaR": exponentially weighted
historical simulation (FRAM VaR reading material, section 4).

Same idea as historical simulation (replay past days on today's holdings), but
recent days count MORE. With lam = 0.994 on 500 days, yesterday's weight is
0.63% and a day 115 days ago has half that (equal weights would be 0.2% each).

VaR: sort the replayed P&Ls from worst to best, add up their weights, and stop
at the first day where the running total reaches 1%. That day's loss is VaR.
ES:  the WEIGHTED average of the days up to and including that point.
"""

import numpy as np

from models.base import VaRModel, exp_weights


class WeightedHistoricalVaR(VaRModel):
    """Historical simulation with exponentially decaying weights on past days."""

    name = "weighted_hs"

    def __init__(self, holdings, confidence, lam):
        super().__init__(holdings, confidence)   # the parent stores holdings and confidence
        self.lam = lam                            # decay factor, e.g. 0.994

    def _tail(self, returns_window, level):
        """
        The worst days whose weights add up to (just past) 1 - level, with their weights.

        Example, 5 days, weights already normalised, level 0.80 (so 20% tail):
            sorted P&L: -5, -3, -1, +2, +4   weights: 0.10, 0.15, 0.30, 0.25, 0.20
            running total: 0.10, 0.25 -> reaches 0.20 at the 2nd day
            -> tail = (-5, -3), VaR = 3, ES = (0.10x5 + 0.15x3) / 0.25 = 3.8
        """
        pnl = self.scenario_pnl(returns_window).to_numpy()   # one replayed P&L per past day
        w = exp_weights(len(pnl), self.lam)                  # same order as pnl (oldest first)
        order = np.argsort(pnl)                    # positions that sort P&L from worst to best
        pnl_sorted, w_sorted = pnl[order], w[order]  # keep each P&L paired with ITS weight
        running = np.cumsum(w_sorted)              # running total of weights: 0.10, 0.25, ...
        # searchsorted: first position where the running total reaches 1 - level.
        # (The tiny 1e-12 stops rounding errors, e.g. 0.00999999, from skipping a day.)
        k = np.searchsorted(running, (1 - level) - 1e-12)
        return pnl_sorted[:k + 1], w_sorted[:k + 1]

    def predict(self, returns_window):
        tail_pnl, _ = self._tail(returns_window, self.confidence)
        return -tail_pnl[-1]              # the last (least bad) tail day = the VaR point

    def predict_es(self, returns_window, confidence=None):
        tail_pnl, tail_w = self._tail(returns_window, self._level(confidence))
        return -(tail_pnl @ tail_w) / tail_w.sum()   # weighted average tail loss
