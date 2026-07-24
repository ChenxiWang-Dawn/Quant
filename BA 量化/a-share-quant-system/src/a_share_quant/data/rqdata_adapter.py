from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from a_share_quant.data.dataset import DatasetBundle


@dataclass(slots=True, frozen=True)
class RQDataSyncConfig:
    start: str
    end: str
    universe_index: str = "000905.XSHG"
    benchmark_id: str = "000905.XSHG"
    security_ids: tuple[str, ...] = ()
    chunk_size: int = 300
    industry_source: str = "citics_2019"
    industry_level: int = 1
    incremental: bool = True


class RQDataAdapter:
    FACTOR_FIELDS: ClassVar[tuple[str, ...]] = (
        "return_on_equity_ttm",
        "gross_profit_margin_ttm",
        "operating_cash_flow_per_share_ttm",
        "debt_to_asset_ratio",
        "pe_ratio",
        "pb_ratio",
        "operating_revenue_growth_ratio_ttm",
        "net_profit_growth_ratio_ttm",
    )

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            try:
                import rqdatac
            except ImportError as error:
                raise RuntimeError(
                    "rqdatac is not installed; install project dependencies first"
                ) from error
            client = rqdatac
        self.client = client

    def initialize(self) -> None:
        self.client.init()

    def sync(
        self,
        output: str | Path,
        config: RQDataSyncConfig,
        progress=None,
    ) -> DatasetBundle:
        self.initialize()
        output = Path(output)
        trading_dates = pd.DatetimeIndex(
            pd.to_datetime(
                self.client.get_trading_dates(config.start, config.end)
            )
        )
        if trading_dates.empty:
            raise ValueError("RQData returned no trading dates")
        security_ids = self._security_ids(config)
        if not security_ids:
            raise ValueError("RQData returned an empty universe")
        if progress:
            progress("securities", 0.05)
        securities = self._securities(security_ids, config.end)
        if progress:
            progress("prices", 0.15)
        bars = self._bars(security_ids, trading_dates, config, progress)
        if progress:
            progress("fundamentals", 0.65)
        fundamentals = self._fundamentals(
            security_ids, trading_dates, config
        )
        if progress:
            progress("industry", 0.75)
        industry_history = self._industry_history(
            security_ids, trading_dates, config
        )
        if not industry_history.empty:
            latest_industry = (
                industry_history.sort_values(
                    ["security_id", "effective_date"]
                )
                .groupby("security_id", as_index=False)
                .tail(1)
                .set_index("security_id")["industry"]
            )
            securities["industry"] = securities["security_id"].map(
                latest_industry
            ).fillna("UNKNOWN")
        if progress:
            progress("benchmark", 0.85)
        benchmark = self._benchmark(config)
        corporate_actions = self._corporate_actions(
            security_ids, config
        )
        bundle = DatasetBundle(
            securities=securities,
            bars=bars,
            fundamentals=fundamentals,
            benchmark=benchmark,
            corporate_actions=corporate_actions,
            industry_history=industry_history,
            source=(
                f"rqdata:{config.universe_index}:"
                f"{config.start}:{config.end}"
            ),
        )
        bundle.normalize()
        bundle.validate()
        if config.incremental and (output / "bars.parquet").exists():
            bundle = self._merge_existing(output, bundle)
        bundle.save(output)
        if progress:
            progress("completed", 1.0)
        return bundle

    def _security_ids(self, config: RQDataSyncConfig) -> list[str]:
        if config.security_ids:
            return sorted(set(map(str, config.security_ids)))
        if config.universe_index.lower() == "all":
            master = self.client.all_instruments(
                type="CS", date=config.end, market="cn"
            )
            return sorted(master["order_book_id"].astype(str).unique())
        history = self.client.index_components(
            config.universe_index,
            start_date=config.start,
            end_date=config.end,
        )
        if isinstance(history, dict):
            return sorted({
                str(security_id)
                for members in history.values()
                for security_id in members
            })
        return sorted(map(str, history))

    def _securities(
        self, security_ids: list[str], as_of: str
    ) -> pd.DataFrame:
        master = self.client.all_instruments(type="CS", market="cn")
        master = master[
            master["order_book_id"].astype(str).isin(security_ids)
        ].copy()
        board_mapping = {
            "MainBoard": "main",
            "GEM": "chinext",
            "KSH": "star",
        }
        frame = pd.DataFrame({
            "security_id": master["order_book_id"].astype(str),
            "symbol": master["trading_code"].astype(str),
            "exchange": master["exchange"].astype(str),
            "board": master["board_type"].map(board_mapping).fillna("main"),
            "industry": master.get(
                "citics_industry_name",
                pd.Series("UNKNOWN", index=master.index),
            ).fillna("UNKNOWN"),
            "list_date": pd.to_datetime(master["listed_date"]),
            "delist_date": pd.to_datetime(
                master["de_listed_date"], errors="coerce", format="mixed"
            ),
            "name": master["symbol"].astype(str),
            "round_lot": master["round_lot"].fillna(100).astype(int),
            "source_as_of": pd.Timestamp(as_of),
        })
        return frame.reset_index(drop=True)

    def _bars(
        self,
        security_ids: list[str],
        trading_dates: pd.DatetimeIndex,
        config: RQDataSyncConfig,
        progress=None,
    ) -> pd.DataFrame:
        chunks = list(self._chunks(security_ids, config.chunk_size))
        rows: list[pd.DataFrame] = []
        for index, security_chunk in enumerate(chunks):
            raw = self.client.get_price(
                security_chunk,
                config.start,
                config.end,
                frequency="1d",
                fields=[
                    "open",
                    "high",
                    "low",
                    "close",
                    "prev_close",
                    "volume",
                    "total_turnover",
                    "limit_up",
                    "limit_down",
                ],
                adjust_type="none",
                skip_suspended=False,
                expect_df=True,
            )
            adjusted = self.client.get_price(
                security_chunk,
                config.start,
                config.end,
                frequency="1d",
                fields=["close"],
                adjust_type="pre",
                skip_suspended=False,
                expect_df=True,
            ).rename(columns={"close": "adjusted_close"})
            suspended = self._wide_boolean(
                self.client.is_suspended(
                    security_chunk, config.start, config.end
                ),
                "is_suspended",
            )
            risk_warning = self._wide_boolean(
                self.client.is_st_stock(
                    security_chunk, config.start, config.end
                ),
                "is_risk_warning",
            )
            shares = self.client.get_shares(
                security_chunk,
                config.start,
                config.end,
                fields=["total", "circulation_a"],
                expect_df=True,
            )
            frame = (
                raw.join(adjusted, how="left")
                .join(suspended, how="left")
                .join(risk_warning, how="left")
                .join(shares, how="left")
                .reset_index()
            )
            frame = frame.rename(columns={
                "order_book_id": "security_id",
                "date": "trade_date",
                "open": "open_raw",
                "high": "high_raw",
                "low": "low_raw",
                "close": "close_raw",
                "prev_close": "prev_close_raw",
                "total_turnover": "amount",
                "limit_up": "limit_up_price",
                "limit_down": "limit_down_price",
            })
            frame["adjust_factor"] = (
                frame["adjusted_close"] / frame["close_raw"]
            ).replace([np.inf, -np.inf], np.nan).fillna(1.0)
            frame["is_suspended"] = frame["is_suspended"].fillna(False)
            frame["is_risk_warning"] = frame[
                "is_risk_warning"
            ].fillna(False)
            frame[["total", "circulation_a"]] = (
                frame.sort_values(["security_id", "trade_date"])
                .groupby("security_id")[["total", "circulation_a"]]
                .ffill()
            )
            frame["market_cap"] = (
                frame["close_raw"] * frame["total"]
            )
            frame["float_market_cap"] = (
                frame["close_raw"] * frame["circulation_a"]
            )
            frame["is_delisting"] = False
            rows.append(frame[[
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
            ]])
            if progress:
                progress(
                    "prices",
                    0.15 + 0.48 * (index + 1) / len(chunks),
                )
        return pd.concat(rows, ignore_index=True)

    def _fundamentals(
        self,
        security_ids: list[str],
        trading_dates: pd.DatetimeIndex,
        config: RQDataSyncConfig,
    ) -> pd.DataFrame:
        snapshot_dates = self._monthly_last_dates(trading_dates)
        rows: list[pd.DataFrame] = []
        for snapshot_date in snapshot_dates:
            factors = self.client.get_factor(
                security_ids,
                self.FACTOR_FIELDS,
                snapshot_date,
                snapshot_date,
                expect_df=True,
            ).reset_index()
            rows.append(factors)
        if not rows:
            return pd.DataFrame()
        frame = pd.concat(rows, ignore_index=True).rename(columns={
            "order_book_id": "security_id",
            "return_on_equity_ttm": "roe_ttm",
            "gross_profit_margin_ttm": "gross_margin",
            "operating_cash_flow_per_share_ttm": (
                "operating_cash_flow_per_share"
            ),
            "debt_to_asset_ratio": "debt_ratio",
            "operating_revenue_growth_ratio_ttm": "revenue_growth",
            "net_profit_growth_ratio_ttm": "profit_growth",
        })
        frame["debt_ratio"] = np.where(
            frame["debt_ratio"].abs() > 2,
            frame["debt_ratio"] / 100.0,
            frame["debt_ratio"],
        )
        frame["earnings_yield"] = np.where(
            frame["pe_ratio"] > 0, 1.0 / frame["pe_ratio"], np.nan
        )
        frame["book_to_price"] = np.where(
            frame["pb_ratio"] > 0, 1.0 / frame["pb_ratio"], np.nan
        )
        frame["report_period"] = frame["date"]
        frame["announcement_time"] = frame["date"]
        frame["available_time"] = frame["date"]
        frame["revision_time"] = frame["date"]
        return frame.drop(columns=["date"]).sort_values(
            ["available_time", "security_id"]
        ).reset_index(drop=True)

    def _industry_history(
        self,
        security_ids: list[str],
        trading_dates: pd.DatetimeIndex,
        config: RQDataSyncConfig,
    ) -> pd.DataFrame:
        monthly_dates = self._monthly_last_dates(trading_dates).tolist()
        if trading_dates[0] not in monthly_dates:
            monthly_dates.insert(0, trading_dates[0])
        rows: list[pd.DataFrame] = []
        for effective_date in monthly_dates:
            industry = self.client.get_instrument_industry(
                security_ids,
                source=config.industry_source,
                level=config.industry_level,
                date=effective_date,
            )
            if industry is None or industry.empty:
                continue
            industry = industry.reset_index().rename(columns={
                "order_book_id": "security_id",
                "first_industry_name": "industry",
            })
            industry["effective_date"] = effective_date
            rows.append(
                industry[["security_id", "effective_date", "industry"]]
            )
        if not rows:
            return pd.DataFrame(
                columns=["security_id", "effective_date", "industry"]
            )
        return pd.concat(rows, ignore_index=True).drop_duplicates(
            ["security_id", "effective_date"], keep="last"
        )

    def _benchmark(self, config: RQDataSyncConfig) -> pd.DataFrame:
        benchmark = self.client.get_price(
            config.benchmark_id,
            config.start,
            config.end,
            frequency="1d",
            fields=["close"],
            adjust_type="none",
            expect_df=True,
        ).reset_index()
        return benchmark.rename(columns={
            "date": "trade_date",
            "order_book_id": "benchmark_id",
        })

    def _corporate_actions(
        self, security_ids: list[str], config: RQDataSyncConfig
    ) -> pd.DataFrame:
        dividend_rows: list[pd.DataFrame] = []
        split_rows: list[pd.DataFrame] = []
        for security_chunk in self._chunks(
            security_ids, config.chunk_size
        ):
            dividend_query_start = (
                pd.Timestamp(config.start) - pd.DateOffset(years=1)
            ).strftime("%Y-%m-%d")
            dividends = self.client.get_dividend(
                security_chunk,
                dividend_query_start,
                config.end,
                expect_df=True,
            )
            if dividends is not None and not dividends.empty:
                item = dividends.reset_index()
                item["cash_dividend_per_share"] = (
                    item["dividend_cash_before_tax"]
                    / item["round_lot"].replace(0, np.nan)
                )
                item = item.rename(columns={
                    "order_book_id": "security_id",
                    "ex_dividend_date": "ex_date",
                })
                item["ex_date"] = pd.to_datetime(item["ex_date"])
                item = item[
                    item["ex_date"].between(
                        pd.Timestamp(config.start),
                        pd.Timestamp(config.end),
                    )
                ]
                dividend_rows.append(
                    item[[
                        "security_id",
                        "ex_date",
                        "cash_dividend_per_share",
                    ]]
                )
            splits = self.client.get_split(
                security_chunk, config.start, config.end
            )
            if splits is not None and not splits.empty:
                item = splits.reset_index().rename(columns={
                    "order_book_id": "security_id",
                    "ex_dividend_date": "ex_date",
                })
                item["split_ratio"] = (
                    item["split_coefficient_to"]
                    / item["split_coefficient_from"].replace(0, np.nan)
                )
                split_rows.append(
                    item[["security_id", "ex_date", "split_ratio"]]
                )
        actions = []
        if dividend_rows:
            actions.append(pd.concat(dividend_rows, ignore_index=True))
        if split_rows:
            actions.append(pd.concat(split_rows, ignore_index=True))
        if not actions:
            return pd.DataFrame(
                columns=[
                    "security_id",
                    "ex_date",
                    "cash_dividend_per_share",
                    "split_ratio",
                ]
            )
        frame = pd.concat(actions, ignore_index=True)
        if "cash_dividend_per_share" not in frame:
            frame["cash_dividend_per_share"] = 0.0
        if "split_ratio" not in frame:
            frame["split_ratio"] = 1.0
        return (
            frame.groupby(["security_id", "ex_date"], as_index=False)
            .agg({
                "cash_dividend_per_share": "sum",
                "split_ratio": "max",
            })
            .fillna({
                "cash_dividend_per_share": 0.0,
                "split_ratio": 1.0,
            })
        )

    @staticmethod
    def _wide_boolean(
        frame: pd.DataFrame, name: str
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame(columns=[name])
        stacked = frame.rename_axis("date").stack(
            future_stack=True
        ).rename(name).to_frame()
        stacked.index = stacked.index.set_names(
            ["date", "order_book_id"]
        )
        return stacked.reorder_levels(
            ["order_book_id", "date"]
        ).sort_index()

    @staticmethod
    def _monthly_last_dates(
        dates: pd.DatetimeIndex,
    ) -> pd.DatetimeIndex:
        frame = pd.DataFrame({
            "date": dates,
            "period": dates.to_period("M"),
        })
        return pd.DatetimeIndex(
            frame.groupby("period")["date"].max().tolist()
        )

    @staticmethod
    def _chunks(items: list[str], size: int):
        for start in range(0, len(items), size):
            yield items[start : start + size]

    @staticmethod
    def _merge_existing(
        output: Path, incoming: DatasetBundle
    ) -> DatasetBundle:
        existing = DatasetBundle.load(output)

        def merge(
            old: pd.DataFrame,
            new: pd.DataFrame,
            keys: list[str],
        ) -> pd.DataFrame:
            if old.empty:
                return new.copy()
            if new.empty:
                return old.copy()
            return (
                pd.concat([old, new], ignore_index=True)
                .drop_duplicates(keys, keep="last")
                .reset_index(drop=True)
            )

        bundle = DatasetBundle(
            securities=merge(
                existing.securities,
                incoming.securities,
                ["security_id"],
            ),
            bars=merge(
                existing.bars,
                incoming.bars,
                ["security_id", "trade_date"],
            ),
            fundamentals=merge(
                existing.fundamentals,
                incoming.fundamentals,
                ["security_id", "available_time"],
            ),
            benchmark=merge(
                existing.benchmark,
                incoming.benchmark,
                ["trade_date"],
            ),
            corporate_actions=merge(
                existing.corporate_actions,
                incoming.corporate_actions,
                ["security_id", "ex_date"],
            ),
            industry_history=merge(
                existing.industry_history,
                incoming.industry_history,
                ["security_id", "effective_date"],
            ),
            source=incoming.source,
        )
        bundle.normalize()
        bundle.validate()
        return bundle
