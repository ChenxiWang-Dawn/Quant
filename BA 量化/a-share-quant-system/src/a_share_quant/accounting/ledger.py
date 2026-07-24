from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(slots=True)
class Position:
    security_id: str
    quantity: int = 0
    sellable_quantity: int = 0
    average_cost: float = 0.0
    last_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price


@dataclass(slots=True, frozen=True)
class Fill:
    trade_date: pd.Timestamp
    security_id: str
    side: str
    requested_quantity: int
    filled_quantity: int
    price: float
    gross_amount: float
    commission: float
    stamp_tax: float
    transfer_fee: float
    slippage_cost: float
    impact_cost: float
    status: str
    reason: str = ""

    @property
    def total_fees(self) -> float:
        return self.commission + self.stamp_tax + self.transfer_fee


class Ledger:
    def __init__(self, initial_cash: float) -> None:
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.positions: dict[str, Position] = {}
        self.fills: list[Fill] = []
        self.realized_pnl = 0.0
        self.dividend_income = 0.0

    @property
    def nav(self) -> float:
        return self.cash + sum(position.market_value for position in self.positions.values())

    def start_day(self) -> None:
        for position in self.positions.values():
            position.sellable_quantity = position.quantity

    def mark(self, prices: dict[str, float]) -> None:
        for security_id, price in prices.items():
            if security_id in self.positions and pd.notna(price):
                self.positions[security_id].last_price = float(price)

    def apply_fill(self, fill: Fill) -> None:
        self.fills.append(fill)
        if fill.filled_quantity <= 0:
            return
        position = self.positions.setdefault(
            fill.security_id, Position(fill.security_id, last_price=fill.price)
        )
        quantity = fill.filled_quantity
        fees = fill.total_fees
        if fill.side == "BUY":
            total_cost = position.average_cost * position.quantity + fill.gross_amount + fees
            position.quantity += quantity
            position.average_cost = total_cost / position.quantity
            self.cash -= fill.gross_amount + fees
        else:
            quantity = min(quantity, position.quantity, position.sellable_quantity)
            proceeds = fill.price * quantity
            allocated_fees = fees * quantity / fill.filled_quantity
            self.realized_pnl += (
                (fill.price - position.average_cost) * quantity - allocated_fees
            )
            position.quantity -= quantity
            position.sellable_quantity -= quantity
            self.cash += proceeds - allocated_fees
            if position.quantity == 0:
                del self.positions[fill.security_id]
                return
        position.last_price = fill.price

    def apply_corporate_actions(self, actions: pd.DataFrame) -> None:
        for action in actions.itertuples(index=False):
            security_id = str(action.security_id)
            position = self.positions.get(security_id)
            if position is None:
                continue
            split_ratio = float(getattr(action, "split_ratio", 1.0) or 1.0)
            cash_dividend = float(getattr(action, "cash_dividend_per_share", 0.0) or 0.0)
            if cash_dividend:
                cash_received = position.quantity * cash_dividend
                self.cash += cash_received
                self.dividend_income += cash_received
            if split_ratio != 1.0:
                position.quantity = round(position.quantity * split_ratio)
                position.sellable_quantity = round(position.sellable_quantity * split_ratio)
                position.average_cost /= split_ratio
                position.last_price /= split_ratio

    def weights(self) -> dict[str, float]:
        nav = self.nav
        if nav <= 0:
            return {}
        return {
            security_id: position.market_value / nav
            for security_id, position in self.positions.items()
        }

    def positions_frame(self) -> pd.DataFrame:
        if not self.positions:
            return pd.DataFrame(
                columns=[
                    "security_id", "quantity", "sellable_quantity",
                    "average_cost", "last_price", "market_value",
                ]
            )
        rows = []
        for position in self.positions.values():
            row = asdict(position)
            row["market_value"] = position.market_value
            rows.append(row)
        return pd.DataFrame(rows)
