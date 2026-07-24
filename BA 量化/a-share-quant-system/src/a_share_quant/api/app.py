from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from a_share_quant.config import load_execution, load_strategy, load_universe
from a_share_quant.contracts.models import BacktestRequest
from a_share_quant.daily import DailyPipeline
from a_share_quant.data import DatasetBundle
from a_share_quant.jobs import JobManager
from a_share_quant.monitoring import data_health
from a_share_quant.services import RunService
from a_share_quant.universe import UniverseEngine

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class DatasetRequest(BaseModel):
    dataset: str
    as_of: str | None = None


def create_app(
    artifact_root: str | Path = "artifacts",
    metadata_path: str | Path = "storage/metadata/system.db",
) -> FastAPI:
    service = RunService(artifact_root, metadata_path)
    jobs = JobManager(service)
    app = FastAPI(
        title="A-Share Quant System",
        version="0.1.0",
        description="Research, backtest, shadow recommendations and audit API. Broker submission is disabled.",
    )
    app.state.service = service
    app.state.jobs = jobs

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "broker_submission": "disabled"}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "data_sources": ["local_parquet", "local_csv"],
            "portfolio_builders": ["topk", "optimized"],
            "execution": [
                "t_plus_one", "price_limits", "suspension", "lot_size",
                "fees", "slippage", "market_impact", "partial_fill",
            ],
            "modes": ["research", "backtest", "shadow", "order_preview"],
            "broker_submission": "disabled",
        }

    @app.get("/v1/strategy-manifests")
    def strategy_manifests() -> list[dict]:
        strategy = load_strategy(
            PROJECT_ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml"
        )
        return [strategy.model_dump(mode="json")]

    @app.post("/v1/datasets/snapshots")
    def dataset_snapshot(request: DatasetRequest) -> dict:
        bundle = DatasetBundle.load(request.dataset)
        return {
            "fingerprint": bundle.fingerprint,
            "source": bundle.source,
            "health": data_health(bundle),
        }

    @app.post("/v1/universes")
    def universe_snapshot(request: DatasetRequest) -> dict:
        bundle = DatasetBundle.load(request.dataset)
        as_of = request.as_of or str(bundle.trade_dates[-1].date())
        config = load_universe(
            PROJECT_ROOT / "configs/universes/cn_a_share_liquid_v1.yaml"
        )
        result = UniverseEngine(config).build(bundle, as_of)
        return {
            "summary": result.summary,
            "members": result.members.to_dict(orient="records"),
            "exclusions": result.exclusions.to_dict(orient="records"),
        }

    @app.post("/v1/backtests", status_code=202)
    def submit_backtest(request: BacktestRequest) -> dict:
        return jobs.submit_backtest(request).model_dump(mode="json")

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        try:
            return service.metadata.get_job(job_id).model_dump(mode="json")
        except KeyError as error:
            raise HTTPException(status_code=404, detail="job not found") from error

    @app.post("/v1/jobs/{job_id}/cancel", status_code=202)
    def cancel_job(job_id: str) -> dict:
        try:
            return jobs.cancel(job_id).model_dump(mode="json")
        except KeyError as error:
            raise HTTPException(status_code=404, detail="job not found") from error

    @app.get("/v1/experiments")
    def experiments() -> list[dict]:
        return service.metadata.list_experiments()

    @app.post("/v1/shadow-runs")
    @app.post("/v1/order-plans/preview")
    def shadow_run(request: DatasetRequest) -> dict:
        pipeline = DailyPipeline(
            load_universe(PROJECT_ROOT / "configs/universes/cn_a_share_liquid_v1.yaml"),
            load_strategy(
                PROJECT_ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml"
            ),
            load_execution(
                PROJECT_ROOT / "configs/execution/cn_a_share_base_2026.yaml"
            ),
            artifact_root,
            metadata_path,
        )
        return pipeline.run(request.dataset, request.as_of)

    @app.get("/v1/monitoring/summary")
    def monitoring_summary() -> dict:
        experiments = service.metadata.list_experiments()
        alerts = service.metadata.list_alerts()
        return {
            "experiments": len(experiments),
            "latest_experiment": experiments[0] if experiments else None,
            "open_alerts": len(alerts),
            "broker_submission": "disabled",
        }

    @app.get("/v1/alerts")
    def alerts() -> list[dict]:
        return service.metadata.list_alerts()

    return app


app = create_app()
