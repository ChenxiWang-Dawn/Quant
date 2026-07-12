"""AI Quant Lab cloud/local research API.

The browser never calls AkShare, yfinance or RQData directly.  This service is
safe to host separately from GitHub Pages and keeps provider credentials local.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_lab import BacktestConfig, run_backtest
from quant_lab.data import normalize_price_frame

CATALOG_PATH = ROOT / "ai-quant-lab" / "shared" / "strategy_catalog.json"
CATALOG: List[Dict[str, Any]] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
ALLOWED_ORIGINS = [item.strip() for item in os.getenv("APP_ALLOWED_ORIGINS", "http://localhost:5173,https://chenxiwang-dawn.github.io").split(",") if item.strip()]
QUOTE_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
LOCAL_RUNTIME = os.getenv("AI_QUANT_LAB_RUNTIME", "local").strip().lower() == "local"

app = FastAPI(title="AI Quant Lab API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class StrategyRef(BaseModel):
    id: str
    version: Optional[str] = None


class Period(BaseModel):
    start: str
    end: str
    frequency: Literal["1d", "1w"] = "1d"


class DataOptions(BaseModel):
    source: Literal["auto", "akshare", "yfinance", "rqdata"] = "auto"
    adjustType: Literal["pre", "none"] = "pre"


class Execution(BaseModel):
    engine: Literal["quant_lab", "rqalpha"] = "quant_lab"
    initialCash: float = Field(default=100000, gt=0)
    tradePrice: Literal["next_open"] = "next_open"
    commissionRate: float = Field(default=0.0008, ge=0)
    slippageRate: float = Field(default=0.0002, ge=0)
    minCommission: float = Field(default=5, ge=0)
    lotSize: int = Field(default=100, ge=1)


class BacktestRequest(BaseModel):
    strategy: StrategyRef
    params: Dict[str, float]
    universe: List[str] = Field(min_length=1, max_length=1)
    period: Period
    data: DataOptions = Field(default_factory=DataOptions)
    execution: Execution = Field(default_factory=Execution)
    benchmark: Optional[str] = None
    candles: List[Dict[str, Any]] = Field(default_factory=list)


def optional_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def provider_status() -> Dict[str, bool]:
    return {
        "akshare": optional_import("akshare") is not None,
        "yfinance": optional_import("yfinance") is not None,
        "rqdata": LOCAL_RUNTIME and optional_import("rqdatac") is not None,
    }


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    compact = raw.split(".")[0]
    if len(compact) == 6 and compact.isdigit():
        if compact.startswith(("60", "68", "90", "51", "52", "56", "58")):
            return compact + ".XSHG"
        if compact.startswith(("00", "30", "15", "16", "18", "20")):
            return compact + ".XSHE"
    return raw.replace(".SH", ".XSHG").replace(".SZ", ".XSHE").replace(".SS", ".XSHG")


def is_a_share(symbol: str) -> bool:
    return normalize_symbol(symbol).endswith((".XSHG", ".XSHE"))


def yfinance_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    if normalized.endswith(".XSHG"):
        return normalized.replace(".XSHG", ".SS")
    if normalized.endswith(".XSHE"):
        return normalized.replace(".XSHE", ".SZ")
    return normalized


def records_from_frame(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    frame = frame.copy().reset_index()
    aliases = {"date": "date", "日期": "date", "Date": "date", "datetime": "date", "开盘": "open", "Open": "open", "最高": "high", "High": "high", "最低": "low", "Low": "low", "收盘": "close", "Close": "close", "成交量": "volume", "Volume": "volume"}
    frame = frame.rename(columns={column: aliases.get(column, column.lower()) for column in frame.columns})
    if "date" not in frame.columns:
        raise ValueError("行情数据缺少日期字段")
    if "volume" not in frame.columns:
        frame["volume"] = 0
    required = ["open", "high", "low", "close"]
    if any(column not in frame.columns for column in required):
        raise ValueError("行情数据缺少 OHLC 字段")
    output = []
    for _, row in frame.iterrows():
        output.append({"date": pd.to_datetime(row["date"]).strftime("%Y-%m-%d"), "open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]), "close": float(row["close"]), "volume": float(row["volume"] or 0)})
    return sorted(output, key=lambda item: item["date"])


def fetch_akshare(symbol: str, start: str, end: str, frequency: str, adjust: str) -> List[Dict[str, Any]]:
    ak = optional_import("akshare")
    if ak is None:
        raise RuntimeError("云端服务未安装 AkShare")
    if not is_a_share(symbol):
        raise RuntimeError("AkShare 当前路径只用于 A 股标的")
    frame = ak.stock_zh_a_hist(symbol=normalize_symbol(symbol).split(".")[0], period="weekly" if frequency == "1w" else "daily", start_date=start.replace("-", ""), end_date=end.replace("-", ""), adjust="qfq" if adjust == "pre" else "")
    return records_from_frame(frame)


def fetch_yfinance(symbol: str, start: str, end: str, frequency: str, adjust: str) -> List[Dict[str, Any]]:
    yf = optional_import("yfinance")
    if yf is None:
        raise RuntimeError("云端服务未安装 yfinance")
    frame = yf.Ticker(yfinance_symbol(symbol)).history(start=start, end=end, interval="1wk" if frequency == "1w" else "1d", auto_adjust=adjust == "pre")
    return records_from_frame(frame)


def fetch_rqdata(symbol: str, start: str, end: str, frequency: str, adjust: str) -> List[Dict[str, Any]]:
    if not LOCAL_RUNTIME:
        raise RuntimeError("RQData 仅允许在本地研究服务中使用")
    rqdatac = optional_import("rqdatac")
    if rqdatac is None:
        raise RuntimeError("本地环境未安装 rqdatac")
    rqdatac.init()
    frame = rqdatac.get_price(normalize_symbol(symbol), start_date=start, end_date=end, frequency=frequency, fields=["open", "high", "low", "close", "volume"], adjust_type="pre" if adjust == "pre" else "none", expect_df=True)
    return records_from_frame(frame)


def provider_order(source: str, symbol: str) -> List[str]:
    if source != "auto":
        if source == "rqdata" and not LOCAL_RUNTIME:
            raise RuntimeError("GitHub 部署环境不提供 RQData，请选择 AkShare 或 yfinance")
        return [source]
    if is_a_share(symbol):
        return (["rqdata"] if LOCAL_RUNTIME else []) + ["akshare", "yfinance"]
    return ["yfinance", "akshare"]


def resolve_security_name(symbol: str, provider: str) -> str:
    """Return a best-effort display name without making name lookup a hard dependency."""
    normalized = normalize_symbol(symbol)
    try:
        if provider in {"akshare", "rqdata"} and is_a_share(normalized):
            ak = optional_import("akshare")
            if ak is not None:
                frame = ak.stock_individual_info_em(symbol=normalized.split(".")[0])
                if frame is not None and not frame.empty:
                    for label in ("股票简称", "证券简称", "名称"):
                        match = frame.loc[frame["item"].astype(str) == label]
                        if not match.empty:
                            return str(match.iloc[0]["value"])
        if provider == "yfinance":
            yf = optional_import("yfinance")
            if yf is not None:
                info = yf.Ticker(yfinance_symbol(normalized)).get_info()
                return str(info.get("shortName") or info.get("longName") or normalized)
    except Exception:
        pass
    return normalized


def fetch_bars(symbol: str, start: str, end: str, frequency: str = "1d", adjust: str = "pre", source: str = "auto") -> tuple[str, str, str, List[Dict[str, Any]]]:
    normalized = normalize_symbol(symbol)
    errors = []
    fetchers = {"akshare": fetch_akshare, "yfinance": fetch_yfinance, "rqdata": fetch_rqdata}
    for provider in provider_order(source, normalized):
        try:
            candles = fetchers[provider](normalized, start, end, frequency, adjust)
            if candles:
                return provider, normalized, resolve_security_name(normalized, provider), candles
            errors.append(provider + ": 无数据")
        except Exception as exc:
            errors.append(provider + ": " + str(exc)[:110])
    raise RuntimeError("所有数据源均不可用：" + " | ".join(errors))


def quote_from_yfinance(symbol: str) -> Dict[str, Any]:
    yf = optional_import("yfinance")
    if yf is None:
        raise RuntimeError("未安装 yfinance")
    ticker = yf.Ticker(yfinance_symbol(symbol))
    history = ticker.history(period="5d", interval="1d", auto_adjust=False)
    if history is None or len(history) < 1:
        raise RuntimeError("无最新报价")
    last = history.iloc[-1]
    previous = float(history.iloc[-2]["Close"]) if len(history) > 1 else float(last["Close"])
    price = float(last["Close"])
    return {"symbol": normalize_symbol(symbol), "name": normalize_symbol(symbol), "price": price, "change": price - previous, "changePercent": (price / previous - 1) if previous else 0, "asOf": str(history.index[-1]), "source": "yfinance", "delayed": True}


def quote_from_akshare(symbol: str) -> Dict[str, Any]:
    ak = optional_import("akshare")
    if ak is None or not is_a_share(symbol):
        raise RuntimeError("AkShare 实时报价不可用")
    code = normalize_symbol(symbol).split(".")[0]
    frame = ak.stock_zh_a_spot_em()
    row = frame.loc[frame["代码"].astype(str).str.zfill(6) == code]
    if row.empty:
        raise RuntimeError("AkShare 未返回该标的实时报价")
    record = row.iloc[0]
    price = float(record["最新价"])
    return {"symbol": normalize_symbol(symbol), "name": str(record["名称"]), "price": price, "change": float(record.get("涨跌额") or 0), "changePercent": float(record.get("涨跌幅") or 0) / 100, "asOf": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "akshare", "delayed": False}


def quote(symbol: str) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    cached = QUOTE_CACHE.get(normalized)
    if cached and time.time() - cached[0] < 15:
        return cached[1]
    errors = []
    order = (quote_from_akshare, quote_from_yfinance) if is_a_share(normalized) else (quote_from_yfinance, quote_from_akshare)
    for fetcher in order:
        try:
            payload = fetcher(normalized)
            QUOTE_CACHE[normalized] = (time.time(), payload)
            return payload
        except Exception as exc:
            errors.append(str(exc)[:90])
    raise RuntimeError("无法获取最新报价：" + " | ".join(errors))


def manifest(strategy_id: str) -> Dict[str, Any]:
    item = next((strategy for strategy in CATALOG if strategy["id"] == strategy_id), None)
    if item is None:
        raise ValueError("未注册的策略：" + strategy_id)
    return item


def validate_params(item: Dict[str, Any], params: Dict[str, float]) -> None:
    for definition in item["params"]:
        value = float(params.get(definition["key"], definition["default"]))
        if value < definition["minimum"] or value > definition["maximum"]:
            raise ValueError(definition["label"] + "超出允许范围")
    if item["id"] == "ma_cross" and params.get("fast_window", 5) >= params.get("slow_window", 20):
        raise ValueError("快线窗口必须小于慢线窗口")
    if item["id"] == "turtle_breakout" and params.get("exit_window", 10) >= params.get("entry_window", 20):
        raise ValueError("退出窗口必须小于入场窗口")


@app.get("/api/v1/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "ai-quant-lab-api", "runtime": "local" if LOCAL_RUNTIME else "cloud", "providers": provider_status(), "rqdataLocalOnly": True, "allowedOrigins": len(ALLOWED_ORIGINS)}


@app.get("/api/v1/strategies")
def get_strategies() -> Dict[str, Any]:
    return {"strategies": CATALOG}


@app.get("/api/v1/strategies/{strategy_id}")
def get_strategy(strategy_id: str) -> Dict[str, Any]:
    try:
        return manifest(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/market-data/bars")
def market_bars(symbol: str, start: str, end: str, source: Literal["auto", "akshare", "yfinance", "rqdata"] = "auto", frequency: Literal["1d", "1w"] = "1d", adjust: Literal["pre", "none"] = "pre") -> Dict[str, Any]:
    try:
        provider, normalized, name, candles = fetch_bars(symbol, start, end, frequency, adjust, source)
        return {"symbol": normalized, "name": name, "source": provider, "candles": candles}
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": {"code": "MARKET_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}}) from exc


@app.get("/api/v1/market-data/quote")
def market_quote(symbol: str = Query(min_length=1, max_length=24)) -> Dict[str, Any]:
    try:
        return quote(symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": {"code": "QUOTE_UNAVAILABLE", "message": str(exc), "retryable": True}}) from exc


@app.post("/api/v1/backtests")
def create_backtest(request: BacktestRequest) -> Dict[str, Any]:
    try:
        item = manifest(request.strategy.id)
        validate_params(item, request.params)
        symbol = normalize_symbol(request.universe[0])
        candles = request.candles
        used_source = request.data.source
        if not candles:
            used_source, symbol, security_name, candles = fetch_bars(symbol, request.period.start, request.period.end, request.period.frequency, request.data.adjustType, request.data.source)
        else:
            security_name = resolve_security_name(symbol, request.data.source if request.data.source != "auto" else "akshare")
        config = BacktestConfig(symbol=symbol, start_date=request.period.start, end_date=request.period.end, strategy_name=request.strategy.id, strategy_params=request.params, benchmark=request.benchmark, frequency=request.period.frequency, adjust_type=request.data.adjustType, initial_cash=request.execution.initialCash, commission_rate=request.execution.commissionRate, slippage_rate=request.execution.slippageRate, min_commission=request.execution.minCommission, trade_price=request.execution.tradePrice, target_weight=float(request.params.get("target_weight", 0.95)), lot_size=request.execution.lotSize, periods_per_year=52 if request.period.frequency == "1w" else 252)
        result = run_backtest(normalize_price_frame(pd.DataFrame(candles)), config).to_dict()
        fingerprint_source = json.dumps({"symbol": symbol, "period": request.period.model_dump(), "source": used_source, "count": len(candles)}, sort_keys=True)
        config_source = json.dumps(request.model_dump(exclude={"candles"}), sort_keys=True, default=str)
        metrics = result.get("metrics", {})
        return {"engine": "quant_lab", "security": {"symbol": symbol, "name": security_name}, "summary": metrics, "metrics": metrics, "equity": result.get("equity", []), "trades": result.get("trades", []), "notes": result.get("notes", []) + ["信号于收盘确认，默认下一交易日开盘成交。", "行情源：" + used_source], "warnings": ["历史回测不代表未来表现。"] if len(candles) >= 30 else ["样本不足，结果不具统计代表性。"], "configHash": hashlib.sha256(config_source.encode()).hexdigest()[:16], "dataFingerprint": hashlib.sha256(fingerprint_source.encode()).hexdigest()[:16]}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_STRATEGY_PARAMS", "message": str(exc), "retryable": False}}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": {"code": "BACKTEST_FAILED", "message": str(exc), "retryable": True}}) from exc


@app.get("/")
def root() -> Dict[str, str]:
    return {"service": "AI Quant Lab API", "docs": "/docs"}
