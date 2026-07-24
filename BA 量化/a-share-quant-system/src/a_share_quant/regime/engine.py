from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from a_share_quant.contracts.models import RegimeConfig
from a_share_quant.data.dataset import DatasetBundle


@dataclass(slots=True, frozen=True)
class RegimeSnapshot:
    as_of: pd.Timestamp
    state: str
    target_exposure: float
    fast_ma: float
    slow_ma: float
    close: float
    volatility: float
    breadth: float


class RegimeEngine:
    def __init__(self, config: RegimeConfig) -> None:
        self.config = config

    def classify(self, bundle: DatasetBundle, as_of: pd.Timestamp) -> RegimeSnapshot:
        series = self._benchmark_series(bundle, as_of)
        if len(series) < self.config.slow_window:
            return RegimeSnapshot(
                pd.Timestamp(as_of), "risk_off", self.config.risk_off_exposure,
                0.0, 0.0, float(series.iloc[-1]) if len(series) else 0.0, 1.0, 0.0,
            )
        fast = float(series.tail(self.config.fast_window).mean())
        slow = float(series.tail(self.config.slow_window).mean())
        close = float(series.iloc[-1])
        volatility = float(
            series.pct_change().tail(self.config.volatility_window).std(ddof=0)
        )
        breadth = self._breadth(bundle, as_of)
        if (
            close > slow
            and fast > slow
            and breadth >= 0.50
            and volatility <= self.config.high_volatility
        ):
            state, exposure = "risk_on", self.config.risk_on_exposure
        elif close > slow or fast > slow:
            state, exposure = "neutral", self.config.neutral_exposure
        else:
            state, exposure = "risk_off", self.config.risk_off_exposure
        return RegimeSnapshot(
            pd.Timestamp(as_of), state, exposure, fast, slow, close, volatility, breadth
        )

    @staticmethod
    def _benchmark_series(bundle: DatasetBundle, as_of: pd.Timestamp) -> pd.Series:
        if not bundle.benchmark.empty:
            benchmark = bundle.benchmark[bundle.benchmark["trade_date"] <= as_of]
            benchmark = benchmark.sort_values("trade_date")
            price_column = "close" if "close" in benchmark else "close_raw"
            return benchmark.set_index("trade_date")[price_column].astype(float)
        bars = bundle.bars[bundle.bars["trade_date"] <= as_of].copy()
        bars["adj_close"] = bars["close_raw"] * bars["adjust_factor"].fillna(1.0)
        returns = bars.pivot(
            index="trade_date", columns="security_id", values="adj_close"
        ).pct_change()
        return (1.0 + returns.mean(axis=1).fillna(0.0)).cumprod() * 1000.0

    @staticmethod
    def _breadth(bundle: DatasetBundle, as_of: pd.Timestamp) -> float:
        recent = bundle.bars_until(as_of, lookback=21)
        performance = recent.groupby("security_id")["close_raw"].agg(["first", "last"])
        return float((performance["last"] > performance["first"]).mean()) if len(performance) else 0.0
