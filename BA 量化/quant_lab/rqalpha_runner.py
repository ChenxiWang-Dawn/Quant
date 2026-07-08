from __future__ import annotations

from typing import Any, Dict
from pathlib import Path

import pandas as pd

from .schemas import BacktestConfig, frame_records


def run_rqalpha_ma_cross(config: BacktestConfig) -> Dict[str, Any]:
    try:
        import rqalpha
    except Exception as exc:
        raise RuntimeError("当前 Python 环境未安装 rqalpha") from exc

    if config.frequency not in ("1d", "1m", "tick"):
        raise RuntimeError("RQAlpha Plus 完整引擎仅支持 1d/1m/tick，当前周期为 " + str(config.frequency))

    symbol = config.symbol
    fast = int(config.strategy_params.get("fast_window", config.strategy_params.get("fast", 5)))
    slow = int(config.strategy_params.get("slow_window", config.strategy_params.get("slow", 20)))
    target_weight = float(config.strategy_params.get("target_weight", config.target_weight))
    commission_multiplier = config.commission_rate / 0.0008 if config.commission_rate > 0 else 0

    def init(context):
        context.symbol = symbol
        context.fast = fast
        context.slow = slow
        context.target_weight = target_weight

    def handle_bar(context, bar_dict):
        from rqalpha.api import history_bars, order_target_percent

        closes = history_bars(context.symbol, context.slow + 2, "1d", "close")
        if closes is None or len(closes) < context.slow + 1:
            return
        fast_ma = closes[-context.fast :].mean()
        slow_ma = closes[-context.slow :].mean()
        prev_fast = closes[-context.fast - 1 : -1].mean()
        prev_slow = closes[-context.slow - 1 : -1].mean()
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            order_target_percent(context.symbol, context.target_weight)
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            order_target_percent(context.symbol, 0)

    rq_config = {
        "base": {
            "start_date": config.start_date,
            "end_date": config.end_date,
            "frequency": config.frequency,
            "accounts": {"STOCK": config.initial_cash},
            "data_bundle_path": str(Path.home() / ".rqalpha-plus" / "bundle"),
            "capital_gain_tax_rate": 0,
        },
        "extra": {"log_level": "warning"},
        "mod": {
            "sys_analyser": {
                "record": True,
                "benchmark": config.benchmark,
                "plot": False,
                "strategy_name": "AI Quant Lab MA Cross",
            },
            "sys_simulation": {
                "matching_type": None,
                "slippage_model": "PriceRatioSlippage",
                "slippage": config.slippage_rate,
                "price_limit": True,
                "volume_limit": True,
            },
            "sys_transaction_cost": {
                "stock_min_commission": config.min_commission,
                "stock_commission_multiplier": commission_multiplier,
            },
            "sys_progress": {"show": False},
        },
    }

    result = rqalpha.run_func(config=rq_config, init=init, handle_bar=handle_bar)
    return normalize_rqalpha_result(result)


def normalize_rqalpha_result(result: Dict[str, Any]) -> Dict[str, Any]:
    if "sys_analyser" in result and isinstance(result["sys_analyser"], dict):
        result = result["sys_analyser"]
    summary = sanitize_mapping(result.get("summary", {}))
    trades = normalize_frame(result.get("trades"))
    portfolio = normalize_frame(result.get("portfolio"))
    stock_positions = normalize_frame(result.get("stock_positions"))
    metrics = {
        "endingValue": pick(summary, "total_value", "portfolio_value", "unit_net_value"),
        "totalReturn": pick(summary, "total_returns", "total_return", default=0),
        "annualizedReturn": pick(summary, "annualized_returns", "annualized_return", default=0),
        "annualizedVolatility": pick(summary, "volatility", "annualized_volatility", default=0),
        "maxDrawdown": -abs(pick(summary, "max_drawdown", default=0) or 0),
        "sharpe": pick(summary, "sharpe", default=0),
        "sortino": pick(summary, "sortino", default=0),
        "calmar": pick(summary, "calmar", default=0),
        "tradeCount": len(trades),
        "winRate": 0,
        "turnover": pick(summary, "turnover", default=0),
        "benchmarkReturn": pick(summary, "benchmark_total_returns", default=None),
        "excessReturn": pick(summary, "excess_returns", default=None),
        "alpha": pick(summary, "alpha", default=None),
        "beta": pick(summary, "beta", default=None),
    }
    return {
        "engine": "rqalpha-plus",
        "note": "使用 RQAlpha Plus 完整数据包回测；结果来自 sys_analyser 的 summary/trades/portfolio。",
        "summary": {
            "totalReturn": metrics["totalReturn"] or 0,
            "maxDd": metrics["maxDrawdown"] or 0,
            "trades": metrics["tradeCount"],
            "winRate": metrics["winRate"],
        },
        "metrics": metrics,
        "rqalphaSummary": summary,
        "trades": trades,
        "equity": portfolio,
        "positions": stock_positions,
    }


def normalize_frame(value) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, pd.Series):
        frame = value.to_frame().T
    elif isinstance(value, pd.DataFrame):
        frame = value.copy()
    else:
        try:
            frame = pd.DataFrame(value)
        except Exception:
            return []
    if frame.empty:
        return []
    frame.index.name = "_index"
    frame = frame.reset_index()
    return frame_records(frame)


def sanitize_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for key, value in dict(mapping or {}).items():
        if hasattr(value, "item"):
            value = value.item()
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        try:
            if pd.isna(value):
                value = None
        except Exception:
            pass
        out[str(key)] = value
    return out


def pick(mapping: Dict[str, Any], *keys: str, default=0):
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            try:
                return float(value)
            except Exception:
                return value
    return default
