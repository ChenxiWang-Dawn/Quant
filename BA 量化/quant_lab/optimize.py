from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd

from .backtester import run_backtest
from .schemas import BacktestConfig


def optimize_ma_cross(
    price: pd.DataFrame,
    base_config: BacktestConfig,
    fast_values: Iterable[int],
    slow_values: Iterable[int],
    objective: str = "sharpe",
) -> pd.DataFrame:
    rows: List[Dict] = []
    for fast in fast_values:
        for slow in slow_values:
            fast = int(fast)
            slow = int(slow)
            if fast <= 0 or slow <= 0 or fast >= slow:
                continue
            config = BacktestConfig(
                symbol=base_config.symbol,
                start_date=base_config.start_date,
                end_date=base_config.end_date,
                strategy_name="ma_cross",
                strategy_params={
                    **base_config.strategy_params,
                    "fast_window": fast,
                    "slow_window": slow,
                    "target_weight": base_config.target_weight,
                },
                benchmark=base_config.benchmark,
                frequency=base_config.frequency,
                adjust_type=base_config.adjust_type,
                initial_cash=base_config.initial_cash,
                commission_rate=base_config.commission_rate,
                slippage_rate=base_config.slippage_rate,
                min_commission=base_config.min_commission,
                trade_price=base_config.trade_price,
                target_weight=base_config.target_weight,
                allow_short=base_config.allow_short,
                lot_size=base_config.lot_size,
                risk_free_rate=base_config.risk_free_rate,
                periods_per_year=base_config.periods_per_year,
            )
            try:
                result = run_backtest(price, config)
                metrics = result.metrics
                score = score_metrics(metrics, objective)
                rows.append(
                    {
                        "fast": fast,
                        "slow": slow,
                        "score": score,
                        "totalReturn": metrics.get("totalReturn", 0.0),
                        "annualizedReturn": metrics.get("annualizedReturn", 0.0),
                        "maxDrawdown": metrics.get("maxDrawdown", 0.0),
                        "sharpe": metrics.get("sharpe", 0.0),
                        "calmar": metrics.get("calmar", 0.0),
                        "tradeCount": metrics.get("tradeCount", 0),
                        "winRate": metrics.get("winRate", 0.0),
                    }
                )
            except Exception as exc:
                rows.append({"fast": fast, "slow": slow, "score": -999.0, "error": str(exc)})
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("score", ascending=False).reset_index(drop=True)
        frame.insert(0, "rank", range(1, len(frame) + 1))
    return frame


def optimize_turtle_breakout(
    price: pd.DataFrame,
    base_config: BacktestConfig,
    entry_values: Iterable[int],
    exit_values: Iterable[int],
    atr_window: int = 20,
    stop_atr_multiplier: float = 2.0,
    objective: str = "sharpe",
) -> pd.DataFrame:
    rows: List[Dict] = []
    for entry in entry_values:
        for exit_ in exit_values:
            entry = int(entry)
            exit_ = int(exit_)
            if entry <= 1 or exit_ <= 1 or exit_ >= entry:
                continue
            config = BacktestConfig(
                symbol=base_config.symbol,
                start_date=base_config.start_date,
                end_date=base_config.end_date,
                strategy_name="turtle_breakout",
                strategy_params={
                    **base_config.strategy_params,
                    "entry_window": entry,
                    "exit_window": exit_,
                    "atr_window": int(atr_window),
                    "stop_atr_multiplier": float(stop_atr_multiplier),
                    "target_weight": base_config.target_weight,
                },
                benchmark=base_config.benchmark,
                frequency=base_config.frequency,
                adjust_type=base_config.adjust_type,
                initial_cash=base_config.initial_cash,
                commission_rate=base_config.commission_rate,
                slippage_rate=base_config.slippage_rate,
                min_commission=base_config.min_commission,
                trade_price=base_config.trade_price,
                target_weight=base_config.target_weight,
                allow_short=base_config.allow_short,
                lot_size=base_config.lot_size,
                risk_free_rate=base_config.risk_free_rate,
                periods_per_year=base_config.periods_per_year,
            )
            try:
                result = run_backtest(price, config)
                metrics = result.metrics
                score = score_metrics(metrics, objective)
                rows.append(
                    {
                        "entry": entry,
                        "exit": exit_,
                        "fast": entry,
                        "slow": exit_,
                        "atrWindow": int(atr_window),
                        "stopAtr": float(stop_atr_multiplier),
                        "score": score,
                        "totalReturn": metrics.get("totalReturn", 0.0),
                        "annualizedReturn": metrics.get("annualizedReturn", 0.0),
                        "maxDrawdown": metrics.get("maxDrawdown", 0.0),
                        "sharpe": metrics.get("sharpe", 0.0),
                        "calmar": metrics.get("calmar", 0.0),
                        "tradeCount": metrics.get("tradeCount", 0),
                        "winRate": metrics.get("winRate", 0.0),
                    }
                )
            except Exception as exc:
                rows.append({"entry": entry, "exit": exit_, "fast": entry, "slow": exit_, "score": -999.0, "error": str(exc)})
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("score", ascending=False).reset_index(drop=True)
        frame.insert(0, "rank", range(1, len(frame) + 1))
    return frame


def score_metrics(metrics: Dict, objective: str) -> float:
    if objective == "total_return":
        return float(metrics.get("totalReturn", 0.0))
    if objective == "calmar":
        return float(metrics.get("calmar", 0.0))
    if objective == "risk_adjusted":
        return float(metrics.get("annualizedReturn", 0.0)) + float(metrics.get("maxDrawdown", 0.0)) * 0.8
    return float(metrics.get("sharpe", 0.0))
