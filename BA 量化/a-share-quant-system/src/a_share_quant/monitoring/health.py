from __future__ import annotations

import pandas as pd

from a_share_quant.data import DatasetBundle


def data_health(bundle: DatasetBundle, as_of: pd.Timestamp | None = None) -> dict[str, object]:
    as_of = pd.Timestamp(as_of or bundle.trade_dates[-1]).normalize()
    eligible_dates = bundle.trade_dates[bundle.trade_dates <= as_of]
    if len(eligible_dates) == 0:
        return {
            "passed": False,
            "checks": {"has_session_on_or_before_as_of": False},
            "latest_trade_date": None,
            "stale_calendar_days": None,
            "missing_price_rate": 1.0,
            "duplicate_rows": int(
                bundle.bars.duplicated(["security_id", "trade_date"]).sum()
            ),
            "securities": int(bundle.securities["security_id"].nunique()),
            "bar_rows": len(bundle.bars),
        }
    latest_trade_date = eligible_dates[-1]
    latest = bundle.bars[bundle.bars["trade_date"] == latest_trade_date]
    missing_price_rate = float(
        latest[["open_raw", "high_raw", "low_raw", "close_raw"]].isna().any(axis=1).mean()
    )
    duplicate_rows = int(bundle.bars.duplicated(["security_id", "trade_date"]).sum())
    stale_days = int((as_of - latest_trade_date).days)
    checks = {
        "no_duplicate_bars": duplicate_rows == 0,
        "missing_price_rate_below_1pct": missing_price_rate <= 0.01,
        "latest_session_not_future": latest_trade_date <= as_of,
        "fundamental_pit_field_present": (
            bundle.fundamentals.empty or "available_time" in bundle.fundamentals
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "latest_trade_date": str(latest_trade_date.date()),
        "stale_calendar_days": stale_days,
        "missing_price_rate": missing_price_rate,
        "duplicate_rows": duplicate_rows,
        "securities": int(bundle.securities["security_id"].nunique()),
        "bar_rows": len(bundle.bars),
    }
