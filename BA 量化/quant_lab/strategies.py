from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd

from .indicators import sma


class Strategy(ABC):
    name = "base"

    def __init__(self, **params: Any) -> None:
        self.params = params

    @abstractmethod
    def generate_signals(self, price: pd.DataFrame) -> pd.DataFrame:
        """Return one row per bar with target_weight decided after that bar closes."""


class MACrossStrategy(Strategy):
    name = "ma_cross"

    def __init__(self, fast_window: int = 5, slow_window: int = 20, target_weight: float = 0.95) -> None:
        if fast_window <= 0 or slow_window <= 0:
            raise ValueError("均线窗口必须为正数")
        if fast_window >= slow_window:
            raise ValueError("fast_window 必须小于 slow_window")
        super().__init__(fast_window=int(fast_window), slow_window=int(slow_window), target_weight=float(target_weight))
        self.fast_window = int(fast_window)
        self.slow_window = int(slow_window)
        self.target_weight = float(target_weight)

    def generate_signals(self, price: pd.DataFrame) -> pd.DataFrame:
        df = price[["date", "close"]].copy()
        df["fast_ma"] = sma(df["close"], self.fast_window)
        df["slow_ma"] = sma(df["close"], self.slow_window)
        df["signal"] = 0
        df["target_weight"] = 0.0
        df["reason"] = ""

        prev_fast = df["fast_ma"].shift(1)
        prev_slow = df["slow_ma"].shift(1)
        cross_up = (prev_fast <= prev_slow) & (df["fast_ma"] > df["slow_ma"])
        cross_down = (prev_fast >= prev_slow) & (df["fast_ma"] < df["slow_ma"])

        df.loc[cross_up, "signal"] = 1
        df.loc[cross_up, "target_weight"] = self.target_weight
        df.loc[cross_up, "reason"] = "短均线上穿长均线"
        df.loc[cross_down, "signal"] = -1
        df.loc[cross_down, "target_weight"] = 0.0
        df.loc[cross_down, "reason"] = "短均线下穿长均线"

        df["position_state"] = df["target_weight"].where(df["signal"] != 0).ffill().fillna(0.0)
        return df


def build_strategy(name: str, params: Dict[str, Any]) -> Strategy:
    if name == "ma_cross":
        return MACrossStrategy(
            fast_window=int(params.get("fast_window", params.get("fast", 5))),
            slow_window=int(params.get("slow_window", params.get("slow", 20))),
            target_weight=float(params.get("target_weight", params.get("targetWeight", 0.95))),
        )
    raise ValueError("未知策略: " + str(name))
