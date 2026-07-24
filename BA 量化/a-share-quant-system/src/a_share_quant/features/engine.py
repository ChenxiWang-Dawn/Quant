from __future__ import annotations

import numpy as np
import pandas as pd

from a_share_quant.contracts.models import FeatureConfig
from a_share_quant.data.dataset import DatasetBundle


class FeatureEngine:
    def __init__(self, config: FeatureConfig) -> None:
        self.config = config
        self._technical_by_date: dict[pd.Timestamp, pd.DataFrame] = {}

    def prepare(
        self,
        bundle: DatasetBundle,
        as_of_dates: set[pd.Timestamp],
    ) -> None:
        if not as_of_dates:
            self._technical_by_date = {}
            return
        dates = {pd.Timestamp(item).normalize() for item in as_of_dates}
        bars = bundle.bars_until(max(dates)).copy()
        bars = bars.sort_values(["security_id", "trade_date"])
        bars["adj_close"] = (
            bars["close_raw"] * bars["adjust_factor"].fillna(1.0)
        )
        security = bars["security_id"]
        grouped = bars.groupby("security_id", sort=False)
        bars["mom20"] = bars["adj_close"] / grouped[
            "adj_close"
        ].shift(20) - 1.0
        bars["mom60"] = bars["adj_close"] / grouped[
            "adj_close"
        ].shift(60) - 1.0
        bars["mom120_20"] = (
            grouped["adj_close"].shift(20)
            / grouped["adj_close"].shift(120)
            - 1.0
        )
        one_day_return = grouped["adj_close"].pct_change()
        bars["vol20"] = (
            one_day_return.groupby(security, sort=False)
            .rolling(20)
            .std(ddof=0)
            .reset_index(level=0, drop=True)
            * np.sqrt(252)
        )
        previous_close = grouped["adj_close"].shift(1)
        bars["previous_high60"] = (
            previous_close.groupby(security, sort=False)
            .rolling(60, min_periods=40)
            .max()
            .reset_index(level=0, drop=True)
        )
        for window in (5, 20, 60):
            bars[f"volume_mean{window}"] = (
                bars["volume"].groupby(security, sort=False)
                .rolling(window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )
        for window, minimum in ((20, 15), (60, 40)):
            bars[f"ma{window}"] = (
                bars["adj_close"].groupby(security, sort=False)
                .rolling(window, min_periods=minimum)
                .mean()
                .reset_index(level=0, drop=True)
            )
        bars["adv20"] = (
            bars["amount"].groupby(security, sort=False)
            .rolling(20, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        bars["volume_ratio20"] = (
            bars["volume_mean5"] / bars["volume_mean20"].clip(lower=1.0)
        )
        bars["breakout60"] = (
            bars["adj_close"] / bars["previous_high60"] - 1.0
        ).fillna(0.0)
        bars["ma20_distance"] = (
            bars["adj_close"] / bars["ma20"] - 1.0
        ).fillna(0.0)
        bars["ma60_distance"] = (
            bars["adj_close"] / bars["ma60"] - 1.0
        ).fillna(0.0)
        for column in ("mom20", "mom60", "mom120_20"):
            bars[column] = bars[column].fillna(0.0)
        selected = bars[bars["trade_date"].isin(dates)].rename(
            columns={"close_raw": "close"}
        )
        columns = [
            "security_id",
            "close",
            "adv20",
            "mom20",
            "mom60",
            "mom120_20",
            "vol20",
            "volume_ratio20",
            "breakout60",
            "ma20_distance",
            "ma60_distance",
        ]
        self._technical_by_date = {
            pd.Timestamp(date): frame[columns].reset_index(drop=True)
            for date, frame in selected.groupby("trade_date", sort=False)
        }

    def compute(
        self, bundle: DatasetBundle, universe: pd.DataFrame, as_of: pd.Timestamp
    ) -> pd.DataFrame:
        security_ids = set(universe["security_id"].astype(str))
        as_of = pd.Timestamp(as_of).normalize()
        prepared = self._technical_by_date.get(as_of)
        if prepared is None:
            prepared = self._compute_technical(bundle, security_ids, as_of)
        else:
            prepared = prepared[
                prepared["security_id"].astype(str).isin(security_ids)
            ].copy()
        if prepared.empty:
            return pd.DataFrame()
        features = prepared.merge(universe, on="security_id", how="left")
        fundamentals = bundle.latest_fundamentals(pd.Timestamp(as_of))
        if not fundamentals.empty:
            fundamentals = fundamentals.reset_index(drop=False)
            features = features.merge(fundamentals, on="security_id", how="left")
        primitive_groups = {
            "quality": (
                [
                "roe_ttm",
                "gross_margin",
                "cfo_to_profit",
                "operating_cash_flow_per_share",
                "roic_ttm",
                ],
                ["debt_ratio"],
            ),
            "value": (
                ["earnings_yield", "book_to_price", "fcf_yield"],
                [],
            ),
            "momentum": (["mom60", "mom120_20"], []),
            "earnings": (
                ["revenue_growth", "profit_growth", "earnings_revision"],
                [],
            ),
        }
        primitive_columns = list(dict.fromkeys(
            column
            for positive, negative in primitive_groups.values()
            for column in positive + negative
            if column in features and features[column].notna().any()
        ))
        primitive_z = self._transform_many(features, primitive_columns)
        for sleeve, (positive, negative) in primitive_groups.items():
            features[f"{sleeve}_raw"] = self._composite_from(
                primitive_z, positive, negative, features.index
            )
        features["breakout_raw"] = (
            features["breakout60"]
            + 0.25 * np.log(features["volume_ratio20"].clip(lower=0.01))
            + 0.20 * features["ma60_distance"]
        )
        features["risk_penalty_raw"] = (
            features["vol20"].fillna(features["vol20"].median())
            + features["ma20_distance"].clip(lower=0.15).fillna(0)
        )
        sleeves = (
            "quality",
            "value",
            "momentum",
            "earnings",
            "breakout",
            "risk_penalty",
        )
        raw_columns = [f"{sleeve}_raw" for sleeve in sleeves]
        transformed_sleeves = self._transform_many(features, raw_columns)
        for sleeve in sleeves:
            features[f"{sleeve}_z"] = transformed_sleeves[
                f"{sleeve}_raw"
            ]
        return features.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)

    def _compute_technical(
        self,
        bundle: DatasetBundle,
        security_ids: set[str],
        as_of: pd.Timestamp,
    ) -> pd.DataFrame:
        bars = bundle.bars_until(as_of, lookback=260)
        bars = bars[
            bars["security_id"].astype(str).isin(security_ids)
        ].copy()
        if bars.empty:
            return pd.DataFrame()
        bars = bars.sort_values(["security_id", "trade_date"])
        bars["adj_close"] = (
            bars["close_raw"] * bars["adjust_factor"].fillna(1.0)
        )
        records: list[dict[str, float | str]] = []
        for security_id, group in bars.groupby(
            "security_id", sort=False
        ):
            group = group.tail(260)
            close = group["adj_close"].astype(float)
            raw_close = group["close_raw"].astype(float)
            returns = close.pct_change()
            previous_high = close.shift(1).rolling(
                60, min_periods=40
            ).max()
            ma20 = close.rolling(20, min_periods=15).mean()
            ma60 = close.rolling(60, min_periods=40).mean()
            records.append({
                "security_id": str(security_id),
                "close": float(raw_close.iloc[-1]),
                "adv20": float(group["amount"].tail(20).mean()),
                "mom20": self._return(close, 20),
                "mom60": self._return(close, 60),
                "mom120_20": self._skip_return(close, 120, 20),
                "vol20": float(
                    returns.tail(20).std(ddof=0) * np.sqrt(252)
                ),
                "volume_ratio20": float(
                    group["volume"].tail(5).mean()
                    / max(group["volume"].tail(20).mean(), 1.0)
                ),
                "breakout60": (
                    float(close.iloc[-1] / previous_high.iloc[-1] - 1)
                    if pd.notna(previous_high.iloc[-1])
                    else 0.0
                ),
                "ma20_distance": (
                    float(close.iloc[-1] / ma20.iloc[-1] - 1)
                    if pd.notna(ma20.iloc[-1])
                    else 0.0
                ),
                "ma60_distance": (
                    float(close.iloc[-1] / ma60.iloc[-1] - 1)
                    if pd.notna(ma60.iloc[-1])
                    else 0.0
                ),
            })
        return pd.DataFrame(records)

    @staticmethod
    def _return(close: pd.Series, days: int) -> float:
        if len(close) <= days or close.iloc[-days - 1] <= 0:
            return 0.0
        return float(close.iloc[-1] / close.iloc[-days - 1] - 1)

    @staticmethod
    def _skip_return(close: pd.Series, long_days: int, skip_days: int) -> float:
        if len(close) <= long_days or close.iloc[-long_days - 1] <= 0:
            return 0.0
        return float(close.iloc[-skip_days - 1] / close.iloc[-long_days - 1] - 1)

    def _transform(self, frame: pd.DataFrame, column: str) -> pd.Series:
        return self._transform_many(frame, [column])[column]

    def _transform_many(
        self,
        frame: pd.DataFrame,
        columns: list[str],
    ) -> pd.DataFrame:
        result = pd.DataFrame(0.0, index=frame.index, columns=columns)
        usable: list[str] = []
        values_by_column: dict[str, pd.Series] = {}
        for column in columns:
            values = frame[column].astype(float).replace(
                [np.inf, -np.inf], np.nan
            )
            if values.notna().sum() < 2:
                continue
            lower, upper = values.quantile([
                self.config.winsor_lower,
                self.config.winsor_upper,
            ])
            values_by_column[column] = values.clip(
                lower=lower, upper=upper
            ).fillna(values.median())
            usable.append(column)
        if not usable:
            return result
        design_parts: list[pd.DataFrame | pd.Series] = [
            pd.Series(1.0, index=frame.index, name="intercept")
        ]
        if self.config.neutralize_industry and "industry" in frame:
            design_parts.append(
                pd.get_dummies(frame["industry"].fillna("UNKNOWN"), drop_first=True, dtype=float)
            )
        if self.config.neutralize_log_market_cap and "float_market_cap" in frame:
            log_cap = np.log(
                frame["float_market_cap"].astype(float).clip(lower=1.0)
            ).replace([np.inf, -np.inf], np.nan)
            design_parts.append(
                log_cap.fillna(log_cap.median()).fillna(0.0).rename("log_cap")
            )
        design = pd.concat(design_parts, axis=1).astype(float)
        values_matrix = pd.DataFrame(
            values_by_column, index=frame.index
        )[usable].to_numpy()
        coefficients, *_ = np.linalg.lstsq(
            design.to_numpy(), values_matrix, rcond=None
        )
        residual = pd.DataFrame(
            values_matrix - design.to_numpy() @ coefficients,
            index=frame.index,
            columns=usable,
        )
        deviation = residual.std(axis=0, ddof=0)
        safe = deviation.where(deviation > 1e-12)
        normalized = (
            residual.subtract(residual.mean(axis=0), axis=1)
            .divide(safe, axis=1)
            .fillna(0.0)
        )
        result.loc[:, usable] = normalized
        return result

    @staticmethod
    def _composite_from(
        transformed: pd.DataFrame,
        positive: list[str],
        negative: list[str],
        index: pd.Index,
    ) -> pd.Series:
        positive_columns = [
            column for column in positive if column in transformed
        ]
        negative_columns = [
            column for column in negative if column in transformed
        ]
        if not positive_columns and not negative_columns:
            return pd.Series(0.0, index=index)
        result = (
            transformed[positive_columns].mean(axis=1)
            if positive_columns
            else pd.Series(0.0, index=index)
        )
        if negative_columns:
            result = result - transformed[negative_columns].mean(axis=1)
        return result.fillna(0.0)
