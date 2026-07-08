from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .indicators import annualized_return, drawdown_series, returns_from_equity
from .schemas import Trade


def calculate_performance(
    equity: pd.DataFrame,
    trades: List[Trade],
    initial_cash: float,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
    benchmark_equity: Optional[pd.Series] = None,
) -> Dict[str, Any]:
    if equity is None or equity.empty:
        return empty_metrics()

    curve = pd.to_numeric(equity["equity"], errors="coerce")
    returns = returns_from_equity(curve)
    ending_value = float(curve.iloc[-1])
    total_return = ending_value / float(initial_cash) - 1
    ann_return = annualized_return(total_return, max(len(curve) - 1, 1), periods_per_year)
    ann_vol = float(returns.std(ddof=0) * np.sqrt(periods_per_year)) if len(returns) else 0.0
    sharpe = (ann_return - risk_free_rate) / ann_vol if ann_vol else 0.0

    downside = returns[returns < 0]
    downside_vol = float(downside.std(ddof=0) * np.sqrt(periods_per_year)) if len(downside) else 0.0
    sortino = (ann_return - risk_free_rate) / downside_vol if downside_vol else 0.0

    dd = drawdown_series(curve)
    max_dd = float(dd.min()) if len(dd) else 0.0
    calmar = ann_return / abs(max_dd) if max_dd < 0 else 0.0
    trade_pairs = pair_trades(trades)
    winning = [item for item in trade_pairs if item["pnl"] > 0]
    losing = [item for item in trade_pairs if item["pnl"] < 0]
    gross_profit = sum(item["pnl"] for item in winning)
    gross_loss = abs(sum(item["pnl"] for item in losing))
    win_rate = len(winning) / len(trade_pairs) if trade_pairs else 0.0
    avg_win = gross_profit / len(winning) if winning else 0.0
    avg_loss = gross_loss / len(losing) if losing else 0.0
    payoff_ratio = avg_win / avg_loss if avg_loss else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit > 0 else 0.0)
    commissions = sum(trade.commission for trade in trades)
    slippage = sum(trade.slippage for trade in trades)
    turnover = sum(trade.turnover for trade in trades)

    benchmark_metrics = benchmark_stats(curve, benchmark_equity, periods_per_year) if benchmark_equity is not None else {}
    return {
        "endingValue": ending_value,
        "totalReturn": float(total_return),
        "annualizedReturn": float(ann_return),
        "annualizedVolatility": ann_vol,
        "maxDrawdown": max_dd,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "tradeCount": len(trades),
        "roundTripCount": len(trade_pairs),
        "winRate": float(win_rate),
        "payoffRatio": float(payoff_ratio),
        "profitFactor": float(profit_factor) if np.isfinite(profit_factor) else None,
        "averageHoldingBars": average_holding_bars(trade_pairs),
        "turnover": float(turnover),
        "commission": float(commissions),
        "slippage": float(slippage),
        "cost": float(commissions + slippage),
        "bestTrade": max([item["return"] for item in trade_pairs], default=0.0),
        "worstTrade": min([item["return"] for item in trade_pairs], default=0.0),
        **benchmark_metrics,
    }


def empty_metrics() -> Dict[str, Any]:
    return {
        "endingValue": 0.0,
        "totalReturn": 0.0,
        "annualizedReturn": 0.0,
        "annualizedVolatility": 0.0,
        "maxDrawdown": 0.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "calmar": 0.0,
        "tradeCount": 0,
        "roundTripCount": 0,
        "winRate": 0.0,
    }


def pair_trades(trades: List[Trade]) -> List[Dict[str, Any]]:
    pairs = []
    entry = None
    for trade in trades:
        if trade.side == "buy":
            entry = trade
        elif trade.side == "sell" and entry is not None:
            pnl = trade.turnover - entry.turnover - trade.commission - entry.commission - trade.slippage - entry.slippage
            pairs.append(
                {
                    "entryDate": entry.date,
                    "exitDate": trade.date,
                    "entryPrice": entry.price,
                    "exitPrice": trade.price,
                    "shares": min(entry.shares, trade.shares),
                    "pnl": pnl,
                    "return": trade.price / entry.price - 1 if entry.price else 0.0,
                }
            )
            entry = None
    return pairs


def average_holding_bars(pairs: List[Dict[str, Any]]) -> float:
    if not pairs:
        return 0.0
    spans = []
    for item in pairs:
        try:
            spans.append((pd.to_datetime(item["exitDate"]) - pd.to_datetime(item["entryDate"])).days)
        except Exception:
            pass
    return float(np.mean(spans)) if spans else 0.0


def benchmark_stats(curve: pd.Series, benchmark_equity: pd.Series, periods_per_year: int) -> Dict[str, Any]:
    aligned = pd.concat([curve.rename("strategy"), benchmark_equity.rename("benchmark")], axis=1).dropna()
    if len(aligned) < 3:
        return {}
    strategy_ret = aligned["strategy"].pct_change().dropna()
    benchmark_ret = aligned["benchmark"].pct_change().dropna()
    benchmark_total = aligned["benchmark"].iloc[-1] / aligned["benchmark"].iloc[0] - 1
    excess_total = aligned["strategy"].iloc[-1] / aligned["strategy"].iloc[0] - 1 - benchmark_total
    cov = float(np.cov(strategy_ret, benchmark_ret)[0, 1]) if len(strategy_ret) > 1 else 0.0
    var = float(np.var(benchmark_ret)) if len(benchmark_ret) else 0.0
    beta = cov / var if var else 0.0
    alpha = annualized_return(excess_total, len(aligned) - 1, periods_per_year)
    return {
        "benchmarkReturn": float(benchmark_total),
        "excessReturn": float(excess_total),
        "beta": float(beta),
        "alpha": float(alpha),
    }
