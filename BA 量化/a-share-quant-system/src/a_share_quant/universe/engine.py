from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from a_share_quant.contracts.models import UniverseConfig
from a_share_quant.data.dataset import DatasetBundle


@dataclass(slots=True)
class UniverseResult:
    members: pd.DataFrame
    exclusions: pd.DataFrame
    summary: dict[str, int | float | str]


class UniverseEngine:
    def __init__(self, config: UniverseConfig) -> None:
        self.config = config

    def build(self, bundle: DatasetBundle, as_of: pd.Timestamp) -> UniverseResult:
        as_of = pd.Timestamp(as_of).normalize()
        bars = bundle.bars_until(as_of, lookback=20)
        if bars.empty:
            return UniverseResult(
                pd.DataFrame(columns=["security_id"]),
                pd.DataFrame(columns=["security_id", "reason"]),
                {"as_of": str(as_of.date()), "eligible": 0, "excluded": 0},
            )
        latest = bars.groupby("security_id", as_index=False).tail(1)
        recent = bars.groupby("security_id", as_index=False).tail(20)
        liquidity = recent.groupby("security_id").agg(
            adv20=("amount", "mean"),
            valid_days20=("close_raw", lambda values: int(values.notna().sum())),
        )
        frame = bundle.securities_as_of(as_of).merge(
            latest, on="security_id", how="inner"
        )
        frame = frame.merge(liquidity, on="security_id", how="left")
        frame["listing_days"] = (as_of - frame["list_date"]).dt.days
        for column in ("is_suspended", "is_risk_warning", "is_delisting"):
            frame[column] = frame[column].fillna(False).astype(bool)

        rules: list[tuple[str, pd.Series]] = [
            ("board_not_allowed", ~frame["board"].isin([item.value for item in self.config.allowed_boards])),
            ("new_listing", frame["listing_days"] < self.config.min_listing_days),
            ("low_price", frame["close_raw"] < self.config.min_price_cny),
            ("low_liquidity", frame["adv20"].fillna(0) < self.config.min_adv20_cny),
            ("insufficient_history", frame["valid_days20"].fillna(0) < self.config.min_valid_days_20),
        ]
        if self.config.exclude_risk_warning:
            rules.append(("risk_warning", frame["is_risk_warning"]))
        if self.config.exclude_delisting:
            rules.append(("delisting", frame["is_delisting"]))
        if self.config.exclude_suspended:
            rules.append(("suspended", frame["is_suspended"]))

        reason = pd.Series("", index=frame.index, dtype="object")
        excluded = pd.Series(False, index=frame.index)
        for name, mask in rules:
            mask = mask.fillna(True)
            reason = reason.mask(mask & ~excluded, name)
            excluded |= mask
        frame["eligible"] = ~excluded
        frame["exclusion_reason"] = reason
        keep = [
            column
            for column in [
                "security_id", "symbol", "exchange", "board", "industry",
                "float_market_cap", "close_raw", "adv20", "valid_days20",
                "listing_days", "eligible", "exclusion_reason",
            ]
            if column in frame
        ]
        members = frame.loc[frame["eligible"], keep].reset_index(drop=True)
        exclusions = frame.loc[~frame["eligible"], keep].reset_index(drop=True)
        summary: dict[str, int | float | str] = {
            "as_of": str(as_of.date()),
            "input": len(frame),
            "eligible": len(members),
            "excluded": len(exclusions),
            "median_adv20": float(np.nanmedian(members["adv20"])) if len(members) else 0.0,
        }
        return UniverseResult(members, exclusions, summary)
