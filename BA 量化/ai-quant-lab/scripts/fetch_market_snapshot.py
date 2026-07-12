#!/usr/bin/env python3
"""Create a small, public, delayed market snapshot for GitHub Pages fallback."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "public" / "snapshots" / "market-summary.json"


def yfinance_quote(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    history = ticker.history(period="5d", interval="1d", auto_adjust=False)
    if history is None or len(history) < 1:
        raise RuntimeError("no price data")
    last = history.iloc[-1]
    previous = history.iloc[-2]["Close"] if len(history) > 1 else last["Close"]
    price = float(last["Close"])
    previous = float(previous)
    return {
        "symbol": symbol,
        "name": symbol,
        "price": price,
        "change": price - previous,
        "changePercent": price / previous - 1 if previous else 0,
        "asOf": str(history.index[-1]),
        "source": "yfinance snapshot",
        "delayed": True,
    }


def akshare_quote(code: str, exchange: str) -> dict:
    import akshare as ak

    frame = ak.stock_zh_a_spot_em()
    match = frame.loc[frame["代码"].astype(str).str.zfill(6) == code]
    if match.empty:
        raise RuntimeError("quote not found")
    item = match.iloc[0]
    return {
        "symbol": code + "." + exchange,
        "name": str(item["名称"]),
        "price": float(item["最新价"]),
        "change": float(item.get("涨跌额") or 0),
        "changePercent": float(item.get("涨跌幅") or 0) / 100,
        "asOf": datetime.now(timezone.utc).isoformat(),
        "source": "akshare snapshot",
        "delayed": True,
    }


def akshare_history_quote(code: str, exchange: str) -> dict:
    """Use recent daily bars when the intraday spot endpoint is rate-limited."""
    import akshare as ak

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=14)
    frame = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"), adjust="qfq")
    if frame is None or len(frame) < 1:
        raise RuntimeError("daily history unavailable")
    last = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) > 1 else last
    price = float(last["收盘"])
    prior = float(previous["收盘"])
    return {
        "symbol": code + "." + exchange,
        "name": code,
        "price": price,
        "change": price - prior,
        "changePercent": price / prior - 1 if prior else 0,
        "asOf": str(last["日期"]),
        "source": "akshare daily snapshot",
        "delayed": True,
    }


def safe(fetcher) -> dict | None:
    try:
        return fetcher()
    except Exception as exc:
        print("snapshot source failed:", exc)
        return None


def main() -> None:
    quotes = [
        safe(lambda: akshare_quote("000001", "XSHE")) or safe(lambda: akshare_history_quote("000001", "XSHE")),
        safe(lambda: akshare_quote("600519", "XSHG")) or safe(lambda: akshare_history_quote("600519", "XSHG")),
        safe(lambda: yfinance_quote("AAPL")),
    ]
    payload = {"updatedAt": datetime.now(timezone.utc).isoformat(), "quotes": [quote for quote in quotes if quote is not None]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUTPUT, "with", len(payload["quotes"]), "quotes")


if __name__ == "__main__":
    main()
