from __future__ import annotations

import uuid
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from a_share_quant.alpha import AlphaEngine
from a_share_quant.contracts.models import (
    ExecutionProfile,
    StrategyConfig,
    UniverseConfig,
)
from a_share_quant.data import DatasetBundle
from a_share_quant.features import FeatureEngine
from a_share_quant.monitoring import data_health
from a_share_quant.portfolio import PortfolioBuilder
from a_share_quant.regime import RegimeEngine
from a_share_quant.risk import RiskEngine
from a_share_quant.storage.artifacts import ArtifactStore
from a_share_quant.storage.metadata import MetadataStore
from a_share_quant.universe import UniverseEngine


class DailyPipeline:
    def __init__(
        self,
        universe: UniverseConfig,
        strategy: StrategyConfig,
        execution: ExecutionProfile,
        artifact_root: str | Path = "artifacts",
        metadata_path: str | Path = "storage/metadata/system.db",
    ) -> None:
        self.universe_config = universe
        self.strategy = strategy
        self.execution = execution
        self.artifacts = ArtifactStore(artifact_root)
        self.metadata = MetadataStore(metadata_path)

    def run(self, dataset: str | Path, as_of: pd.Timestamp | None = None) -> dict[str, object]:
        bundle = DatasetBundle.load(dataset)
        trade_dates = bundle.trade_dates
        if as_of is None:
            as_of = trade_dates[-1]
        else:
            eligible = trade_dates[trade_dates <= pd.Timestamp(as_of)]
            if len(eligible) == 0:
                raise ValueError("as_of is before the first trading session")
            as_of = eligible[-1]
        health = data_health(bundle, as_of)
        if not health["passed"]:
            alert_id = self.metadata.create_alert(
                "critical", "DATA_HEALTH_FAILED", str(health)
            )
            raise RuntimeError(f"daily run blocked by data health; alert={alert_id}")
        universe = UniverseEngine(self.universe_config).build(bundle, as_of)
        features = FeatureEngine(self.strategy.feature).compute(bundle, universe.members, as_of)
        scored = AlphaEngine(self.strategy.alpha).score(features)
        regime = RegimeEngine(self.strategy.regime).classify(bundle, as_of)
        portfolio = PortfolioBuilder(self.strategy.portfolio).build(
            scored, regime.target_exposure
        )
        risk = RiskEngine(self.strategy.portfolio).validate(
            portfolio.target_weights, nav=1_000_000
        )
        if not risk.passed:
            self.metadata.create_alert(
                "critical", "DAILY_RISK_FAILED", ",".join(risk.violations)
            )
            raise RuntimeError("daily run blocked by risk validation")
        run_id = f"daily_{pd.Timestamp(as_of).strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        recommendations = portfolio.target_weights.copy()
        recommendations["as_of"] = as_of
        recommendations["target_notional_per_1m"] = (
            recommendations["target_weight"] * 1_000_000
        )
        recommendations["indicative_quantity"] = (
            recommendations["target_notional_per_1m"]
            / recommendations["close"]
            / self.execution.lot_size
        ).fillna(0).astype(int) * self.execution.lot_size
        recommendations["review_status"] = "PENDING_HUMAN_REVIEW"
        recommendations["broker_submission"] = "DISABLED"
        references = {
            "recommendations": self.artifacts.write_frame(
                run_id, "recommendations", recommendations
            ),
            "scores": self.artifacts.write_frame(run_id, "scores", scored),
            "exclusions": self.artifacts.write_frame(
                run_id, "exclusions", universe.exclusions
            ),
        }
        summary: dict[str, object] = {
            "run_id": run_id,
            "as_of": str(pd.Timestamp(as_of).date()),
            "regime": asdict(regime),
            "universe": universe.summary,
            "portfolio": portfolio.diagnostics,
            "risk": asdict(risk),
            "data_health": health,
            "artifacts": references,
            "broker_submission": "disabled",
        }
        references["summary"] = self.artifacts.write_json(run_id, "daily_summary", summary)
        self.metadata.audit(
            "system", "daily_recommendations_generated", "daily_run", run_id,
            {"as_of": summary["as_of"], "broker_submission": "disabled"},
        )
        return summary
