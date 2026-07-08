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
import re
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_QUANT_LAB_PORT", "8766"))
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_lab import BacktestConfig, optimize_ma_cross, run_backtest as run_quant_backtest, run_rqalpha_ma_cross
from quant_lab.data import normalize_price_frame
from quant_lab.schemas import frame_records


def optional_import(name):
    try:
        return __import__(name)
    except Exception:
        return None


pd = optional_import("pandas")
requests = optional_import("requests")


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


def eastmoney_secid(symbol):
    normalized = normalize_order_book_id(symbol)
    code = normalized.split(".")[0]
    if normalized.endswith(".XSHG"):
        return "1." + code
    return "0." + code


def fetch_eastmoney(symbol, start, end, frequency, adjust):
    if requests is None:
        raise RuntimeError("requests is not installed")
    klt = "102" if frequency == "1w" else "101"
    fqt = "1" if adjust == "pre" else "0"
    params = {
        "secid": eastmoney_secid(symbol),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": klt,
        "fqt": fqt,
        "beg": start.replace("-", ""),
        "end": end.replace("-", ""),
    }
    response = requests.get(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        params=params,
        timeout=12,
        proxies={"http": None, "https": None},
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or {}
    klines = data.get("klines") or []
    rows = []
    for item in klines:
        parts = item.split(",")
        if len(parts) < 6:
            continue
        rows.append(
            {
                "date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
            }
        )
    return data.get("name") or "", rows


def sina_symbol(symbol):
    normalized = normalize_order_book_id(symbol)
    code = normalized.split(".")[0]
    if normalized.endswith(".XSHG"):
        return "sh" + code
    return "sz" + code


def fetch_sina(symbol, start, end, frequency, adjust):
    if requests is None:
        raise RuntimeError("requests is not installed")
    callback = "var _k="
    response = requests.get(
        "https://quotes.sina.cn/cn/api/jsonp_v2.php/" + callback + "/CN_MarketDataService.getKLineData",
        params={"symbol": sina_symbol(symbol), "scale": "240", "ma": "no", "datalen": "1200"},
        timeout=12,
        proxies={"http": "", "https": ""},
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"},
    )
    response.raise_for_status()
    match = re.search(r"=\((\[.*\])\)", response.text, re.S)
    if not match:
        raise RuntimeError("新浪财经返回格式无法解析")
    items = json.loads(match.group(1))
    rows = []
    for item in items:
        date = item.get("day")
        if not date or date < start or date > end:
            continue
        rows.append(
            {
                "date": date,
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume") or 0),
            }
        )
    rows.sort(key=lambda row: row["date"])
    if frequency == "1w" and rows:
        frame = pd.DataFrame(rows)
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
        weekly = (
            frame.resample("W-FRI")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna()
        )
        weekly = weekly.reset_index()
        rows = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
            for _, row in weekly.iterrows()
        ]
    return fetch_sina_name(symbol), rows


def fetch_sina_name(symbol):
    try:
        response = requests.get(
            "https://hq.sinajs.cn/list=" + sina_symbol(symbol),
            timeout=8,
            proxies={"http": "", "https": ""},
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"},
        )
        response.encoding = "gb18030"
        match = re.search(r'="([^,"]+),', response.text)
        return match.group(1) if match else ""
    except Exception:
        return ""


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
    try:
        name, rows = fetch_eastmoney(symbol, start, end, frequency, adjust)
        if rows:
            return name, rows
    except Exception:
        pass
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
    return "", frame_to_candles(df)


def fetch_yfinance(symbol, start, end, frequency, adjust):
    yf = optional_import("yfinance")
    if yf is None:
        raise RuntimeError("yfinance is not installed")
    interval = "1wk" if frequency == "1w" else "1d"
    ticker = yf.Ticker(normalize_symbol_for_yfinance(symbol))
    df = ticker.history(start=start, end=end, interval=interval, auto_adjust=adjust == "pre")
    return "", frame_to_candles(df)


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
    return "", frame_to_candles(df)


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
    return "", frame_to_candles(df)


def source_order(source, symbol):
    requested = (source or "auto").lower()
    if is_a_share_symbol(symbol):
        order = ["rqdata", "akshare", "sina", "yfinance", "tushare"]
    else:
        order = ["yfinance", "akshare", "sina", "rqdata", "tushare"]
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
        "sina": fetch_sina,
        "yfinance": fetch_yfinance,
        "rqdata": fetch_rqdata,
        "tushare": fetch_tushare,
    }
    normalized = normalize_order_book_id(symbol)
    errors = []
    for name in source_order(source, normalized):
        try:
            security_name, candles = fetchers[name](normalized, start, end, frequency, adjust)
            if candles:
                return name, normalized, security_name, candles
            errors.append(f"{name}: empty data")
        except Exception as exc:
            errors.append(f"{name}: {short_error(exc)}")
    raise RuntimeError("all data sources failed; " + " | ".join(errors))


