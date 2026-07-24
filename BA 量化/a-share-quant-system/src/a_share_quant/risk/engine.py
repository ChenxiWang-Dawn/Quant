from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from a_share_quant.contracts.models import PortfolioConfig


@dataclass(slots=True)
class RiskReport:
    passed: bool
    violations: list[str]
    metrics: dict[str, float | int]


class RiskEngine:
    def __init__(self, config: PortfolioConfig) -> None:
        self.config = config

    def validate(self, targets: pd.DataFrame, nav: float) -> RiskReport:
        if targets.empty:
            return RiskReport(True, [], {"holdings": 0, "exposure": 0.0})
        violations: list[str] = []
        weights = targets["target_weight"].astype(float)
        if (weights < -1e-12).any():
            violations.append("short_position_not_allowed")
        if weights.max() > self.config.max_stock_weight + 1e-9:
            violations.append("single_name_cap_exceeded")
        if "industry" in targets:
            sector = targets.groupby(targets["industry"].fillna("UNKNOWN"))["target_weight"].sum()
            if sector.max() > self.config.max_sector_weight + 1e-9:
                violations.append("industry_cap_exceeded")
        if "adv20" in targets and (
            weights * nav
            > targets["adv20"].fillna(0) * self.config.max_adv_participation
        ).any():
            violations.append("adv_participation_exceeded")
        return RiskReport(
            not violations,
            violations,
            {
                "holdings": len(targets),
                "exposure": float(weights.sum()),
                "max_stock_weight": float(weights.max()),
            },
        )

    @staticmethod
    def drawdown_exposure_multiplier(drawdown: float) -> float:
        if drawdown >= 0.20:
            return 0.25
        if drawdown >= 0.15:
            return 0.50
        if drawdown >= 0.10:
            return 0.75
        return 1.0
