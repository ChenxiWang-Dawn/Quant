"""AI Quant Lab cloud/local research API.

The browser never calls AkShare, yfinance or RQData directly.  This service is
safe to host separately from GitHub Pages and keeps provider credentials local.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_lab import BacktestConfig, run_backtest
from quant_lab.data import normalize_price_frame
from research_platform import AIPlatform, ResearchStore

CATALOG_PATH = ROOT / "ai-quant-lab" / "shared" / "strategy_catalog.json"
CATALOG: List[Dict[str, Any]] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
ALLOWED_ORIGINS = [item.strip() for item in os.getenv("APP_ALLOWED_ORIGINS", "http://localhost:5173,https://chenxiwang-dawn.github.io").split(",") if item.strip()]
QUOTE_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
LOCAL_RUNTIME = os.getenv("AI_QUANT_LAB_RUNTIME", "local").strip().lower() == "local"
RESEARCH_PLATFORM = AIPlatform(ResearchStore(Path(__file__).resolve().parent / ".ai-research" / "research.db"), LOCAL_RUNTIME)

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


class AIExperimentRequest(BaseModel):
    """A deliberately small, reproducible first version of the AI research lab."""

    universe: List[str] = Field(min_length=4, max_length=12)
    start: str
    end: str
    horizon: int = Field(default=10, ge=5, le=30)
    topK: int = Field(default=5, ge=2, le=10)
    transactionCost: float = Field(default=0.001, ge=0, le=0.02)
    source: Literal["auto", "akshare", "yfinance", "rqdata"] = "auto"
    task: Literal["ranking", "regression", "classification"] = "ranking"
    model: Literal["ridge", "linear", "elastic_net", "random_forest", "gradient_boosting"] = "ridge"
    splitMode: Literal["forward", "walk_forward"] = "forward"
    walkForwardFolds: int = Field(default=1, ge=1, le=3)
    seeds: List[int] = Field(default_factory=lambda: [7])


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


AI_FEATURES = ["momentum_5", "momentum_20", "volatility_20", "volume_zscore_20"]


def ai_feature_frame(candles: List[Dict[str, Any]], symbol: str, name: str, horizon: int) -> pd.DataFrame:
    """Create only historical, close-of-day features and a next-open forward label."""
    frame = pd.DataFrame(candles)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").drop_duplicates("date").set_index("date")
    close = pd.to_numeric(frame["close"], errors="coerce")
    opening = pd.to_numeric(frame["open"], errors="coerce")
    volume = pd.to_numeric(frame["volume"], errors="coerce").fillna(0)
    output = pd.DataFrame(index=frame.index)
    output["momentum_5"] = close.pct_change(5)
    output["momentum_20"] = close.pct_change(20)
    output["volatility_20"] = close.pct_change().rolling(20).std()
    volume_std = volume.rolling(20).std().replace(0, np.nan)
    output["volume_zscore_20"] = (volume - volume.rolling(20).mean()) / volume_std
    # A signal observed after today's close is assumed to enter at the next open.
    output["target"] = close.shift(-horizon) / opening.shift(-1) - 1
    output["symbol"] = symbol
    output["name"] = name
    return output.reset_index()


def fit_ridge(frame: pd.DataFrame, alpha: float = 3.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    features = frame[AI_FEATURES].to_numpy(dtype=float)
    target = frame["target"].to_numpy(dtype=float)
    means = features.mean(axis=0)
    scales = features.std(axis=0)
    scales[scales < 1e-10] = 1.0
    standardized = (features - means) / scales
    target_mean = float(target.mean())
    coefficients = np.linalg.pinv(standardized.T @ standardized + alpha * np.eye(len(AI_FEATURES))) @ (standardized.T @ (target - target_mean))
    return coefficients, means, scales, target_mean


def ridge_predict(frame: pd.DataFrame, fitted: tuple[np.ndarray, np.ndarray, np.ndarray, float]) -> np.ndarray:
    coefficients, means, scales, target_mean = fitted
    features = frame[AI_FEATURES].to_numpy(dtype=float)
    return ((features - means) / scales) @ coefficients + target_mean


def fit_classical_model(frame: pd.DataFrame, model_name: str, task: str, seed: int) -> Dict[str, Any]:
    """Fit preprocessing on the training fold only, then return a uniform adapter."""
    if model_name == "ridge":
        fitted = fit_ridge(frame)
        return {"name": "Ridge Cross-Sectional Ranker", "type": "ridge_regression", "adapter": "manual_ridge", "fitted": fitted, "importance": [{"feature": feature, "coefficient": float(value), "scale": float(scale)} for feature, value, scale in zip(AI_FEATURES, fitted[0], fitted[2])], "alpha": 3.0}
    sklearn = optional_import("sklearn")
    if sklearn is None:
        raise ValueError("所选模型需要 scikit-learn；请在受控研究服务安装依赖后重试")
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import ElasticNet, LinearRegression, LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    target = frame["target"].to_numpy(dtype=float)
    if task == "classification":
        target = (target > 0).astype(int)
    if model_name == "linear":
        estimator = LogisticRegression(max_iter=600, random_state=seed) if task == "classification" else LinearRegression()
    elif model_name == "elastic_net":
        estimator = ElasticNet(alpha=.001, l1_ratio=.3, random_state=seed, max_iter=2000)
    elif model_name == "random_forest":
        estimator = RandomForestRegressor(n_estimators=180, min_samples_leaf=5, random_state=seed, n_jobs=1)
    elif model_name == "gradient_boosting":
        estimator = GradientBoostingRegressor(n_estimators=100, max_depth=2, learning_rate=.04, random_state=seed)
    else:
        raise ValueError("不支持的模型类型")
    needs_scaler = model_name in {"linear", "elastic_net"}
    pipeline = Pipeline([("scaler", StandardScaler()), ("model", estimator)]) if needs_scaler else Pipeline([("model", estimator)])
    pipeline.fit(frame[AI_FEATURES], target)
    fitted_estimator = pipeline.named_steps["model"]
    raw_importance = getattr(fitted_estimator, "coef_", getattr(fitted_estimator, "feature_importances_", np.zeros(len(AI_FEATURES))))
    raw_importance = np.asarray(raw_importance).reshape(-1)
    return {"name": {"linear": "Linear Baseline", "elastic_net": "Elastic Net Ranker", "random_forest": "Random Forest Ranker", "gradient_boosting": "Gradient Boosting Ranker"}[model_name], "type": model_name, "adapter": "sklearn_pipeline", "fitted": pipeline, "importance": [{"feature": feature, "coefficient": float(value), "scale": 1.0} for feature, value in zip(AI_FEATURES, raw_importance)], "alpha": None, "classification": task == "classification"}


def predict_classical_model(frame: pd.DataFrame, adapter: Dict[str, Any]) -> np.ndarray:
    if adapter["adapter"] == "manual_ridge":
        return ridge_predict(frame, adapter["fitted"])
    pipeline = adapter["fitted"]
    if adapter.get("classification"):
        return pipeline.predict_proba(frame[AI_FEATURES])[:, 1]
    return pipeline.predict(frame[AI_FEATURES])


def mean_rank_ic(frame: pd.DataFrame) -> float:
    values: List[float] = []
    for _, group in frame.groupby("date"):
        if len(group) < 4 or group["prediction"].nunique() < 2 or group["target"].nunique() < 2:
            continue
        correlation = group["prediction"].corr(group["target"], method="spearman")
        if pd.notna(correlation):
            values.append(float(correlation))
    return float(np.mean(values)) if values else 0.0


def ai_equity_curve(test_frame: pd.DataFrame, horizon: int, top_k: int, transaction_cost: float) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, float]]:
    dates = sorted(pd.to_datetime(test_frame["date"].unique()))[::horizon]
    equity = 1.0
    benchmark = 1.0
    peak = 1.0
    max_drawdown = 0.0
    period_returns: List[float] = []
    turnover_values: List[float] = []
    curve: List[Dict[str, Any]] = []
    holdings: List[Dict[str, Any]] = []
    previous: set[str] = set()

    for timestamp in dates:
        snapshot = test_frame.loc[test_frame["date"] == timestamp].sort_values("prediction", ascending=False)
        if len(snapshot) < top_k:
            continue
        selected = snapshot.head(top_k)
        selected_symbols = selected["symbol"].tolist()
        turnover = 1.0 if not previous else 1.0 - len(previous.intersection(selected_symbols)) / top_k
        # The first rebalance buys the portfolio; subsequent rebalances sell the
        # changing part and buy the replacement part.  Cost is explicitly post-return.
        cost = transaction_cost if not previous else transaction_cost * (2 * turnover)
        portfolio_return = float(selected["target"].mean()) - cost
        benchmark_return = float(snapshot["target"].mean()) - (transaction_cost if not previous else 0.0)
        equity *= 1 + portfolio_return
        benchmark *= 1 + benchmark_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1
        max_drawdown = min(max_drawdown, drawdown)
        curve.append({"date": pd.Timestamp(timestamp).strftime("%Y-%m-%d"), "equity": float(equity), "benchmark": float(benchmark), "drawdown": float(drawdown)})
        holdings.append({"date": pd.Timestamp(timestamp).strftime("%Y-%m-%d"), "symbols": selected_symbols, "names": selected["name"].tolist(), "scores": [float(value) for value in selected["prediction"].tolist()]})
        period_returns.append(portfolio_return)
        turnover_values.append(turnover)
        previous = set(selected_symbols)

    annualizer = math.sqrt(252 / horizon)
    dispersion = float(np.std(period_returns, ddof=1)) if len(period_returns) > 1 else 0.0
    sharpe = float(np.mean(period_returns) / dispersion * annualizer) if dispersion > 1e-12 else 0.0
    return curve, holdings, {
        "totalReturn": float(equity - 1),
        "benchmarkReturn": float(benchmark - 1),
        "maxDrawdown": float(max_drawdown),
        "sharpe": sharpe,
        "turnover": float(np.mean(turnover_values)) if turnover_values else 0.0,
        "rebalances": len(curve),
    }


def create_ai_experiment(request: AIExperimentRequest) -> Dict[str, Any]:
    unique_symbols = list(dict.fromkeys(normalize_symbol(symbol) for symbol in request.universe if str(symbol).strip()))
    if len(unique_symbols) < 4:
        raise ValueError("请至少输入 4 个不重复的标的")
    if request.topK >= len(unique_symbols):
        raise ValueError("Top-K 必须小于标的池数量，才能形成横截面比较")
    start, end = pd.Timestamp(request.start), pd.Timestamp(request.end)
    if end <= start:
        raise ValueError("结束日期必须晚于开始日期")

    warnings: List[str] = []
    assets: List[Dict[str, Any]] = []
    frames: List[pd.DataFrame] = []
    for symbol in unique_symbols:
        try:
            provider, normalized, name, candles = fetch_bars(symbol, request.start, request.end, "1d", "pre", request.source)
            feature_frame = ai_feature_frame(candles, normalized, name, request.horizon)
            if len(feature_frame) < 80:
                warnings.append(normalized + " 的有效历史不足，已跳过")
                continue
            frames.append(feature_frame)
            assets.append({"symbol": normalized, "name": name, "source": provider, "bars": len(candles), "firstDate": candles[0]["date"], "lastDate": candles[-1]["date"]})
        except Exception as exc:
            warnings.append(normalize_symbol(symbol) + " 获取失败：" + str(exc)[:100])

    if len(frames) < 4:
        raise ValueError("可用标的少于 4 个，无法进行横截面实验。" + "；".join(warnings[:3]))
    data = pd.concat(frames, ignore_index=True).replace([np.inf, -np.inf], np.nan).dropna(subset=AI_FEATURES + ["target"])
    per_date = data.groupby("date")["symbol"].nunique()
    eligible_dates = per_date[per_date >= max(4, request.topK)].index.sort_values()
    data = data[data["date"].isin(eligible_dates)].copy()
    dates = list(eligible_dates)
    if len(dates) < 150:
        raise ValueError("有效交易日不足 150 天，请扩大研究区间或更换标的池")

    train_end_index = int(len(dates) * 0.6) - 1
    validation_start_index = train_end_index + 1 + request.horizon
    validation_end_index = validation_start_index + max(20, int(len(dates) * 0.2)) - 1
    test_start_index = validation_end_index + 1 + request.horizon
    if test_start_index >= len(dates) - request.horizon:
        raise ValueError("区间不足以形成训练、验证、测试与 embargo；请增加历史数据")
    train_dates = dates[: train_end_index + 1]
    validation_dates = dates[validation_start_index : validation_end_index + 1]
    test_dates = dates[test_start_index:]
    train = data[data["date"].isin(train_dates)].copy()
    validation = data[data["date"].isin(validation_dates)].copy()
    test = data[data["date"].isin(test_dates)].copy()
    if min(len(train), len(validation), len(test)) < 80:
        raise ValueError("各时间切分中的样本不足，请扩大研究区间")

    seed = request.seeds[0] if request.seeds else 7
    validation_fit = fit_classical_model(train, request.model, request.task, seed)
    validation["prediction"] = predict_classical_model(validation, validation_fit)
    final_fit = fit_classical_model(pd.concat([train, validation], ignore_index=True), request.model, request.task, seed)
    test["prediction"] = predict_classical_model(test, final_fit)
    curve, holdings, metrics = ai_equity_curve(test, request.horizon, request.topK, request.transactionCost)
    if len(curve) < 4:
        raise ValueError("测试期再平衡次数不足，请扩大研究区间")

    equal_weight_returns = [item["benchmark"] / (curve[index - 1]["benchmark"] if index else 1.0) - 1 for index, item in enumerate(curve)]
    baseline_dispersion = float(np.std(equal_weight_returns, ddof=1)) if len(equal_weight_returns) > 1 else 0.0
    baseline_sharpe = float(np.mean(equal_weight_returns) / baseline_dispersion * math.sqrt(252 / request.horizon)) if baseline_dispersion > 1e-12 else 0.0
    ridge_baseline = fit_classical_model(pd.concat([train, validation], ignore_index=True), "ridge", "ranking", seed)
    baseline_test = test.copy()
    baseline_test["prediction"] = predict_classical_model(baseline_test, ridge_baseline)
    baseline_curve, _, baseline_model_metrics = ai_equity_curve(baseline_test, request.horizon, request.topK, request.transactionCost)
    walk_forward = []
    if request.splitMode == "walk_forward" or request.walkForwardFolds > 1:
        fold_count = max(1, request.walkForwardFolds)
        start_index = max(80, len(dates) // 3)
        step = max(request.horizon + 20, (len(dates) - start_index) // fold_count)
        for fold in range(fold_count):
            train_end = min(start_index + fold * step, len(dates) - request.horizon - 30)
            fold_test_start = train_end + request.horizon
            fold_test_end = min(fold_test_start + step, len(dates))
            if fold_test_end - fold_test_start < 20:
                continue
            fold_train = data[data["date"].isin(dates[:train_end])]
            fold_test = data[data["date"].isin(dates[fold_test_start:fold_test_end])].copy()
            fitted = fit_classical_model(fold_train, request.model, request.task, seed + fold)
            fold_test["prediction"] = predict_classical_model(fold_test, fitted)
            walk_forward.append({"fold": fold + 1, "trainEnd": pd.Timestamp(dates[train_end - 1]).strftime("%Y-%m-%d"), "testStart": pd.Timestamp(dates[fold_test_start]).strftime("%Y-%m-%d"), "testEnd": pd.Timestamp(dates[fold_test_end - 1]).strftime("%Y-%m-%d"), "rankIc": mean_rank_ic(fold_test)})
    data_source = sorted({asset["source"] for asset in assets})
    config_payload = request.model_dump() | {"universe": [asset["symbol"] for asset in assets], "split": "60/20/20 chronological with embargo"}
    fingerprint_payload = [{key: asset[key] for key in ("symbol", "source", "bars", "firstDate", "lastDate")} for asset in assets]
    return {
        "id": "ai-" + hashlib.sha256((json.dumps(config_payload, sort_keys=True) + json.dumps(fingerprint_payload, sort_keys=True)).encode()).hexdigest()[:12],
        "status": "completed",
        "engine": "ai-research-mvp",
        "configHash": hashlib.sha256(json.dumps(config_payload, sort_keys=True, default=str).encode()).hexdigest()[:16],
        "dataFingerprint": hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True).encode()).hexdigest()[:16],
        "dataset": {"symbols": assets, "featureNames": AI_FEATURES, "sampleCount": int(len(data)), "dataSources": data_source},
        "split": {"trainEnd": pd.Timestamp(train_dates[-1]).strftime("%Y-%m-%d"), "validationStart": pd.Timestamp(validation_dates[0]).strftime("%Y-%m-%d"), "validationEnd": pd.Timestamp(validation_dates[-1]).strftime("%Y-%m-%d"), "testStart": pd.Timestamp(test_dates[0]).strftime("%Y-%m-%d"), "testEnd": pd.Timestamp(test_dates[-1]).strftime("%Y-%m-%d"), "embargoDays": request.horizon, "trainSamples": len(train), "validationSamples": len(validation), "testSamples": len(test)},
        "model": {"name": final_fit["name"], "type": final_fit["type"], "alpha": final_fit.get("alpha"), "featureCoefficients": final_fit["importance"], "card": {"purpose": "使用历史价格与成交量特征，对未来持有期收益排序，再构造 Top-K 等权组合。", "status": "research baseline" if request.model in {"ridge", "linear"} else "candidate model", "limitations": ["仅使用日频 OHLCV，未接入基本面、行业与宏观数据。", "重要性表示模型依赖，不证明因果关系或未来稳定。", "结果已扣除设定交易成本，但未覆盖停牌、涨跌停与完整税费。"]}},
        "metrics": metrics | {"rankIc": mean_rank_ic(test), "validationRankIc": mean_rank_ic(validation), "walkForward": walk_forward},
        "baseline": {"name": "测试期等权全市场篮子", "totalReturn": float(curve[-1]["benchmark"] - 1), "maxDrawdown": float(min(item["benchmark"] / max(point["benchmark"] for point in curve[: index + 1]) - 1 for index, item in enumerate(curve))), "sharpe": baseline_sharpe},
        "modelBaseline": {"name": ridge_baseline["name"], "totalReturn": baseline_model_metrics["totalReturn"], "rankIc": mean_rank_ic(baseline_test), "rebalances": len(baseline_curve)},
        "equity": curve,
        "holdings": holdings,
        "warnings": warnings + ["研究基线采用严格时间切分，并在训练、验证、测试之间设置持有期长度的 embargo。", "历史回测不代表未来表现；本页面不构成投资建议。"],
    }


@app.get("/api/v1/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "ai-quant-lab-api", "runtime": "local" if LOCAL_RUNTIME else "cloud", "providers": provider_status(), "rqdataLocalOnly": True, "allowedOrigins": len(ALLOWED_ORIGINS), "research": RESEARCH_PLATFORM.store.counts()}


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


@app.get("/api/v1/ai/capabilities")
def ai_capabilities() -> Dict[str, Any]:
    return RESEARCH_PLATFORM.capabilities(provider_status())


@app.post("/api/v1/ai/experiments")
def run_ai_experiment(request: AIExperimentRequest) -> Dict[str, Any]:
    try:
        result = create_ai_experiment(request)
        RESEARCH_PLATFORM.record_experiment(result, request.model_dump())
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": {"code": "AI_EXPERIMENT_INVALID", "message": str(exc), "retryable": False}}) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": {"code": "AI_EXPERIMENT_FAILED", "message": str(exc), "retryable": True}}) from exc


@app.get("/api/v1/ai/datasets")
def list_ai_datasets() -> Dict[str, Any]:
    return {"datasets": RESEARCH_PLATFORM.datasets()}


@app.post("/api/v1/ai/datasets/build")
def build_ai_dataset(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.build_dataset(payload, fetch_bars)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": {"code": "DATASET_INVALID", "message": str(exc), "retryable": False}}) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": {"code": "DATASET_BUILD_FAILED", "message": str(exc), "retryable": True}}) from exc


@app.get("/api/v1/ai/datasets/{dataset_id}")
def get_ai_dataset(dataset_id: str) -> Dict[str, Any]:
    if dataset_id == "a_share_price_volume_v1":
        return RESEARCH_PLATFORM.datasets()[0]
    dataset = RESEARCH_PLATFORM.store.get(dataset_id, "dataset")
    if dataset is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset


@app.get("/api/v1/ai/features")
def list_ai_features() -> Dict[str, Any]:
    return {"featureSets": RESEARCH_PLATFORM.feature_sets()}


@app.post("/api/v1/ai/feature-sets")
def create_ai_feature_set(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.create_feature_set(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/experiments")
def list_ai_experiments(query: str = "") -> Dict[str, Any]:
    return {"experiments": RESEARCH_PLATFORM.store.list("experiment", query)}


@app.get("/api/v1/ai/experiments/{run_id}")
def get_ai_experiment(run_id: str) -> Dict[str, Any]:
    experiment = RESEARCH_PLATFORM.store.get(run_id, "experiment")
    if experiment is None:
        raise HTTPException(status_code=404, detail="实验不存在")
    return experiment


@app.post("/api/v1/ai/experiments/{run_id}/cancel")
def cancel_ai_experiment(run_id: str) -> Dict[str, Any]:
    experiment = RESEARCH_PLATFORM.store.get(run_id, "experiment")
    if experiment is None:
        raise HTTPException(status_code=404, detail="实验不存在")
    if experiment.get("status") != "running":
        return {"id": run_id, "status": experiment.get("status"), "message": "同步实验已结束，不能取消。"}
    experiment["status"] = "cancelled"
    return RESEARCH_PLATFORM.store.save("experiment", experiment, "experiment_cancelled")


@app.post("/api/v1/ai/experiments/compare")
def compare_ai_experiments(payload: Dict[str, Any]) -> Dict[str, Any]:
    ids = [str(item) for item in payload.get("experimentIds", [])][:6]
    records = [RESEARCH_PLATFORM.store.get(item, "experiment") for item in ids]
    experiments = [item for item in records if item]
    if len(experiments) < 2:
        raise HTTPException(status_code=422, detail="请选择至少两个已保存实验")
    fingerprints = {item.get("dataFingerprint") for item in experiments}
    comparable = len(fingerprints) == 1 and len({item.get("result", {}).get("split", {}).get("testStart") for item in experiments}) == 1
    summary = [{"id": item["id"], "model": item.get("result", {}).get("model", {}).get("name"), "metrics": item.get("result", {}).get("metrics", {}), "gate": item.get("gate", {})} for item in experiments]
    return {"comparable": comparable, "warning": "数据或切分不同，不能直接判定胜负。" if not comparable else None, "experiments": summary}


@app.get("/api/v1/ai/models")
def list_ai_models() -> Dict[str, Any]:
    return {"models": RESEARCH_PLATFORM.store.list("model"), "audits": RESEARCH_PLATFORM.store.audits()}


@app.get("/api/v1/ai/models/{model_id}")
def get_ai_model(model_id: str) -> Dict[str, Any]:
    model = RESEARCH_PLATFORM.store.get(model_id, "model")
    if model is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model | {"audits": RESEARCH_PLATFORM.store.audits(model_id)}


@app.post("/api/v1/ai/models/register")
def register_ai_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.register_model(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/ai/models/{model_id}/promote")
def promote_ai_model(model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.promote_model(model_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/portfolios")
def list_ai_portfolios() -> Dict[str, Any]:
    return {"portfolios": RESEARCH_PLATFORM.store.list("portfolio")}


@app.post("/api/v1/ai/portfolios/build")
def build_ai_portfolio(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.build_portfolio(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/portfolios/{portfolio_id}")
def get_ai_portfolio(portfolio_id: str) -> Dict[str, Any]:
    portfolio = RESEARCH_PLATFORM.store.get(portfolio_id, "portfolio")
    if portfolio is None:
        raise HTTPException(status_code=404, detail="组合构建记录不存在")
    return portfolio


@app.post("/api/v1/ai/evaluations")
def create_ai_evaluation(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.evaluate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/evaluations")
def list_ai_evaluations() -> Dict[str, Any]:
    return {"evaluations": RESEARCH_PLATFORM.store.list("evaluation")}


@app.get("/api/v1/ai/evaluations/{evaluation_id}")
def get_ai_evaluation(evaluation_id: str) -> Dict[str, Any]:
    evaluation = RESEARCH_PLATFORM.store.get(evaluation_id, "evaluation")
    if evaluation is None:
        raise HTTPException(status_code=404, detail="评测不存在")
    return evaluation


@app.post("/api/v1/ai/rl/environments/validate")
def validate_rl_environment(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.rl_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/ai/rl/runs")
def run_rl_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.rl_run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/rl/runs")
def list_rl_runs() -> Dict[str, Any]:
    return {"runs": RESEARCH_PLATFORM.store.list("rl_run")}


@app.post("/api/v1/ai/deep-learning/runs")
def run_deep_learning(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.deep_learning_run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": {"code": "DEEP_LEARNING_UNAVAILABLE", "message": str(exc), "retryable": False}}) from exc


@app.get("/api/v1/ai/deep-learning/runs")
def list_deep_learning_runs() -> Dict[str, Any]:
    return {"runs": RESEARCH_PLATFORM.store.list("deep_learning_run")}


@app.post("/api/v1/ai/copilot/responses")
def create_copilot_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.copilot(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/copilot/traces/{trace_id}")
def get_copilot_trace(trace_id: str) -> Dict[str, Any]:
    trace = RESEARCH_PLATFORM.store.get(trace_id, "copilot_trace")
    if trace is None:
        raise HTTPException(status_code=404, detail="助手轨迹不存在")
    return trace


@app.get("/api/v1/ai/negative-results")
def list_negative_results(query: str = "") -> Dict[str, Any]:
    return {"negativeResults": RESEARCH_PLATFORM.store.list("negative_result", query)}


@app.post("/api/v1/ai/negative-results")
def create_negative_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return RESEARCH_PLATFORM.save_negative_result(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/ai/monitoring")
def ai_monitoring() -> Dict[str, Any]:
    return RESEARCH_PLATFORM.monitoring(provider_status())


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
