"""Tests for the blocking ComfyUI sync creator.

Organized by functionality:
- Settings seam: sync and async surfaces share one worker-url helper
- Polling loop: success, timeout, and explicit completion failures
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.media.media_creators.comfy_forge import ComfyDispatcher, ComfyForge, ComfySpec


class StubApi:
    """Small API stub for sync creator tests."""

    def __init__(self) -> None:
        self.prompt_id = "prompt-123"
        self.histories: list[dict[str, object] | None] = []
        self.image_bytes = b""

    def queue_prompt(self, workflow):
        self.queued_workflow = workflow
        return self.prompt_id

    def get_history(self, prompt_id: str):
        self.history_prompt_id = prompt_id
        if self.histories:
            return self.histories.pop(0)
        return None

    def extract_output_image_refs(self, history):
        return [
            {
                "filename": "hero.png",
                "subfolder": "",
                "type": "output",
            }
        ] if isinstance(history, dict) and history.get("outputs") else []

    def fetch_image_bytes(self, filename: str, *, subfolder: str = "", folder_type: str = "output"):
        self.fetch_args = (filename, subfolder, folder_type)
        return self.image_bytes


class TestComfyForgeSettings:
    """Tests for the settings-backed sync creator seam."""

    def test_dispatcher_and_sync_creator_share_the_same_configured_worker(self, monkeypatch) -> None:
        stableforge = SimpleNamespace(comfy_workers=["titan2.lan:8188"])
        monkeypatch.setattr(
            "tangl.media.media_creators.comfy_forge._common.stableforge_config",
            lambda: stableforge,
        )

        dispatcher = ComfyDispatcher.from_settings()
        forge = ComfyForge.from_settings()

        assert dispatcher is not None
        assert forge is not None
        assert dispatcher._api.endpoint() == "http://titan2.lan:8188"
        assert forge._api.endpoint() == "http://titan2.lan:8188"


class TestComfyForgeCreation:
    """Tests for the blocking workflow submission and polling loop."""

    def test_create_media_returns_image_bytes_and_realized_spec(self) -> None:
        api = StubApi()
        api.histories = [
            {
                "status": {"completed": True},
                "outputs": {"save": {"images": [{"filename": "hero.png"}]}},
            }
        ]
        api.image_bytes = b"\x89PNG\r\n\x1a\npayload"
        forge = ComfyForge(api=api, timeout_seconds=1.0, poll_interval_seconds=0.0)
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of Katya",
        )

        image_bytes, realized_spec = forge.create_media(spec)

        assert image_bytes == b"\x89PNG\r\n\x1a\npayload"
        assert realized_spec is spec
        assert realized_spec.workflow is not None
        assert api.queued_workflow == realized_spec.workflow
        assert api.fetch_args == ("hero.png", "", "output")

    def test_create_media_raises_on_comfy_execution_error(self) -> None:
        api = StubApi()
        api.histories = [
            {
                "status": {
                    "status_str": "error",
                    "messages": [["execution_error", {"exception_message": "boom"}]],
                }
            }
        ]
        forge = ComfyForge(api=api, timeout_seconds=1.0, poll_interval_seconds=0.0)
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of Katya",
        )

        with pytest.raises(RuntimeError, match="boom"):
            forge.create_media(spec)

    def test_create_media_raises_when_completed_workflow_has_no_outputs(self) -> None:
        api = StubApi()
        api.histories = [{"status": {"completed": True}, "outputs": {}}]
        forge = ComfyForge(api=api, timeout_seconds=1.0, poll_interval_seconds=0.0)
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of Katya",
        )

        with pytest.raises(RuntimeError, match="no output images"):
            forge.create_media(spec)

    def test_create_media_times_out_while_history_stays_pending(self, monkeypatch) -> None:
        api = StubApi()
        forge = ComfyForge(api=api, timeout_seconds=0.5, poll_interval_seconds=0.0)
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of Katya",
        )
        monotonic_values = iter([0.0, 0.0, 1.0])

        monkeypatch.setattr(
            "tangl.media.media_creators.comfy_forge.comfy_forge.time.monotonic",
            lambda: next(monotonic_values),
        )
        monkeypatch.setattr(
            "tangl.media.media_creators.comfy_forge.comfy_forge.time.sleep",
            lambda _seconds: None,
        )

        with pytest.raises(TimeoutError, match="Timed out waiting for ComfyUI prompt"):
            forge.create_media(spec)