def candles_to_frame(candles):
    if pd is None:
        raise RuntimeError("pandas is required")
    return normalize_price_frame(pd.DataFrame(candles))


def strategy_catalog():
    return [
        {
            "id": "ma_cross",
            "name": "MA 双均线交叉",
            "category": "趋势跟随",
            "description": "短均线上穿长均线买入，下穿卖出；信号在收盘后确认，下一交易日开盘执行。",
            "params": [
                {"key": "fast_window", "label": "快线窗口", "type": "number", "min": 2, "max": 120, "step": 1, "default": 5},
                {"key": "slow_window", "label": "慢线窗口", "type": "number", "min": 3, "max": 260, "step": 1, "default": 20},
                {"key": "target_weight", "label": "目标仓位", "type": "number", "min": 0.1, "max": 1, "step": 0.05, "default": 0.95},
            ],
        }
    ]


def build_backtest_config(payload):
    params = payload.get("strategyParams") or {}
    if payload.get("strategy") == "ma_cross" and "fast_window" not in params:
        params = {
            "fast_window": payload.get("fastWindow", payload.get("fast", 5)),
            "slow_window": payload.get("slowWindow", payload.get("slow", 20)),
            "target_weight": payload.get("targetWeight", 0.95),
        }
    target_weight = float(params.get("target_weight", payload.get("targetWeight", 0.95)))
    frequency = payload.get("frequency", "1d")
    periods_per_year = 52 if frequency == "1w" else 252
    strategy_name = payload.get("strategy", payload.get("strategyName", "ma_cross"))
    if strategy_name != "ma_cross":
        strategy_name = "ma_cross"
    return BacktestConfig(
        symbol=payload.get("symbol", "000001.XSHE"),
        start_date=payload.get("start", ""),
        end_date=payload.get("end", ""),
        strategy_name=strategy_name,
        strategy_params={**params, "target_weight": target_weight},
        benchmark=payload.get("benchmark") or None,
        frequency=frequency,
        adjust_type=payload.get("adjust", payload.get("adjustType", "pre")),
        initial_cash=float(payload.get("initialCash") or 100000),
        commission_rate=float(payload.get("commissionBps", 8)) / 10000,
        slippage_rate=float(payload.get("slippageBps", 2)) / 10000,
        min_commission=float(payload.get("minCommission", 5)),
        trade_price=payload.get("tradePrice", "next_open"),
        target_weight=target_weight,
        allow_short=bool(payload.get("allowShort", False)),
        lot_size=int(payload.get("lotSize", 100)),
        risk_free_rate=float(payload.get("riskFreeRate", 0.0)),
        periods_per_year=periods_per_year,
    )


def run_backtest(payload):
    candles = payload.get("candles") or []
    config = build_backtest_config(payload)
    if payload.get("engine") == "rqalpha":
        try:
            return run_rqalpha_ma_cross(config)
        except Exception as exc:
            if not candles:
                raise RuntimeError("RQAlpha 回测失败，且没有 candles 可用于 fallback: " + short_error(exc))
            fallback = run_quant_backtest(candles_to_frame(candles), config).to_dict()
            metrics = fallback["metrics"]
            fallback.update(
                {
                    "engine": "quant-lab-python",
                    "note": "RQAlpha Plus 不可用，已回退 quant_lab 引擎：" + short_error(exc),
                    "rqalphaError": short_error(exc),
                    "summary": {
                        "totalReturn": metrics.get("totalReturn", 0),
                        "maxDd": metrics.get("maxDrawdown", 0),
                        "trades": metrics.get("tradeCount", 0),
                        "winRate": metrics.get("winRate", 0),
                    },
                }
            )
            return fallback
    if not candles:
        raise RuntimeError("回测需要 candles 行情数据")
    result = run_quant_backtest(candles_to_frame(candles), config)
    payload_out = result.to_dict()
    metrics = payload_out["metrics"]
    payload_out.update(
        {
            "engine": "quant-lab-python",
            "note": "使用 quant_lab 可复用回测核心；信号收盘确认，下一交易日开盘成交。",
            "summary": {
                "totalReturn": metrics.get("totalReturn", 0),
                "maxDd": metrics.get("maxDrawdown", 0),
                "trades": metrics.get("tradeCount", 0),
                "winRate": metrics.get("winRate", 0),
            },
        }
    )
    return payload_out


