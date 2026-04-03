from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from tangl.media.media_data_type import MediaDataType
from tangl.media.worker_dispatcher import WorkerResult

from ._common import configured_comfy_url, history_error
from .comfy_api import ComfyApi, ComfyWorkerSnapshot

logger = logging.getLogger(__name__)


@dataclass
class _ComfyJob:
    job_id: str
    spec: dict[str, Any]
    submitted_at: datetime


class ComfyDispatcher:
    """WorkerDispatcher implementation backed by one ComfyUI instance."""

    def __init__(
        self,
        *,
        url: str = "http://127.0.0.1:8188",
        worker_id: str = "comfy-ui",
        output_index: int = 0,
        api: ComfyApi | None = None,
    ) -> None:
        self._worker_id = worker_id
        self._output_index = output_index
        self._api = api or ComfyApi(url)
        self._jobs: dict[str, _ComfyJob] = {}

    @classmethod
    def from_settings(cls) -> "ComfyDispatcher | None":
        url = configured_comfy_url()
        if not url:
            return None
        return cls(url=url)

    def submit(self, spec: dict[str, Any]) -> str:
        workflow = spec.get("workflow")
        if not isinstance(workflow, dict) or not workflow:
            raise ValueError("ComfyDispatcher.submit requires adapted spec['workflow']")
        job_id = self._api.queue_prompt(workflow)
        self._jobs[job_id] = _ComfyJob(
            job_id=job_id,
            spec=dict(spec),
            submitted_at=datetime.now(),
        )
        return job_id

    def poll(self, job_id: str) -> WorkerResult | None:
        job = self._jobs.get(job_id)
        if job is None:
            return WorkerResult(
                success=False,
                error=f"unknown job {job_id!r}",
                worker_id=self._worker_id,
            )

        try:
            history = self._api.get_history(job_id)
            if history is None:
                return None
            error = history_error(history)
            if error is not None:
                return WorkerResult(
                    success=False,
                    error=error,
                    execution_spec=dict(job.spec),
                    worker_id=self._worker_id,
                )

            image_refs = self._api.extract_output_image_refs(history)
            if not image_refs:
                status = history.get("status")
                if isinstance(status, dict) and status.get("completed") is False:
                    return None
                return WorkerResult(
                    success=False,
                    error="completed workflow produced no output images",
                    execution_spec=dict(job.spec),
                    worker_id=self._worker_id,
                )

            index = min(self._output_index, len(image_refs) - 1)
            image_ref = image_refs[index]
            image_bytes = self._api.fetch_image_bytes(
                image_ref["filename"],
                subfolder=image_ref.get("subfolder", ""),
                folder_type=image_ref.get("type", "output"),
            )
        except requests.RequestException:
            logger.exception("Transient ComfyUI poll failure for job %s", job_id)
            return None

        return WorkerResult(
            success=True,
            data=image_bytes,
            data_type=MediaDataType.IMAGE,
            execution_spec=dict(job.spec),
            worker_id=self._worker_id,
            generated_at=datetime.now(),
        )

    def describe_worker(
        self,
        *,
        model_folders: tuple[str, ...] = ("checkpoints",),
    ) -> ComfyWorkerSnapshot:
        return self._api.describe_worker(model_folders=model_folders)

    def cancel(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        try:
            self._api.cancel_prompt(job_id)
        except requests.RequestException:
            logger.info("Unable to cancel ComfyUI job %s", job_id, exc_info=True)

    def interrupt(self) -> None:
        try:
            self._api.interrupt()
        except requests.RequestException:
            logger.info("Unable to interrupt active ComfyUI execution", exc_info=True)
