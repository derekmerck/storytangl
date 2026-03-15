"""In-process async-style dispatcher for the checkerboard media harness."""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from tangl.media.media_data_type import MediaDataType
from tangl.media.worker_dispatcher import WorkerResult

from .checker_forge import CheckerForge
from .checker_spec import CheckerSpec


@dataclass
class _PendingJob:
    job_id: str
    spec: dict[str, Any]
    result: WorkerResult | None = None


def _run_forge(spec_dict: dict[str, Any], *, worker_id: str) -> WorkerResult:
    """Realize one checker spec into PNG bytes for the async lifecycle tests."""

    try:
        spec = CheckerSpec.model_validate(spec_dict)
        image, realized_spec = CheckerForge().create_media(spec)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return WorkerResult(
            success=True,
            data=buffer.getvalue(),
            data_type=MediaDataType.IMAGE,
            execution_spec=realized_spec.normalized_spec_payload(),
            worker_id=worker_id,
            generated_at=datetime.now(),
        )
    except Exception as exc:  # noqa: BLE001
        return WorkerResult(
            success=False,
            error=str(exc),
            worker_id=worker_id,
        )


class CheckerDispatcher:
    """Simple in-process dispatcher that satisfies the Phase 2 worker protocol."""

    def __init__(
        self,
        *,
        immediate: bool = True,
        worker_id: str = "checker-forge",
    ) -> None:
        self._immediate = immediate
        self._worker_id = worker_id
        self._jobs: dict[str, _PendingJob] = {}
        self.submitted: list[tuple[str, dict[str, Any]]] = []
        self.cancelled: list[str] = []

    def submit(self, spec: dict[str, Any]) -> str:
        job_id = f"checker-{uuid4().hex[:8]}"
        job = _PendingJob(job_id=job_id, spec=dict(spec))
        if self._immediate:
            job.result = _run_forge(job.spec, worker_id=self._worker_id)
        self._jobs[job_id] = job
        self.submitted.append((job_id, dict(spec)))
        return job_id

    def poll(self, job_id: str) -> WorkerResult | None:
        job = self._jobs.get(job_id)
        if job is None:
            return WorkerResult(success=False, error=f"unknown job {job_id!r}")
        return job.result

    def cancel(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        self.cancelled.append(job_id)

    def resolve(self, job_id: str) -> None:
        """Force-complete one staged job when ``immediate`` is disabled."""

        job = self._jobs.get(job_id)
        if job is not None and job.result is None:
            job.result = _run_forge(job.spec, worker_id=self._worker_id)

    def resolve_all(self) -> None:
        """Force-complete all staged jobs."""

        for job_id in list(self._jobs):
            self.resolve(job_id)

    def fail(self, job_id: str, error: str = "forced failure") -> None:
        """Force a staged job into a terminal failure for tests."""

        job = self._jobs.get(job_id)
        if job is not None:
            job.result = WorkerResult(
                success=False,
                error=error,
                worker_id=self._worker_id,
            )

    @property
    def pending_job_ids(self) -> list[str]:
        return [job_id for job_id, job in self._jobs.items() if job.result is None]
