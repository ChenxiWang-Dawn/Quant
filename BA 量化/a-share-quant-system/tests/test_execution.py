import pandas as pd

from a_share_quant.accounting import Ledger
from a_share_quant.contracts.models import ExecutionProfile
from a_share_quant.execution import ExecutionSimulator, Order


def _bar(**updates) -> pd.Series:
    payload = {
        "security_id": "A",
        "open_raw": 10.0,
        "high_raw": 10.2,
        "low_raw": 9.8,
        "close_raw": 10.1,
        "volume": 1_000_000,
        "amount": 10_000_000,
        "limit_up_price": 11.0,
        "limit_down_price": 9.0,
        "is_suspended": False,
    }
    payload.update(updates)
    return pd.Series(payload)


def test_t_plus_one_blocks_same_day_sell() -> None:
    ledger = Ledger(100_000)
    ledger.start_day()
    simulator = ExecutionSimulator(ExecutionProfile(trade_price="open"))
    buy = simulator.execute_order(
        pd.Timestamp("2025-01-02"), Order("A", "BUY", 1000, 0.1), _bar(), ledger
    )
    ledger.apply_fill(buy)
    same_day = simulator.execute_order(
        pd.Timestamp("2025-01-02"), Order("A", "SELL", 1000, 0.0), _bar(), ledger
    )
    assert same_day.filled_quantity == 0
    ledger.start_day()
    next_day = simulator.execute_order(
        pd.Timestamp("2025-01-03"), Order("A", "SELL", 1000, 0.0), _bar(), ledger
    )
    assert next_day.filled_quantity == 1000


def test_one_price_limit_up_blocks_buy() -> None:
    simulator = ExecutionSimulator(ExecutionProfile(trade_price="open"))
    fill = simulator.execute_order(
        pd.Timestamp("2025-01-02"),
        Order("A", "BUY", 100, 0.1),
        _bar(open_raw=11.0, high_raw=11.0, low_raw=11.0, close_raw=11.0),
        Ledger(100_000),
    )
    assert fill.status == "REJECTED"
    assert fill.reason == "one_price_limit_up"


def test_minimum_commission_cannot_make_cash_negative() -> None:
    simulator = ExecutionSimulator(ExecutionProfile(trade_price="open"))
    ledger = Ledger(1003)
    fill = simulator.execute_order(
        pd.Timestamp("2025-01-02"),
        Order("A", "BUY", 100, 1.0),
        _bar(),
        ledger,
    )
    ledger.apply_fill(fill)
    assert ledger.cash >= 0


def test_dividend_and_split_keep_accounting_consistent() -> None:
    ledger = Ledger(10_000)
    ledger.start_day()
    simulator = ExecutionSimulator(ExecutionProfile(trade_price="open"))
    fill = simulator.execute_order(
        pd.Timestamp("2025-01-02"), Order("A", "BUY", 100, 0.1), _bar(), ledger
    )
    ledger.apply_fill(fill)
    cash_before = ledger.cash
    ledger.apply_corporate_actions(pd.DataFrame([{
        "security_id": "A",
        "cash_dividend_per_share": 0.5,
        "split_ratio": 2.0,
    }]))
    assert ledger.positions["A"].quantity == 200
    assert ledger.cash == cash_before + 50
