"""Tests for the ComfyUI worker dispatcher.

Organized by functionality:
- Submission: required workflow payload and prompt-id job identity
- Polling: pending, success, failure, and transient network handling
- Settings seam: config-driven worker construction remains isolated here
"""

from __future__ import annotations

from types import SimpleNamespace

import requests

from tangl.media.media_creators.comfy_forge.comfy_dispatcher import ComfyDispatcher
from tangl.media.media_data_type import MediaDataType


class StubApi:
    """Small API stub for dispatcher tests."""

    def __init__(self) -> None:
        self.prompt_id = "prompt-123"
        self.history = None
        self.image_bytes = b""
        self.cancelled: list[str] = []
        self.interrupted = False
        self.snapshot = SimpleNamespace(model_types=("checkpoints",))

    def queue_prompt(self, workflow):
        self.queued_workflow = workflow
        return self.prompt_id

    def get_history(self, prompt_id: str):
        self.history_prompt_id = prompt_id
        value = self.history
        if isinstance(value, Exception):
            raise value
        return value

    def extract_output_image_refs(self, history):
        self.extract_history = history
        if not isinstance(history, dict) or not history.get("outputs"):
            return []
        return [{"filename": "hero.png", "subfolder": "", "type": "output"}]

    def fetch_image_bytes(self, filename: str, *, subfolder: str = "", folder_type: str = "output"):
        self.fetch_args = (filename, subfolder, folder_type)
        if isinstance(self.image_bytes, Exception):
            raise self.image_bytes
        return self.image_bytes

    def cancel_prompt(self, prompt_id: str) -> None:
        self.cancelled.append(prompt_id)

    def interrupt(self) -> None:
        self.interrupted = True

    def describe_worker(self, *, model_folders=("checkpoints",)):
        self.snapshot_model_folders = model_folders
        return self.snapshot


class TestComfyDispatcherSubmission:
    """Tests for job submission behavior."""

    def test_submit_requires_workflow_and_returns_prompt_id(self) -> None:
        api = StubApi()
        dispatcher = ComfyDispatcher(api=api)

        job_id = dispatcher.submit({"workflow": {"1": {"inputs": {}}}, "prompt": "portrait"})

        assert job_id == "prompt-123"
        assert api.queued_workflow == {"1": {"inputs": {}}}

    def test_submit_without_workflow_raises(self) -> None:
        dispatcher = ComfyDispatcher(api=StubApi())

        try:
            dispatcher.submit({"prompt": "portrait"})
        except ValueError as exc:
            assert "workflow" in str(exc)
        else:
            raise AssertionError("submit should reject adapted specs without workflow")


class TestComfyDispatcherPolling:
    """Tests for async polling behavior."""

    def test_poll_returns_none_while_prompt_is_pending(self) -> None:
        api = StubApi()
        dispatcher = ComfyDispatcher(api=api)
        job_id = dispatcher.submit({"workflow": {"1": {"inputs": {}}}})

        assert dispatcher.poll(job_id) is None

    def test_poll_returns_successful_image_result_when_complete(self) -> None:
        api = StubApi()
        api.history = {
            "status": {"completed": True},
            "outputs": {"save": {"images": [{"filename": "hero.png"}]}},
        }
        api.image_bytes = b"\x89PNG\r\n\x1a\npayload"
        dispatcher = ComfyDispatcher(api=api)
        job_id = dispatcher.submit(
            {
                "workflow": {"1": {"inputs": {}}},
                "prompt": "portrait",
            }
        )

        result = dispatcher.poll(job_id)

        assert result is not None
        assert result.success is True
        assert result.data == b"\x89PNG\r\n\x1a\npayload"
        assert result.data_type == MediaDataType.IMAGE
        assert result.execution_spec == {
            "workflow": {"1": {"inputs": {}}},
            "prompt": "portrait",
        }

    def test_poll_returns_failure_when_comfy_reports_error(self) -> None:
        api = StubApi()
        api.history = {
            "status": {
                "status_str": "error",
                "messages": [["execution_error", {"exception_message": "boom"}]],
            }
        }
        dispatcher = ComfyDispatcher(api=api)
        job_id = dispatcher.submit({"workflow": {"1": {"inputs": {}}}})

        result = dispatcher.poll(job_id)

        assert result is not None
        assert result.success is False
        assert result.error == "boom"

    def test_poll_returns_failure_for_unknown_job(self) -> None:
        result = ComfyDispatcher(api=StubApi()).poll("missing-job")

        assert result is not None
        assert result.success is False
        assert "unknown job" in str(result.error)

    def test_network_error_during_poll_is_treated_as_pending(self) -> None:
        api = StubApi()
        api.history = requests.ConnectionError("offline")
        dispatcher = ComfyDispatcher(api=api)
        job_id = dispatcher.submit({"workflow": {"1": {"inputs": {}}}})

        assert dispatcher.poll(job_id) is None


class TestComfyDispatcherSettings:
    """Tests for the settings-backed dispatcher seam."""

    def test_from_settings_uses_first_configured_worker(self, monkeypatch) -> None:
        stableforge = SimpleNamespace(comfy_workers=["titan2.lan:8188"])
        monkeypatch.setattr(
            "tangl.media.media_creators.comfy_forge._common.stableforge_config",
            lambda: stableforge,
        )

        dispatcher = ComfyDispatcher.from_settings()

        assert dispatcher is not None
        assert dispatcher._api.endpoint() == "http://titan2.lan:8188"


class TestComfyDispatcherWorkerIntrospection:
    """Tests for dispatcher-level worker discovery helpers."""

    def test_describe_worker_delegates_to_api(self) -> None:
        api = StubApi()
        dispatcher = ComfyDispatcher(api=api)

        snapshot = dispatcher.describe_worker(model_folders=("checkpoints", "loras"))

        assert snapshot is api.snapshot
        assert api.snapshot_model_folders == ("checkpoints", "loras")
