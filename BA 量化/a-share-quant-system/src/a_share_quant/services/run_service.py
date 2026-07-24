from __future__ import annotations

import uuid
from dataclasses import asdict
from pathlib import Path

from a_share_quant.backtest import BacktestEngine, BacktestResult
from a_share_quant.contracts.models import BacktestRequest, JobStatus
from a_share_quant.data import DatasetBundle
from a_share_quant.storage.artifacts import ArtifactStore, content_hash
from a_share_quant.storage.metadata import MetadataStore


class RunService:
    def __init__(
        self,
        artifact_root: str | Path = "artifacts",
        metadata_path: str | Path = "storage/metadata/system.db",
    ) -> None:
        self.artifacts = ArtifactStore(artifact_root)
        self.metadata = MetadataStore(metadata_path)

    def run_backtest(
        self,
        request: BacktestRequest,
        *,
        run_id: str | None = None,
        job_id: str | None = None,
        progress_hook=None,
    ) -> tuple[str, BacktestResult, dict[str, str]]:
        run_id = run_id or f"run_{uuid.uuid4().hex}"
        if job_id:
            self.metadata.update_job(job_id, JobStatus.VALIDATING, progress=0.01)
        bundle = DatasetBundle.load(request.dataset)
        if job_id:
            self.metadata.update_job(job_id, JobStatus.RUNNING, progress=0.03)

        def report(value: float) -> None:
            if progress_hook:
                progress_hook(value)
            if job_id and (int(value * 100) % 5 == 0 or value >= 1.0):
                self.metadata.update_job(
                    job_id, JobStatus.RUNNING, progress=min(0.85, 0.03 + value * 0.82)
                )

        result = BacktestEngine(request).run(bundle, report)
        if job_id:
            self.metadata.update_job(job_id, JobStatus.EVALUATING, progress=0.90)
        refs = {
            "nav": self.artifacts.write_frame(run_id, "nav", result.nav),
            "fills": self.artifacts.write_frame(run_id, "fills", result.fills),
            "positions": self.artifacts.write_frame(run_id, "positions", result.positions),
            "signals": self.artifacts.write_frame(run_id, "signals", result.signals),
            "exclusions": self.artifacts.write_frame(run_id, "exclusions", result.exclusions),
            "attribution": self.artifacts.write_frame(
                run_id, "attribution", result.attribution
            ),
            "summary": self.artifacts.write_json(run_id, "summary", result.metrics),
            "request": self.artifacts.write_json(
                run_id, "request", request.model_dump(mode="json")
            ),
            "gate": self.artifacts.write_json(run_id, "gate", asdict(result.gate)),
        }
        manifest = {
            "run_id": run_id,
            "metadata": result.metadata,
            "metrics": result.metrics,
            "gate": asdict(result.gate),
            "artifacts": refs,
            "broker_submission": "disabled",
        }
        refs["manifest"] = self.artifacts.write_json(run_id, "manifest", manifest)
        self.metadata.save_experiment(
            run_id,
            content_hash(request.model_dump(mode="json")),
            bundle.fingerprint,
            result.metrics,
            refs,
            asdict(result.gate),
        )
        self.metadata.audit(
            "system", "backtest_completed", "experiment", run_id,
            {"gate_passed": result.gate.passed},
        )
        if job_id:
            self.metadata.update_job(
                job_id, JobStatus.COMPLETED, progress=1.0, result_ref=refs["manifest"]
            )
        return run_id, result, refs
