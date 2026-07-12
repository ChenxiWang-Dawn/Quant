from __future__ import annotations

from typing import List, Optional

import pandas as pd

from .data import normalize_price_frame
from .metrics import calculate_performance
from .schemas import BacktestConfig, BacktestResult, Trade
from .strategies import Strategy, build_strategy


class BacktestEngine:
    def __init__(self, config: BacktestConfig) -> None:
        self.config = config

    def run(
        self,
        price: pd.DataFrame,
        strategy: Optional[Strategy] = None,
        benchmark_price: Optional[pd.DataFrame] = None,
    ) -> BacktestResult:
        data = normalize_price_frame(price, symbol=self.config.symbol)
        if len(data) < 3:
            raise ValueError("行情数据太少，无法回测")
        active_strategy = strategy or build_strategy(self.config.strategy_name, self.config.strategy_params)
        signals = active_strategy.generate_signals(data)
        equity, trades, notes = self._simulate(data, signals)

        benchmark_equity = None
        if benchmark_price is not None:
            bench = normalize_price_frame(benchmark_price, symbol=self.config.benchmark)
            benchmark_equity = benchmark_curve(bench)
        metrics = calculate_performance(
            equity,
            trades,
            initial_cash=self.config.initial_cash,
            periods_per_year=self.config.periods_per_year,
            risk_free_rate=self.config.risk_free_rate,
            benchmark_equity=benchmark_equity,
        )
        equity["drawdown"] = equity["equity"] / equity["equity"].cummax() - 1
        return BacktestResult(
            config=self.config,
            price=data,
            signals=signals,
            equity=equity,
            trades=trades,
            metrics=metrics,
            benchmark=benchmark_price,
            notes=notes,
        )

    def _simulate(self, price: pd.DataFrame, signals: pd.DataFrame):
        cash = float(self.config.initial_cash)
        position = 0
        current_target = 0.0
        rows = []
        trades: List[Trade] = []
        notes = ["信号在当日收盘后确认，默认下一交易日开盘成交。"]

        merged = price[["date", "open", "high", "low", "close", "volume"]].merge(
            signals[["date", "signal", "target_weight", "reason"]], on="date", how="left"
        )
        merged[["signal", "target_weight"]] = merged[["signal", "target_weight"]].fillna(0.0)
        merged["reason"] = merged["reason"].fillna("")

        for i, row in merged.iterrows():
            if i > 0:
                prev = merged.iloc[i - 1]
                if prev["signal"] != 0:
                    current_target = float(prev["target_weight"])
                    cash, position, trade = self._rebalance(
                        date=row["date"],
                        open_price=float(row["open"]),
                        close_price=float(row["close"]),
                        cash=cash,
                        position=position,
                        target_weight=current_target,
                        reason=str(prev["reason"]),
                    )
                    if trade is not None:
                        trades.append(trade)

            equity_value = cash + position * float(row["close"])
            rows.append(
                {
                    "date": row["date"],
                    "cash": cash,
                    "position": position,
                    "close": float(row["close"]),
                    "market_value": position * float(row["close"]),
                    "equity": equity_value,
                    "target_weight": current_target,
                }
            )

        if merged.iloc[-1]["signal"] != 0:
            notes.append("最后一根 K 线产生的信号没有下一交易日可成交，已保留在信号表但未执行。")
        return pd.DataFrame(rows), trades, notes

    def _rebalance(
        self,
        date,
        open_price: float,
        close_price: float,
        cash: float,
        position: int,
        target_weight: float,
        reason: str,
    ):
        fill_price = open_price if self.config.trade_price == "next_open" and open_price > 0 else close_price
        equity_before = cash + position * fill_price
        if not self.config.allow_short:
            target_weight = max(0.0, min(target_weight, 1.0))
        target_value = equity_before * target_weight
        current_value = position * fill_price
        delta_value = target_value - current_value
        lot = max(int(self.config.lot_size), 1)
        raw_shares = int(abs(delta_value) / fill_price)
        shares = raw_shares // lot * lot if lot > 1 else raw_shares
        if shares <= 0:
            return cash, position, None

        side = "buy" if delta_value > 0 else "sell"
        if side == "sell":
            shares = min(shares, position)
        if shares <= 0:
            return cash, position, None

        turnover = shares * fill_price
        commission = max(turnover * self.config.commission_rate, self.config.min_commission)
        slippage = turnover * self.config.slippage_rate
        if side == "buy":
            total_cost = turnover + commission + slippage
            if total_cost > cash:
                affordable = int((cash - self.config.min_commission) / (fill_price * (1 + self.config.commission_rate + self.config.slippage_rate)))
                shares = max(0, affordable // lot * lot if lot > 1 else affordable)
                turnover = shares * fill_price
                commission = max(turnover * self.config.commission_rate, self.config.min_commission) if shares else 0.0
                slippage = turnover * self.config.slippage_rate
                total_cost = turnover + commission + slippage
            if shares <= 0:
                return cash, position, None
            cash -= total_cost
            position += shares
        else:
            cash += turnover - commission - slippage
            position -= shares

        trade = Trade(
            date=pd.to_datetime(date).strftime("%Y-%m-%d"),
            side=side,
            price=float(fill_price),
            shares=int(shares),
            turnover=float(turnover),
            commission=float(commission),
            slippage=float(slippage),
            cash_after=float(cash),
            position_after=int(position),
            reason=reason,
        )
        return cash, position, trade


def benchmark_curve(price: pd.DataFrame) -> pd.Series:
    data = normalize_price_frame(price)
    curve = data.set_index("date")["close"].astype(float)
    return curve / curve.iloc[0]


def run_backtest(price: pd.DataFrame, config: BacktestConfig, benchmark_price: Optional[pd.DataFrame] = None) -> BacktestResult:
    return BacktestEngine(config).run(price, benchmark_price=benchmark_price)