def explain_research(payload):
    stats = payload.get("stats") or {}
    backtest = payload.get("backtest") or {}
    metrics = backtest.get("metrics") or {}
    signals = payload.get("signals") or {}
    optimization = payload.get("optimization") or {}
    params = payload.get("strategyParams") or {}
    cards = [
        {
            "tag": "研究结论",
            "title": "趋势策略需要先看稳定性",
            "body": "当前样本区间收益为 {ret}，最大回撤为 {dd}。若参数扫描结果集中在相邻窗口都较好，可信度高于单一最优参数。".format(
                ret=fmt_pct(metrics.get("totalReturn", stats.get("totalReturn", 0))),
                dd=fmt_pct(metrics.get("maxDrawdown", stats.get("maxDd", 0))),
            ),
        },
        {
            "tag": "信号解释",
            "title": "MA {}/{} 双均线".format(params.get("fast_window", 5), params.get("slow_window", 20)),
            "body": "短均线代表较近价格共识，长均线代表中期趋势基准。上穿买入、下穿退出，适合趋势延续行情，震荡市容易反复交易。",
        },
        {
            "tag": "交易质量",
            "title": "{} 笔交易，胜率 {}".format(metrics.get("tradeCount", signals.get("trades", 0)), fmt_pct(metrics.get("winRate", signals.get("winRate", 0)))),
            "body": "请同时观察 Profit Factor、盈亏比和平均持仓天数。胜率低但盈亏比高的趋势策略也可能有效，关键是回撤是否可承受。",
        },
        {
            "tag": "参数建议",
            "title": best_param_title(optimization),
            "body": "不要只采用历史最优参数。建议围绕最优组合做邻域测试，并把手续费、滑点上调后再验证一次。",
        },
    ]
    return {"ok": True, "cards": cards, "draft": strategy_draft_text(payload)}


def fmt_pct(value):
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "--"


def best_param_title(optimization):
    best = optimization.get("best") or {}
    if best.get("fast") and best.get("slow"):
        return "当前较优组合 Fast {} / Slow {}".format(best.get("fast"), best.get("slow"))
    return "先运行参数扫描"


def strategy_draft_text(payload):
    symbol = payload.get("symbol", "000001.XSHE")
    params = payload.get("strategyParams") or {}
    fast = int(params.get("fast_window", 5))
    slow = int(params.get("slow_window", 20))
    target = float(params.get("target_weight", 0.95))
    return f'''# RQAlpha Plus MA 双均线策略草稿
from rqalpha.api import history_bars, order_target_percent

def init(context):
    context.symbol = "{symbol}"
    context.fast = {fast}
    context.slow = {slow}
    context.target_weight = {target}

def handle_bar(context, bar_dict):
    closes = history_bars(context.symbol, context.slow + 2, "1d", "close")
    if closes is None or len(closes) < context.slow + 1:
        return
    fast_ma = closes[-context.fast:].mean()
    slow_ma = closes[-context.slow:].mean()
    prev_fast = closes[-context.fast - 1:-1].mean()
    prev_slow = closes[-context.slow - 1:-1].mean()
    if prev_fast <= prev_slow and fast_ma > slow_ma:
        order_target_percent(context.symbol, context.target_weight)
    elif prev_fast >= prev_slow and fast_ma < slow_ma:
        order_target_percent(context.symbol, 0)
'''


def run_optimize(payload):
    candles = payload.get("candles") or []
    if not candles:
        raise RuntimeError("参数优化需要 candles 行情数据")
    config = build_backtest_config(payload)
    fast_start = int(payload.get("fastStart", 3))
    fast_end = int(payload.get("fastEnd", 18))
    slow_start = int(payload.get("slowStart", 20))
    slow_end = int(payload.get("slowEnd", 80))
    step = max(int(payload.get("step", 5)), 1)
    fast_values = range(min(fast_start, fast_end), max(fast_start, fast_end) + 1, step)
    slow_values = range(min(slow_start, slow_end), max(slow_start, slow_end) + 1, step)
    result = optimize_ma_cross(
        candles_to_frame(candles),
        config,
        fast_values=fast_values,
        slow_values=slow_values,
        objective=payload.get("objective", "sharpe"),
    )
    return {
        "engine": "quant-lab-python",
        "objective": payload.get("objective", "sharpe"),
        "results": frame_records(result),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
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
            if parsed.path == "/api/strategies":
                self._send({"ok": True, "strategies": strategy_catalog()})
                return
            if parsed.path == "/api/price":
                source = params.get("source", "akshare")
                symbol = params.get("symbol", "000001.XSHE")
                start = params.get("start")
                end = params.get("end")
                frequency = params.get("frequency", "1d")
                adjust = params.get("adjust", "pre")
                used_source, normalized_symbol, security_name, candles = fetch_with_fallback(
                    source, symbol, start, end, frequency, adjust
                )
                self._send(
                    {
                        "ok": True,
                        "source": used_source,
                        "symbol": normalized_symbol,
                        "name": security_name,
                        "candles": candles,
                    }
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
            if urlparse(self.path).path == "/api/optimize":
                self._send(run_optimize(payload))
                return
            if urlparse(self.path).path == "/api/ai/explain":
                self._send(explain_research(payload))
                return
            self._send({"error": "not found"}, 404)
        except Exception as exc:
            self._send({"error": str(exc)}, 500)

    def log_message(self, fmt, *args):
        sys.stderr.write("[quant-lab] " + fmt % args + "\n")


def json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AI Quant Lab local service: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAI Quant Lab local service stopped")
