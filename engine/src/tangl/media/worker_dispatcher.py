from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .media_data_type import MediaDataType


@dataclass
class WorkerResult:
    """Outcome returned by async media workers."""

    success: bool
    path: Path | None = None
    data: bytes | str | None = None
    data_type: MediaDataType | None = None
    error: str | None = None
    execution_spec: dict[str, Any] | None = None
    worker_id: str | None = None
    generated_at: datetime | None = None


class WorkerDispatcher(Protocol):
    """Submit and poll async media generation jobs."""

    def submit(self, spec: dict[str, Any]) -> str:
        """Submit a fully rendered ``adapted_spec`` and return a job id."""
        ...

    def poll(self, job_id: str) -> WorkerResult | None:
        """Return ``None`` while a job is still pending, else its final result."""
        ...

    def cancel(self, job_id: str) -> None:
        """Cancel a queued or running job when supported."""
        ...
