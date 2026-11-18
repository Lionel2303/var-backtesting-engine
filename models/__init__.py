"""
models/ — one file per VaR model, all sharing the VaRModel interface (base.py).

This file lets other code write `from models import HistoricalVaR` instead of
the longer `from models.historical import HistoricalVaR`.
"""

from models.base import VaRModel, rolling_var
from models.historical import HistoricalVaR
from models.parametric import ParametricVaR

__all__ = ["HistoricalVaR", "ParametricVaR", "VaRModel", "rolling_var"]
