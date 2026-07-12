from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").rolling(window=window, min_periods=window).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    high_values = pd.to_numeric(high, errors="coerce")
    low_values = pd.to_numeric(low, errors="coerce")
    close_values = pd.to_numeric(close, errors="coerce")
    prev_close = close_values.shift(1)
    ranges = pd.concat(
        [
            high_values - low_values,
            (high_values - prev_close).abs(),
            (low_values - prev_close).abs(),
        ],
        axis=1,
    )
    true_range = ranges.max(axis=1)
    return true_range.rolling(window=window, min_periods=window).mean()


def returns_from_equity(equity: pd.Series) -> pd.Series:
    return pd.to_numeric(equity, errors="coerce").pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def drawdown_series(equity: pd.Series) -> pd.Series:
    values = pd.to_numeric(equity, errors="coerce")
    peak = values.cummax()
    return values / peak - 1


def max_drawdown(equity: pd.Series) -> float:
    dd = drawdown_series(equity)
    return float(dd.min()) if len(dd) else 0.0


def annualized_return(total_return: float, periods: int, periods_per_year: int) -> float:
    if periods <= 0:
        return 0.0
    base = 1 + float(total_return)
    if base <= 0:
        return -1.0
    return float(base ** (periods_per_year / periods) - 1)
