from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_ma_cross_result(price: pd.DataFrame, signals: pd.DataFrame, equity: pd.DataFrame):
    data = price.merge(signals[["date", "fast_ma", "slow_ma", "signal"]], on="date", how="left")
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True, gridspec_kw={"height_ratios": [2.2, 1, 1]})

    axes[0].plot(data["date"], data["close"], label="Close", color="#17212b", linewidth=1.2)
    axes[0].plot(data["date"], data["fast_ma"], label="Fast MA", color="#1f6feb", linewidth=1)
    axes[0].plot(data["date"], data["slow_ma"], label="Slow MA", color="#d97706", linewidth=1)
    buys = data[data["signal"] == 1]
    sells = data[data["signal"] == -1]
    axes[0].scatter(buys["date"], buys["close"], marker="^", color="#d94a38", label="Buy", zorder=3)
    axes[0].scatter(sells["date"], sells["close"], marker="v", color="#1f9d72", label="Sell", zorder=3)
    axes[0].set_title("Price, Moving Averages and Signals")
    axes[0].legend(loc="best")
    axes[0].grid(alpha=0.25)

    axes[1].plot(equity["date"], equity["equity"], color="#1f6feb", label="Equity")
    axes[1].set_title("Equity Curve")
    axes[1].grid(alpha=0.25)

    axes[2].fill_between(equity["date"], equity["drawdown"], 0, color="#d94a38", alpha=0.25)
    axes[2].plot(equity["date"], equity["drawdown"], color="#d94a38", linewidth=1)
    axes[2].set_title("Drawdown")
    axes[2].grid(alpha=0.25)

    fig.autofmt_xdate()
    fig.tight_layout()
    return fig, axes
