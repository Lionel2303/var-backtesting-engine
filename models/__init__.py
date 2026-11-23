"""
models/ — one file per VaR model, all sharing the VaRModel interface (base.py).

This file lets other code write `from models import HistoricalVaR` instead of
the longer `from models.historical import HistoricalVaR`.
"""

from models.base import VaRModel, exp_weights, rolling_var, weighted_age
from models.ewma import EWMAVaR
from models.historical import HistoricalVaR
from models.parametric import ParametricVaR
from models.weighted_historical import WeightedHistoricalVaR

__all__ = ["EWMAVaR", "HistoricalVaR", "ParametricVaR", "VaRModel", "WeightedHistoricalVaR",
           "exp_weights", "rolling_var", "weighted_age"]
