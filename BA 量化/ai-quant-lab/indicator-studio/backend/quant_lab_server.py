#!/usr/bin/env python3
"""Local optional data service for AI Quant Lab Indicator Studio.

Run with:
    /opt/miniconda3/envs/quant/bin/python backend/quant_lab_server.py

The static page works without this service. Start it only when local real data,
RQData, or rqalpha integration is needed.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_QUANT_LAB_PORT", "8766"))


def optional_import(name):
    try:
        return __import__(name)
    except Exception:
        return None


pd = optional_import("pandas")


def provider_status():
    return {
        "akshare": optional_import("akshare") is not None,
        "tushare": optional_import("tushare") is not None and bool(os.environ.get("TUSHARE_TOKEN")),
        "yfinance": optional_import("yfinance") is not None,
        "rqdata": optional_import("rqdatac") is not None,
        "rqalpha": optional_import("rqalpha") is not None,
    }


def normalize_symbol_for_yfinance(symbol):
    symbol = normalize_order_book_id(symbol)
    if symbol.endswith(".XSHG"):
        return symbol.replace(".XSHG", ".SS")
    if symbol.endswith(".XSHE"):
        return symbol.replace(".XSHE", ".SZ")
    return symbol


def normalize_order_book_id(symbol):
    raw = str(symbol or "").strip().upper()
    compact = raw.split(".")[0]
    if len(compact) == 6 and compact.isdigit():
        if compact.startswith(("60", "68", "90", "51", "52", "56", "58")):
            return compact + ".XSHG"
        if compact.startswith(("00", "30", "15", "16", "18", "20")):
            return compact + ".XSHE"
        if compact.startswith(("43", "83", "87", "88")):
            return compact + ".XBSE"
    if raw.endswith(".SH"):
        return compact + ".XSHG"
    if raw.endswith(".SZ"):
        return compact + ".XSHE"
    if raw.endswith(".SS"):
        return compact + ".XSHG"
    return raw


def is_a_share_symbol(symbol):
    return normalize_order_book_id(symbol).endswith((".XSHG", ".XSHE", ".XBSE"))


def normalize_symbol_for_tushare(symbol):
    symbol = normalize_order_book_id(symbol)
    if symbol.endswith(".XSHG"):
        return symbol.replace(".XSHG", ".SH")
    if symbol.endswith(".XSHE"):
        return symbol.replace(".XSHE", ".SZ")
    return symbol


def compact_symbol(symbol):
    return normalize_order_book_id(symbol).split(".")[0]


def frame_to_candles(df):
    if pd is None:
        raise RuntimeError("pandas is required")
    if df is None or len(df) == 0:
        return []

    frame = df.copy()
    if isinstance(frame.index, pd.MultiIndex):
        frame = frame.reset_index()
    else:
        frame = frame.reset_index()

    rename = {
        "日期": "date",
        "date": "date",
        "datetime": "date",
        "trading_date": "date",
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "vol": "volume",
    }
    frame = frame.rename(columns={col: rename.get(col, col) for col in frame.columns})
    if "date" not in frame.columns:
        frame["date"] = frame.index
    required = ["date", "open", "high", "low", "close"]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise RuntimeError("missing columns: " + ", ".join(missing))
    if "volume" not in frame.columns:
        frame["volume"] = 0

    rows = []
    for _, row in frame.iterrows():
        try:
            date_value = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")
            rows.append(
                {
                    "date": date_value,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"] or 0),
                }
            )
        except Exception:
            continue
    rows.sort(key=lambda item: item["date"])
    return rows


def fetch_akshare(symbol, start, end, frequency, adjust):
    ak = optional_import("akshare")
    if ak is None:
        raise RuntimeError("akshare is not installed")
    period = "weekly" if frequency == "1w" else "daily"
    adjust_name = "qfq" if adjust == "pre" else ""
    df = ak.stock_zh_a_hist(
        symbol=compact_symbol(symbol),
        period=period,
        start_date=start.replace("-", ""),
        end_date=end.replace("-", ""),
        adjust=adjust_name,
    )
    return frame_to_candles(df)


def fetch_yfinance(symbol, start, end, frequency, adjust):
    yf = optional_import("yfinance")
    if yf is None:
        raise RuntimeError("yfinance is not installed")
    interval = "1wk" if frequency == "1w" else "1d"
    ticker = yf.Ticker(normalize_symbol_for_yfinance(symbol))
    df = ticker.history(start=start, end=end, interval=interval, auto_adjust=adjust == "pre")
    return frame_to_candles(df)


def fetch_rqdata(symbol, start, end, frequency, adjust):
    rqdatac = optional_import("rqdatac")
    if rqdatac is None:
        raise RuntimeError("rqdatac is not installed")
    rqdatac.init()
    df = rqdatac.get_price(
        normalize_order_book_id(symbol),
        start_date=start,
        end_date=end,
        frequency=frequency,
        fields=["open", "high", "low", "close", "volume"],
        adjust_type="pre" if adjust == "pre" else "none",
        expect_df=True,
    )
    return frame_to_candles(df)


def fetch_tushare(symbol, start, end, frequency, adjust):
    ts = optional_import("tushare")
    if ts is None:
        raise RuntimeError("tushare is not installed")
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not set")
    ts.set_token(token)
    adj = "qfq" if adjust == "pre" else None
    freq = "W" if frequency == "1w" else "D"
    df = ts.pro_bar(
        ts_code=normalize_symbol_for_tushare(symbol),
        start_date=start.replace("-", ""),
        end_date=end.replace("-", ""),
        adj=adj,
        freq=freq,
    )
    return frame_to_candles(df)


def source_order(source, symbol):
    requested = (source or "auto").lower()
    if is_a_share_symbol(symbol):
        order = ["rqdata", "akshare", "yfinance", "tushare"]
    else:
        order = ["yfinance", "akshare", "rqdata", "tushare"]
    if requested != "auto" and requested in order:
        return [requested] + [item for item in order if item != requested]
    return order


def short_error(exc):
    text = str(exc)
    replacements = {
        "this license is only allowed to access through the education network": "授权仅允许教育网访问",
        "Too Many Requests. Rate limited. Try after a while.": "请求过多，被临时限流",
        "Unable to connect to proxy": "代理连接失败",
        "Remote end closed connection without response": "远端断开连接",
        "tushare is not installed": "未安装 tushare",
        "TUSHARE_TOKEN is not set": "未设置 TUSHARE_TOKEN",
    }
    for old, new in replacements.items():
        if old in text:
            return new
    if "HTTPSConnectionPool" in text:
        return "网络请求失败"
    return text[:120]


def fetch_with_fallback(source, symbol, start, end, frequency, adjust):
    fetchers = {
        "akshare": fetch_akshare,
        "yfinance": fetch_yfinance,
        "rqdata": fetch_rqdata,
        "tushare": fetch_tushare,
    }
    normalized = normalize_order_book_id(symbol)
    errors = []
    for name in source_order(source, normalized):
        try:
            candles = fetchers[name](normalized, start, end, frequency, adjust)
            if candles:
                return name, normalized, candles
            errors.append(f"{name}: empty data")
        except Exception as exc:
            errors.append(f"{name}: {short_error(exc)}")
    raise RuntimeError("all data sources failed; " + " | ".join(errors))


def local_backtest(candles, initial_cash):
    cash = float(initial_cash)
    shares = 0.0
    equity = []
    trades = 0
    wins = 0
    entry_price = None

    closes = [float(row["close"]) for row in candles]
    for i, row in enumerate(candles):
        close = float(row["close"])
        if i >= 20:
            fast = sum(closes[i - 5 + 1 : i + 1]) / 5
            slow = sum(closes[i - 20 + 1 : i + 1]) / 20
            prev_fast = sum(closes[i - 5 : i]) / 5
            prev_slow = sum(closes[i - 20 : i]) / 20
            if prev_fast <= prev_slow and fast > slow and shares == 0:
                shares = cash / close
                cash = 0
                entry_price = close
                trades += 1
            elif prev_fast >= prev_slow and fast < slow and shares > 0:
                cash = shares * close
                shares = 0
                if entry_price and close > entry_price:
                    wins += 1
                entry_price = None
        equity.append(cash + shares * close)

    if not equity:
        return {"totalReturn": 0, "maxDd": 0, "trades": 0, "winRate": 0}
    peak = equity[0]
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1)
    return {
        "totalReturn": equity[-1] / equity[0] - 1,
        "maxDd": max_dd,
        "trades": trades,
        "winRate": wins / trades if trades else 0,
    }


def run_backtest(payload):
    candles = payload.get("candles") or []
    initial_cash = payload.get("initialCash") or 100000
    summary = local_backtest(candles, initial_cash)
    engine = "local-python"
    note = "Python 本地轻量回测"

    if optional_import("rqalpha") is not None and payload.get("strategy"):
        # rqalpha is intentionally optional here. A full rqalpha run needs a local
        # data bundle and account configuration; when unavailable, the service
        # returns the deterministic local result above.
        engine = "rqalpha-ready"
        note = "已检测到 rqalpha；当前返回同规则轻量结果，可继续扩展为完整数据包回测。"

    return {"engine": engine, "note": note, "summary": summary}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send({"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        params = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        try:
            if parsed.path == "/api/health":
                self._send({"ok": True, "message": "AI Quant Lab local service", "providers": provider_status()})
                return
            if parsed.path == "/api/price":
                source = params.get("source", "akshare")
                symbol = params.get("symbol", "000001.XSHE")
                start = params.get("start")
                end = params.get("end")
                frequency = params.get("frequency", "1d")
                adjust = params.get("adjust", "pre")
                used_source, normalized_symbol, candles = fetch_with_fallback(
                    source, symbol, start, end, frequency, adjust
                )
                self._send(
                    {"ok": True, "source": used_source, "symbol": normalized_symbol, "candles": candles}
                )
                return
            self._send({"error": "not found"}, 404)
        except Exception as exc:
            self._send({"error": str(exc)}, 500)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if urlparse(self.path).path == "/api/backtest":
                self._send(run_backtest(payload))
                return
            self._send({"error": "not found"}, 404)
        except Exception as exc:
            self._send({"error": str(exc)}, 500)

    def log_message(self, fmt, *args):
        sys.stderr.write("[quant-lab] " + fmt % args + "\n")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AI Quant Lab local service: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAI Quant Lab local service stopped")
