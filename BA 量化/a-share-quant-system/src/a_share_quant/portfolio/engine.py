from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from a_share_quant.contracts.models import PortfolioConfig


@dataclass(slots=True)
class PortfolioResult:
    target_weights: pd.DataFrame
    diagnostics: dict[str, float | int | str | bool]


class PortfolioBuilder:
    def __init__(self, config: PortfolioConfig) -> None:
        self.config = config

    def build(
        self,
        scored: pd.DataFrame,
        target_exposure: float,
        current_weights: dict[str, float] | None = None,
    ) -> PortfolioResult:
        current_weights = current_weights or {}
        if scored.empty:
            return PortfolioResult(
                pd.DataFrame(columns=["security_id", "target_weight"]),
                {"status": "empty", "target_exposure": target_exposure},
            )
        candidates = self._select_candidates(scored, current_weights)
        if self.config.builder == "optimized":
            weights, optimized = self._optimize(candidates, target_exposure, current_weights)
        else:
            weights, optimized = self._topk(candidates, target_exposure), False
        result = candidates.copy()
        result["target_weight"] = weights
        result = result[result["target_weight"] > 1e-10].copy()
        all_ids = set(result["security_id"].astype(str)) | set(current_weights)
        target_map = dict(zip(result["security_id"].astype(str), result["target_weight"]))
        turnover = sum(
            abs(float(target_map.get(item, 0.0)) - current_weights.get(item, 0.0))
            for item in all_ids
        ) / 2
        diagnostics: dict[str, float | int | str | bool] = {
            "status": "ok",
            "builder": self.config.builder,
            "optimized": optimized,
            "holdings": len(result),
            "target_exposure": float(target_exposure),
            "actual_exposure": float(result["target_weight"].sum()),
            "one_way_turnover": float(turnover),
        }
        return PortfolioResult(
            result.sort_values("target_weight", ascending=False).reset_index(drop=True),
            diagnostics,
        )

    def _select_candidates(
        self, scored: pd.DataFrame, current_weights: dict[str, float]
    ) -> pd.DataFrame:
        retained = scored[
            scored["security_id"].astype(str).isin(current_weights)
            & (scored["alpha_rank"] <= self.config.exit_rank)
        ]
        needed = max(0, self.config.target_holdings - len(retained))
        retained_ids = set(retained["security_id"].astype(str))
        new = scored[~scored["security_id"].astype(str).isin(retained_ids)].head(needed)
        return pd.concat([retained, new], ignore_index=True).sort_values(
            "alpha_rank"
        ).head(self.config.target_holdings).reset_index(drop=True)

    def _topk(self, candidates: pd.DataFrame, target_exposure: float) -> np.ndarray:
        count = len(candidates)
        if not count:
            return np.array([])
        desired = min(target_exposure, self.config.max_stock_weight * count)
        weights = np.full(count, desired / count)
        return self._enforce_industry_caps(candidates, weights, desired)

    def _optimize(
        self,
        candidates: pd.DataFrame,
        target_exposure: float,
        current_weights: dict[str, float],
    ) -> tuple[np.ndarray, bool]:
        count = len(candidates)
        desired = min(target_exposure, self.config.max_stock_weight * count)
        base = self._topk(candidates, desired)
        alpha = candidates["alpha_score"].to_numpy(dtype=float)
        alpha = (alpha - alpha.mean()) / max(alpha.std(), 1e-8)
        volatility = candidates.get(
            "vol20", pd.Series(0.30, index=candidates.index)
        ).fillna(0.30).to_numpy()
        current = np.array([
            current_weights.get(str(item), 0.0) for item in candidates["security_id"]
        ])

        def objective(weights: np.ndarray) -> float:
            return (
                -float(weights @ alpha)
                + 2.0 * float(np.sum((weights * volatility) ** 2))
                + 0.15 * float(np.sum(np.sqrt((weights - current) ** 2 + 1e-8)))
            )

        constraints: list[dict[str, object]] = [
            {"type": "eq", "fun": lambda weights: np.sum(weights) - desired},
            {
                "type": "ineq",
                "fun": lambda weights: self.config.max_weekly_one_way_turnover
                - np.sum(np.abs(weights - current)) / 2,
            },
        ]
        if "industry" in candidates:
            industries = candidates["industry"].fillna("UNKNOWN")
            for industry in industries.unique():
                mask = (industries == industry).to_numpy(dtype=float)
                constraints.append({
                    "type": "ineq",
                    "fun": lambda weights, mask=mask: self.config.max_sector_weight
                    - float(weights @ mask),
                })
        solution = minimize(
            objective, base, method="SLSQP",
            bounds=[(0.0, self.config.max_stock_weight)] * count,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-10},
        )
        return (solution.x, True) if solution.success else (base, False)

    def _enforce_industry_caps(
        self, candidates: pd.DataFrame, weights: np.ndarray, target: float
    ) -> np.ndarray:
        if "industry" not in candidates or len(weights) == 0:
            return weights
        weights = weights.copy()
        industries = candidates["industry"].fillna("UNKNOWN").to_numpy()
        for _ in range(20):
            excess = 0.0
            for industry in np.unique(industries):
                mask = industries == industry
                total = weights[mask].sum()
                if total > self.config.max_sector_weight:
                    excess += total - self.config.max_sector_weight
                    weights[mask] *= self.config.max_sector_weight / total
            room = np.minimum(
                self.config.max_stock_weight - weights,
                np.array([
                    self.config.max_sector_weight - weights[industries == item].sum()
                    for item in industries
                ]),
            ).clip(min=0.0)
            if excess <= 1e-12 or room.sum() <= 1e-12:
                break
            weights += room / room.sum() * min(excess, room.sum())
        if weights.sum() > target:
            weights *= target / weights.sum()
        return weights
