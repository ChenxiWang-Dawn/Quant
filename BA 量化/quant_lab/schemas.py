from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class BacktestConfig:
    symbol: str
    start_date: str
    end_date: str
    strategy_name: str = "ma_cross"
    strategy_params: Dict[str, Any] = field(default_factory=lambda: {"fast_window": 5, "slow_window": 20})
    benchmark: Optional[str] = None
    frequency: str = "1d"
    adjust_type: str = "pre"
    initial_cash: float = 100000.0
    commission_rate: float = 0.0008
    slippage_rate: float = 0.0002
    min_commission: float = 5.0
    trade_price: str = "next_open"
    target_weight: float = 0.95
    allow_short: bool = False
    lot_size: int = 100
    risk_free_rate: float = 0.0
    periods_per_year: int = 252


@dataclass
class Trade:
    date: str
    side: str
    price: float
    shares: int
    turnover: float
    commission: float
    slippage: float
    cash_after: float
    position_after: int
    reason: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "side": self.side,
            "price": self.price,
            "shares": self.shares,
            "turnover": self.turnover,
            "commission": self.commission,
            "slippage": self.slippage,
            "cashAfter": self.cash_after,
            "positionAfter": self.position_after,
            "reason": self.reason,
        }


@dataclass
class BacktestResult:
    config: BacktestConfig
    price: pd.DataFrame
    signals: pd.DataFrame
    equity: pd.DataFrame
    trades: List[Trade]
    metrics: Dict[str, Any]
    benchmark: Optional[pd.DataFrame] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        equity = self.equity.copy()
        signals = self.signals.copy()
        return {
            "config": {
                "symbol": self.config.symbol,
                "startDate": self.config.start_date,
                "endDate": self.config.end_date,
                "strategyName": self.config.strategy_name,
                "strategyParams": self.config.strategy_params,
                "benchmark": self.config.benchmark,
                "frequency": self.config.frequency,
                "adjustType": self.config.adjust_type,
                "initialCash": self.config.initial_cash,
                "commissionRate": self.config.commission_rate,
                "slippageRate": self.config.slippage_rate,
                "minCommission": self.config.min_commission,
                "tradePrice": self.config.trade_price,
                "targetWeight": self.config.target_weight,
                "allowShort": self.config.allow_short,
                "lotSize": self.config.lot_size,
                "riskFreeRate": self.config.risk_free_rate,
                "periodsPerYear": self.config.periods_per_year,
            },
            "metrics": self.metrics,
            "trades": [trade.as_dict() for trade in self.trades],
            "equity": frame_records(equity),
            "signals": frame_records(signals),
            "notes": self.notes,
        }


def frame_records(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    out = frame.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    out = out.astype(object).where(pd.notnull(out), None)
    records = out.to_dict(orient="records")
    for record in records:
        for key, value in list(record.items()):
            if hasattr(value, "item"):
                record[key] = value.item()
    return records
