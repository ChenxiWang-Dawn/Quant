from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from a_share_quant.accounting.ledger import Fill, Ledger
from a_share_quant.contracts.models import ExecutionProfile


@dataclass(slots=True, frozen=True)
class Order:
    security_id: str
    side: str
    quantity: int
    target_weight: float


class ExecutionSimulator:
    def __init__(self, profile: ExecutionProfile) -> None:
        self.profile = profile

    def target_orders(
        self, targets: pd.DataFrame, ledger: Ledger, bars: pd.DataFrame
    ) -> list[Order]:
        bar_map = bars.set_index("security_id")
        target_map = dict(
            zip(targets["security_id"].astype(str), targets["target_weight"].astype(float))
        )
        security_ids = set(target_map) | set(ledger.positions)
        orders: list[Order] = []
        nav = ledger.nav
        for security_id in security_ids:
            if security_id not in bar_map.index:
                continue
            row = bar_map.loc[security_id]
            price = self._base_price(row)
            if price <= 0:
                continue
            desired = int(
                np.floor(nav * target_map.get(security_id, 0.0) / price / self.profile.lot_size)
                * self.profile.lot_size
            )
            current = ledger.positions.get(security_id)
            current_quantity = current.quantity if current else 0
            difference = desired - current_quantity
            if difference > 0:
                orders.append(Order(security_id, "BUY", difference, target_map.get(security_id, 0.0)))
            elif difference < 0:
                sell_quantity = min(-difference, current.sellable_quantity if current else 0)
                if sell_quantity:
                    orders.append(
                        Order(security_id, "SELL", sell_quantity, target_map.get(security_id, 0.0))
                    )
        return sorted(orders, key=lambda order: 0 if order.side == "SELL" else 1)

    def execute_targets(
        self,
        trade_date: pd.Timestamp,
        targets: pd.DataFrame,
        bars: pd.DataFrame,
        ledger: Ledger,
    ) -> list[Fill]:
        fills: list[Fill] = []
        for order in self.target_orders(targets, ledger, bars):
            row = bars[bars["security_id"].astype(str) == order.security_id]
            if row.empty:
                continue
            fill = self.execute_order(trade_date, order, row.iloc[-1], ledger)
            ledger.apply_fill(fill)
            fills.append(fill)
        return fills

    def execute_order(
        self, trade_date: pd.Timestamp, order: Order, bar: pd.Series, ledger: Ledger
    ) -> Fill:
        reason = self._blocked_reason(order.side, bar)
        if reason:
            return self._empty_fill(trade_date, order, reason)
        base_price = self._base_price(bar)
        amount = max(float(bar["amount"]), 0.0)
        maximum = int(
            np.floor(
                amount * self.profile.max_adv_participation
                / max(base_price, 1e-12)
                / self.profile.lot_size
            )
            * self.profile.lot_size
        )
        quantity = min(order.quantity, maximum)
        if order.side == "SELL":
            position = ledger.positions.get(order.security_id)
            quantity = min(quantity, position.sellable_quantity if position else 0)
        if quantity <= 0:
            return self._empty_fill(trade_date, order, "no_executable_quantity")
        participation = base_price * quantity / max(amount, 1.0)
        impact_rate = self.profile.impact_coefficient * np.sqrt(participation)
        direction = 1.0 if order.side == "BUY" else -1.0
        execution_price = base_price * (
            1.0 + direction * (self.profile.slippage_rate + impact_rate)
        )
        execution_price = min(max(execution_price, float(bar["low_raw"])), float(bar["high_raw"]))
        gross = execution_price * quantity
        commission = max(gross * self.profile.commission_rate, self.profile.minimum_commission)
        stamp_tax = gross * self.profile.sell_stamp_tax_rate if order.side == "SELL" else 0.0
        transfer_fee = gross * self.profile.transfer_fee_rate
        if order.side == "BUY":
            affordable = int(
                np.floor(
                    ledger.cash
                    / max(execution_price * (1.0 + self.profile.commission_rate + self.profile.transfer_fee_rate), 1e-12)
                    / self.profile.lot_size
                )
                * self.profile.lot_size
            )
            quantity = min(quantity, affordable)
            if quantity <= 0:
                return self._empty_fill(trade_date, order, "insufficient_cash")
            gross = execution_price * quantity
            commission = max(gross * self.profile.commission_rate, self.profile.minimum_commission)
            transfer_fee = gross * self.profile.transfer_fee_rate
            while (
                quantity > 0
                and gross + commission + transfer_fee > ledger.cash
            ):
                quantity -= self.profile.lot_size
                gross = execution_price * quantity
                commission = (
                    max(gross * self.profile.commission_rate, self.profile.minimum_commission)
                    if quantity > 0 else 0.0
                )
                transfer_fee = gross * self.profile.transfer_fee_rate
            if quantity <= 0:
                return self._empty_fill(trade_date, order, "insufficient_cash")
        status = "FILLED" if quantity == order.quantity else "PARTIAL"
        return Fill(
            pd.Timestamp(trade_date), order.security_id, order.side, order.quantity,
            quantity, float(execution_price), float(gross), float(commission),
            float(stamp_tax), float(transfer_fee),
            float(base_price * quantity * self.profile.slippage_rate),
            float(base_price * quantity * impact_rate), status,
        )

    def _blocked_reason(self, side: str, bar: pd.Series) -> str:
        if bool(bar.get("is_suspended", False)) or float(bar.get("volume", 0.0)) <= 0:
            return "suspended"
        if not self.profile.simulate_price_limits:
            return ""
        tolerance = 1e-8
        one_price = abs(float(bar["high_raw"]) - float(bar["low_raw"])) <= tolerance
        if side == "BUY" and one_price and float(bar["high_raw"]) >= float(bar["limit_up_price"]) - tolerance:
            return "one_price_limit_up"
        if side == "SELL" and one_price and float(bar["low_raw"]) <= float(bar["limit_down_price"]) + tolerance:
            return "one_price_limit_down"
        return ""

    def _base_price(self, bar: pd.Series) -> float:
        if self.profile.trade_price == "open":
            return float(bar["open_raw"])
        return float(
            (bar["open_raw"] + bar["high_raw"] + bar["low_raw"] + bar["close_raw"]) / 4
        )

    @staticmethod
    def _empty_fill(trade_date: pd.Timestamp, order: Order, reason: str) -> Fill:
        return Fill(
            pd.Timestamp(trade_date), order.security_id, order.side, order.quantity,
            0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "REJECTED", reason,
        )
