from __future__ import annotations

import pandas as pd


def industry_return_attribution(
    positions: pd.DataFrame,
    nav: pd.DataFrame,
    bars: pd.DataFrame,
    securities: pd.DataFrame,
    industry_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = ["trade_date", "industry", "return_contribution"]
    if positions.empty:
        return pd.DataFrame(columns=columns)
    prices = bars[["trade_date", "security_id", "close_raw"]].sort_values(
        ["security_id", "trade_date"]
    )
    prices["security_return"] = prices.groupby("security_id")["close_raw"].pct_change()
    frame = positions.merge(
        prices[["trade_date", "security_id", "security_return"]],
        on=["trade_date", "security_id"],
        how="left",
    )
    frame = frame.merge(
        nav[["trade_date", "nav"]].rename(columns={"nav": "portfolio_nav"}),
        on="trade_date",
        how="left",
    )
    if industry_history is not None and not industry_history.empty:
        history = industry_history.sort_values(
            ["effective_date", "security_id"]
        ).copy()
        frame = pd.merge_asof(
            frame.sort_values("trade_date"),
            history.rename(columns={"effective_date": "trade_date"}).sort_values(
                "trade_date"
            ),
            on="trade_date",
            by="security_id",
            direction="backward",
        )
    else:
        frame = frame.merge(
            securities[["security_id", "industry"]], on="security_id", how="left"
        )
    frame["previous_weight"] = (
        frame.groupby("security_id")["market_value"].shift(1)
        / frame["portfolio_nav"].shift(1)
    )
    frame["return_contribution"] = (
        frame["previous_weight"].fillna(0.0) * frame["security_return"].fillna(0.0)
    )
    frame["industry"] = frame["industry"].fillna("UNKNOWN")
    return (
        frame.groupby(["trade_date", "industry"], as_index=False)["return_contribution"]
        .sum()
        .sort_values(["trade_date", "industry"])
        .reset_index(drop=True)
    )
