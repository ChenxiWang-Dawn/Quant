from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from a_share_quant.data import DatasetBundle


def generate_demo_dataset(
    root: str | Path,
    *,
    securities_count: int = 80,
    trading_days: int = 760,
    seed: int = 20260724,
) -> DatasetBundle:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp("2025-12-31"), periods=trading_days)
    industries = np.array(["电子", "机械", "医药", "消费", "金融", "材料", "公用事业", "计算机"])
    boards = np.array(["main", "chinext", "star"])
    security_ids = [f"SEC{index:04d}" for index in range(securities_count)]
    securities = pd.DataFrame({
        "security_id": security_ids,
        "symbol": [f"{600000 + index:06d}" for index in range(securities_count)],
        "exchange": ["SSE" if index % 2 == 0 else "SZSE" for index in range(securities_count)],
        "board": [boards[index % len(boards)] for index in range(securities_count)],
        "industry": [industries[index % len(industries)] for index in range(securities_count)],
        "list_date": [dates[0] - pd.Timedelta(days=1000 + index * 3) for index in range(securities_count)],
    })
    market_returns = rng.normal(0.00025, 0.010, len(dates))
    industry_returns = {
        industry: rng.normal(0.00005, 0.004, len(dates)) for industry in industries
    }
    bar_rows: list[dict[str, object]] = []
    fundamental_rows: list[dict[str, object]] = []
    benchmark_level = 1000 * np.cumprod(1 + market_returns)

    for index, security_id in enumerate(security_ids):
        industry = industries[index % len(industries)]
        quality = rng.normal()
        value = rng.normal()
        beta = rng.uniform(0.7, 1.3)
        drift = 0.00010 + quality * 0.00004 + value * 0.00002
        stock_returns = (
            drift + beta * market_returns + industry_returns[industry]
            + rng.normal(0, 0.012, len(dates))
        )
        close = rng.uniform(8, 35) * np.cumprod(1 + stock_returns)
        previous = np.r_[close[0], close[:-1]]
        overnight = rng.normal(0, 0.0025, len(dates))
        open_price = previous * (1 + overnight)
        intraday = np.abs(rng.normal(0.008, 0.004, len(dates)))
        high = np.maximum(open_price, close) * (1 + intraday)
        low = np.minimum(open_price, close) * (1 - intraday)
        amount = rng.lognormal(np.log(160_000_000), 0.45, len(dates))
        volume = amount / np.maximum(close, 0.01)
        board = boards[index % len(boards)]
        limit_rate = 0.20 if board in {"chinext", "star"} else 0.10
        market_cap = rng.uniform(5e9, 100e9) * close / close[0]
        for date_index, trade_date in enumerate(dates):
            bar_rows.append({
                "security_id": security_id,
                "trade_date": trade_date,
                "open_raw": float(open_price[date_index]),
                "high_raw": float(high[date_index]),
                "low_raw": float(low[date_index]),
                "close_raw": float(close[date_index]),
                "prev_close_raw": float(previous[date_index]),
                "volume": float(volume[date_index]),
                "amount": float(amount[date_index]),
                "adjust_factor": 1.0,
                "limit_up_price": float(previous[date_index] * (1 + limit_rate)),
                "limit_down_price": float(previous[date_index] * (1 - limit_rate)),
                "is_suspended": False,
                "is_risk_warning": False,
                "is_delisting": False,
                "market_cap": float(market_cap[date_index]),
                "float_market_cap": float(market_cap[date_index] * rng.uniform(0.55, 0.9)),
            })
        for report_date in pd.date_range(dates[0], dates[-1], freq="QE"):
            announcement = report_date + pd.Timedelta(days=35)
            if announcement > dates[-1]:
                continue
            fundamental_rows.append({
                "security_id": security_id,
                "report_period": report_date,
                "announcement_time": announcement,
                "available_time": announcement + pd.Timedelta(hours=18),
                "revision_time": announcement + pd.Timedelta(hours=18),
                "roe_ttm": float(0.10 + 0.025 * quality + rng.normal(0, 0.01)),
                "roic_ttm": float(0.08 + 0.020 * quality + rng.normal(0, 0.01)),
                "gross_margin": float(0.30 + 0.04 * quality + rng.normal(0, 0.02)),
                "cfo_to_profit": float(0.90 + 0.10 * quality + rng.normal(0, 0.05)),
                "debt_ratio": float(np.clip(0.45 - 0.04 * quality + rng.normal(0, 0.03), 0.05, 0.90)),
                "earnings_yield": float(0.06 + 0.012 * value + rng.normal(0, 0.006)),
                "book_to_price": float(0.55 + 0.10 * value + rng.normal(0, 0.04)),
                "fcf_yield": float(0.045 + 0.010 * value + rng.normal(0, 0.006)),
                "revenue_growth": float(0.10 + 0.025 * quality + rng.normal(0, 0.02)),
                "profit_growth": float(0.11 + 0.035 * quality + rng.normal(0, 0.025)),
                "earnings_revision": float(rng.normal(0.01 * quality, 0.02)),
            })
    bars = pd.DataFrame(bar_rows)
    benchmark = pd.DataFrame({"trade_date": dates, "close": benchmark_level})
    bundle = DatasetBundle(
        securities=securities,
        bars=bars,
        fundamentals=pd.DataFrame(fundamental_rows),
        benchmark=benchmark,
        source="deterministic_demo",
    )
    bundle.normalize()
    bundle.validate()
    bundle.save(root)
    return bundle
