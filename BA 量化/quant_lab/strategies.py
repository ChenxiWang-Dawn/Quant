from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd

from .indicators import atr, sma


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


class TurtleBreakoutStrategy(Strategy):
    name = "turtle_breakout"

    def __init__(
        self,
        entry_window: int = 20,
        exit_window: int = 10,
        atr_window: int = 20,
        stop_atr_multiplier: float = 2.0,
        target_weight: float = 0.95,
    ) -> None:
        if entry_window <= 1 or exit_window <= 1 or atr_window <= 1:
            raise ValueError("海龟策略窗口必须大于 1")
        if exit_window >= entry_window:
            raise ValueError("exit_window 必须小于 entry_window")
        if stop_atr_multiplier <= 0:
            raise ValueError("stop_atr_multiplier 必须为正数")
        super().__init__(
            entry_window=int(entry_window),
            exit_window=int(exit_window),
            atr_window=int(atr_window),
            stop_atr_multiplier=float(stop_atr_multiplier),
            target_weight=float(target_weight),
        )
        self.entry_window = int(entry_window)
        self.exit_window = int(exit_window)
        self.atr_window = int(atr_window)
        self.stop_atr_multiplier = float(stop_atr_multiplier)
        self.target_weight = float(target_weight)

    def generate_signals(self, price: pd.DataFrame) -> pd.DataFrame:
        df = price[["date", "high", "low", "close"]].copy()
        df["entry_high"] = df["high"].rolling(self.entry_window, min_periods=self.entry_window).max().shift(1)
        df["exit_low"] = df["low"].rolling(self.exit_window, min_periods=self.exit_window).min().shift(1)
        df["atr"] = atr(df["high"], df["low"], df["close"], self.atr_window)
        df["signal"] = 0
        df["target_weight"] = 0.0
        df["reason"] = ""
        df["stop_price"] = pd.NA

        in_position = False
        entry_price = 0.0
        highest_close = 0.0
        stop_price = pd.NA

        for idx, row in df.iterrows():
            close = float(row["close"])
            entry_high = row["entry_high"]
            exit_low = row["exit_low"]
            atr_value = row["atr"]

            if in_position:
                highest_close = max(highest_close, close)
                if pd.notna(atr_value):
                    trailing_stop = highest_close - self.stop_atr_multiplier * float(atr_value)
                    initial_stop = entry_price - self.stop_atr_multiplier * float(atr_value)
                    stop_price = max(float(stop_price) if pd.notna(stop_price) else initial_stop, trailing_stop)
                    df.at[idx, "stop_price"] = stop_price

                channel_exit = pd.notna(exit_low) and close < float(exit_low)
                stop_exit = pd.notna(stop_price) and close <= float(stop_price)
                if channel_exit or stop_exit:
                    df.at[idx, "signal"] = -1
                    df.at[idx, "target_weight"] = 0.0
                    df.at[idx, "reason"] = "跌破退出通道" if channel_exit else "触发 ATR 保护止损"
                    in_position = False
                    entry_price = 0.0
                    highest_close = 0.0
                    stop_price = pd.NA
                    continue

            can_enter = pd.notna(entry_high) and pd.notna(atr_value) and close > float(entry_high)
            if not in_position and can_enter:
                in_position = True
                entry_price = close
                highest_close = close
                stop_price = close - self.stop_atr_multiplier * float(atr_value)
                df.at[idx, "signal"] = 1
                df.at[idx, "target_weight"] = self.target_weight
                df.at[idx, "reason"] = "收盘价突破入场通道"
                df.at[idx, "stop_price"] = stop_price

        df["position_state"] = df["target_weight"].where(df["signal"] != 0).ffill().fillna(0.0)
        return df


def build_strategy(name: str, params: Dict[str, Any]) -> Strategy:
    if name == "ma_cross":
        return MACrossStrategy(
            fast_window=int(params.get("fast_window", params.get("fast", 5))),
            slow_window=int(params.get("slow_window", params.get("slow", 20))),
            target_weight=float(params.get("target_weight", params.get("targetWeight", 0.95))),
        )
    if name == "turtle_breakout":
        return TurtleBreakoutStrategy(
            entry_window=int(params.get("entry_window", params.get("entry", params.get("fast_window", 20)))),
            exit_window=int(params.get("exit_window", params.get("exit", params.get("slow_window", 10)))),
            atr_window=int(params.get("atr_window", params.get("atr", 20))),
            stop_atr_multiplier=float(params.get("stop_atr_multiplier", params.get("stopAtr", 2.0))),
            target_weight=float(params.get("target_weight", params.get("targetWeight", 0.95))),
        )
    raise ValueError("未知策略: " + str(name))
