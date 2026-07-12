"""Reusable research and backtesting helpers for this quant lab."""

from .backtester import BacktestEngine, run_backtest
from .data import fetch_rqdata_price, load_csv_price, normalize_price_frame
from .metrics import calculate_performance
from .optimize import optimize_ma_cross, optimize_turtle_breakout
from .rqalpha_runner import run_rqalpha_ma_cross, run_rqalpha_strategy, run_rqalpha_turtle_breakout
from .schemas import BacktestConfig, BacktestResult, Trade
from .strategies import MACrossStrategy, Strategy, TurtleBreakoutStrategy

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "MACrossStrategy",
    "Strategy",
    "TurtleBreakoutStrategy",
    "Trade",
    "calculate_performance",
    "fetch_rqdata_price",
    "load_csv_price",
    "normalize_price_frame",
    "optimize_ma_cross",
    "optimize_turtle_breakout",
    "run_backtest",
    "run_rqalpha_ma_cross",
    "run_rqalpha_strategy",
    "run_rqalpha_turtle_breakout",
]
