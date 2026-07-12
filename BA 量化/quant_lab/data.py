from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


PRICE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def normalize_order_book_id(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    compact = raw.split(".")[0]
    if len(compact) == 6 and compact.isdigit():
        if compact.startswith(("60", "68", "90", "51", "52", "56", "58")):
            return compact + ".XSHG"
        if compact.startswith(("00", "30", "15", "16", "18", "20")):
            return compact + ".XSHE"
        if compact.startswith(("43", "83", "87", "88")):
            return compact + ".XBSE"
    if raw.endswith(".SH") or raw.endswith(".SS"):
        return compact + ".XSHG"
    if raw.endswith(".SZ"):
        return compact + ".XSHE"
    return raw


def normalize_price_frame(frame: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError("行情数据为空")

    df = frame.copy()
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    elif "date" not in df.columns and "datetime" not in df.columns and "trade_date" not in df.columns:
        df = df.reset_index()

    rename = {
        "日期": "date",
        "trade_date": "date",
        "datetime": "date",
        "Date": "date",
        "level_0": "date",
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
        "vol": "volume",
    }
    df = df.rename(columns={col: rename.get(col, col) for col in df.columns})
    if "date" not in df.columns:
        df["date"] = df.index
    if "volume" not in df.columns:
        df["volume"] = 0.0

    missing = [col for col in ["date", "open", "high", "low", "close"] if col not in df.columns]
    if missing:
        raise ValueError("行情数据缺少字段: " + ", ".join(missing))

    df = df[PRICE_COLUMNS + [col for col in df.columns if col not in PRICE_COLUMNS]].copy()
    raw_date = df["date"]
    date_text = raw_date.astype(str).str.strip()
    if date_text.str.fullmatch(r"\d{8}").all():
        df["date"] = pd.to_datetime(date_text, format="%Y%m%d")
    else:
        df["date"] = pd.to_datetime(raw_date)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "open", "high", "low", "close"])
    df = df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    if symbol:
        df["symbol"] = normalize_order_book_id(symbol)
    return df


def load_csv_price(path: str, symbol: Optional[str] = None, encoding: str = "utf-8") -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))
    try:
        frame = pd.read_csv(csv_path, encoding=encoding)
    except UnicodeDecodeError:
        frame = pd.read_csv(csv_path, encoding="utf-8-sig")
    return normalize_price_frame(frame, symbol=symbol)


def fetch_rqdata_price(
    symbol: str,
    start_date: str,
    end_date: str,
    frequency: str = "1d",
    adjust_type: str = "pre",
    fields: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    import rqdatac

    rqdatac.init()
    order_book_id = normalize_order_book_id(symbol)
    use_fields = list(fields or ["open", "high", "low", "close", "volume"])
    frame = rqdatac.get_price(
        order_book_id,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        fields=use_fields,
        adjust_type=adjust_type,
        expect_df=True,
    )
    return normalize_price_frame(frame, symbol=order_book_id)
