from __future__ import annotations

import numpy as np
import pandas as pd


def evaluate_performance(nav: pd.DataFrame, initial_cash: float) -> dict[str, float | int]:
    if nav.empty:
        return {}
    values = nav.set_index("trade_date")["nav"].astype(float)
    returns = values.pct_change().fillna(0.0)
    days = max((values.index[-1] - values.index[0]).days, 1)
    annualized_return = float((values.iloc[-1] / initial_cash) ** (365.25 / days) - 1)
    annualized_volatility = float(returns.std(ddof=0) * np.sqrt(252))
    sharpe = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0
    drawdown = values / values.cummax() - 1.0
    maximum_drawdown = float(-drawdown.min())
    return {
        "start_nav": float(values.iloc[0]),
        "end_nav": float(values.iloc[-1]),
        "total_return": float(values.iloc[-1] / initial_cash - 1),
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": float(sharpe),
        "maximum_drawdown": maximum_drawdown,
        "trading_days": len(values),
    }
