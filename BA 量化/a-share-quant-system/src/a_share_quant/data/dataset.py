from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..storage.artifacts import content_hash


class DatasetValidationError(ValueError):
    pass


REQUIRED_SECURITY_COLUMNS = {
    "security_id",
    "symbol",
    "exchange",
    "board",
    "industry",
    "list_date",
}
REQUIRED_BAR_COLUMNS = {
    "security_id",
    "trade_date",
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "prev_close_raw",
    "volume",
    "amount",
    "adjust_factor",
    "limit_up_price",
    "limit_down_price",
    "is_suspended",
    "is_risk_warning",
    "is_delisting",
    "market_cap",
    "float_market_cap",
}


@dataclass(slots=True)
class DatasetBundle:
    securities: pd.DataFrame
    bars: pd.DataFrame
    fundamentals: pd.DataFrame = field(default_factory=pd.DataFrame)
    benchmark: pd.DataFrame = field(default_factory=pd.DataFrame)
    corporate_actions: pd.DataFrame = field(default_factory=pd.DataFrame)
    industry_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: str = "local"
    _bar_dates_cache: pd.DatetimeIndex | None = field(
        default=None, init=False, repr=False
    )
    _trade_dates_cache: pd.DatetimeIndex | None = field(
        default=None, init=False, repr=False
    )

    @classmethod
    def load(cls, root: str | Path) -> DatasetBundle:
        path = Path(root)
        if not path.exists():
            raise FileNotFoundError(path)

        def load_optional(name: str) -> pd.DataFrame:
            parquet = path / f"{name}.parquet"
            csv = path / f"{name}.csv"
            if parquet.exists():
                return pd.read_parquet(parquet)
            if csv.exists():
                return pd.read_csv(csv)
            return pd.DataFrame()

        bundle = cls(
            securities=load_optional("securities"),
            bars=load_optional("bars"),
            fundamentals=load_optional("fundamentals"),
            benchmark=load_optional("benchmark"),
            corporate_actions=load_optional("corporate_actions"),
            industry_history=load_optional("industry_history"),
            source=str(path),
        )
        bundle.normalize()
        bundle.validate()
        return bundle

    def save(self, root: str | Path) -> None:
        path = Path(root)
        path.mkdir(parents=True, exist_ok=True)
        for name in (
            "securities",
            "bars",
            "fundamentals",
            "benchmark",
            "corporate_actions",
            "industry_history",
        ):
            frame = getattr(self, name)
            if frame is not None and not frame.empty:
                frame.to_parquet(path / f"{name}.parquet", index=False)

    def normalize(self) -> None:
        for frame in (self.bars, self.benchmark):
            if not frame.empty and "trade_date" in frame.columns:
                frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.normalize()
        if not self.securities.empty:
            self.securities["list_date"] = pd.to_datetime(self.securities["list_date"]).dt.normalize()
            if "delist_date" in self.securities.columns:
                self.securities["delist_date"] = pd.to_datetime(
                    self.securities["delist_date"], errors="coerce"
                ).dt.normalize()
        if not self.fundamentals.empty:
            for column in ("report_period", "announcement_time", "available_time", "revision_time"):
                if column in self.fundamentals.columns:
                    self.fundamentals[column] = pd.to_datetime(
                        self.fundamentals[column], errors="coerce"
                    )
        if not self.corporate_actions.empty and "ex_date" in self.corporate_actions.columns:
            self.corporate_actions["ex_date"] = pd.to_datetime(
                self.corporate_actions["ex_date"]
            ).dt.normalize()
        if not self.industry_history.empty:
            self.industry_history["effective_date"] = pd.to_datetime(
                self.industry_history["effective_date"]
            ).dt.normalize()
        if not self.bars.empty:
            self.bars = self.bars.sort_values(["trade_date", "security_id"]).reset_index(drop=True)
            self._bar_dates_cache = pd.DatetimeIndex(self.bars["trade_date"])
            self._trade_dates_cache = pd.DatetimeIndex(
                self.bars["trade_date"].drop_duplicates()
            )

    def validate(self) -> None:
        if self.securities.empty:
            raise DatasetValidationError("securities dataset is empty")
        if self.bars.empty:
            raise DatasetValidationError("bars dataset is empty")
        missing_security = REQUIRED_SECURITY_COLUMNS - set(self.securities.columns)
        missing_bars = REQUIRED_BAR_COLUMNS - set(self.bars.columns)
        if missing_security:
            raise DatasetValidationError(f"securities missing columns: {sorted(missing_security)}")
        if missing_bars:
            raise DatasetValidationError(f"bars missing columns: {sorted(missing_bars)}")
        if self.bars.duplicated(["security_id", "trade_date"]).any():
            raise DatasetValidationError("bars contain duplicate security/date rows")
        ohlc_invalid = (
            (self.bars["high_raw"] < self.bars[["open_raw", "close_raw", "low_raw"]].max(axis=1))
            | (self.bars["low_raw"] > self.bars[["open_raw", "close_raw", "high_raw"]].min(axis=1))
        )
        if ohlc_invalid.any():
            raise DatasetValidationError("bars contain invalid OHLC relationships")
        if (self.bars["adjust_factor"] <= 0).any():
            raise DatasetValidationError("adjust_factor must be positive")
        if not self.fundamentals.empty and "available_time" not in self.fundamentals.columns:
            raise DatasetValidationError("fundamentals require available_time")

    @property
    def fingerprint(self) -> str:
        pieces = {
            "securities": content_hash(self.securities),
            "bars": content_hash(self.bars),
            "fundamentals": content_hash(self.fundamentals) if not self.fundamentals.empty else None,
            "benchmark": content_hash(self.benchmark) if not self.benchmark.empty else None,
            "corporate_actions": (
                content_hash(self.corporate_actions) if not self.corporate_actions.empty else None
            ),
            "industry_history": (
                content_hash(self.industry_history) if not self.industry_history.empty else None
            ),
        }
        return content_hash(pieces)

    @property
    def trade_dates(self) -> pd.DatetimeIndex:
        if self._trade_dates_cache is None:
            self._trade_dates_cache = pd.DatetimeIndex(
                self.bars["trade_date"].drop_duplicates()
            )
        return self._trade_dates_cache

    def bars_until(self, as_of: pd.Timestamp, lookback: int | None = None) -> pd.DataFrame:
        if self._bar_dates_cache is None:
            self._bar_dates_cache = pd.DatetimeIndex(self.bars["trade_date"])
        as_of = pd.Timestamp(as_of).normalize()
        right = int(self._bar_dates_cache.searchsorted(as_of, side="right"))
        left = 0
        if lookback is not None:
            dates = self.trade_dates
            date_right = int(dates.searchsorted(as_of, side="right"))
            if date_right > lookback:
                cutoff = dates[date_right - lookback]
                left = int(
                    self._bar_dates_cache.searchsorted(cutoff, side="left")
                )
        return self.bars.iloc[left:right].copy()

    def bars_on(self, trade_date: pd.Timestamp) -> pd.DataFrame:
        if self._bar_dates_cache is None:
            self._bar_dates_cache = pd.DatetimeIndex(self.bars["trade_date"])
        trade_date = pd.Timestamp(trade_date).normalize()
        left = int(
            self._bar_dates_cache.searchsorted(trade_date, side="left")
        )
        right = int(
            self._bar_dates_cache.searchsorted(trade_date, side="right")
        )
        return self.bars.iloc[left:right]

    def latest_fundamentals(self, as_of: pd.Timestamp) -> pd.DataFrame:
        if self.fundamentals.empty:
            return pd.DataFrame(index=self.securities["security_id"].astype(str).unique())
        eligible = self.fundamentals[self.fundamentals["available_time"] <= as_of].copy()
        if eligible.empty:
            return pd.DataFrame()
        sort_columns = [
            column
            for column in ["security_id", "report_period", "available_time", "revision_time"]
            if column in eligible.columns
        ]
        eligible = eligible.sort_values(sort_columns, na_position="first")
        return eligible.groupby("security_id", as_index=False).tail(1).set_index("security_id")

    def securities_as_of(self, as_of: pd.Timestamp) -> pd.DataFrame:
        securities = self.securities.copy()
        if self.industry_history.empty:
            return securities
        history = self.industry_history[
            self.industry_history["effective_date"] <= pd.Timestamp(as_of)
        ].copy()
        if history.empty:
            return securities
        latest = (
            history.sort_values(["security_id", "effective_date"])
            .groupby("security_id", as_index=False)
            .tail(1)
        )
        securities = securities.drop(columns=["industry"], errors="ignore")
        return securities.merge(
            latest[["security_id", "industry"]], on="security_id", how="left"
        )
