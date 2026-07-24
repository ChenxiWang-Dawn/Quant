from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor

from a_share_quant.contracts.models import BacktestRequest, JobRecord, JobStatus
from a_share_quant.services import RunService


class JobCancelled(RuntimeError):
    pass


class JobManager:
    def __init__(self, service: RunService, max_workers: int = 2) -> None:
        self.service = service
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="quant-job")
        self.futures: dict[str, Future] = {}
        self.cancel_events: dict[str, threading.Event] = {}
        self.lock = threading.RLock()

    def submit_backtest(self, request: BacktestRequest) -> JobRecord:
        with self.lock:
            job = self.service.metadata.create_job(
                "backtest",
                request.model_dump(mode="json"),
                request.idempotency_key,
            )
            if job.status != JobStatus.QUEUED or job.id in self.futures:
                return job
            event = threading.Event()

        def progress(_: float) -> None:
            if event.is_set():
                raise JobCancelled("job cancelled by user")

        def execute() -> None:
            try:
                self.service.run_backtest(request, job_id=job.id, progress_hook=progress)
            except JobCancelled as error:
                self.service.metadata.update_job(
                    job.id, JobStatus.CANCELLED, error_code="CANCELLED",
                    error_message=str(error),
                )
            except Exception as error:  # noqa: BLE001 - job boundary persists every failure
                self.service.metadata.update_job(
                    job.id, JobStatus.FAILED, error_code=type(error).__name__,
                    error_message=str(error),
                )

        with self.lock:
            future = self.executor.submit(execute)
            self.futures[job.id] = future
            self.cancel_events[job.id] = event
        return job

    def cancel(self, job_id: str) -> JobRecord:
        with self.lock:
            future = self.futures.get(job_id)
            event = self.cancel_events.get(job_id)
        record = self.service.metadata.get_job(job_id)
        if record.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return record
        if event:
            event.set()
        if future and future.cancel():
            return self.service.metadata.update_job(
                job_id, JobStatus.CANCELLED, error_code="CANCELLED",
                error_message="cancelled before execution",
            )
        return self.service.metadata.update_job(job_id, JobStatus.CANCELLING)
