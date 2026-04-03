"""Tests for Comfy-backed story media integration.

Organized by functionality:
- Story lifecycle: async pending -> running -> resolved flow using Comfy specs
- Service payloads: resolved story media still dereferences to canonical story URLs
- Live integration: optional real-node polling through ComfySpec materialization
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from tangl.journal.media import MediaFragment
from tangl.media.media_creators.comfy_forge import ComfyApi, ComfySpec
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaDep, MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.worker_dispatcher import WorkerResult
from tangl.service.media import media_fragment_to_payload
from tangl.story.fabula import World
from tangl.story.system_handlers import render_block_media
from tangl.vm.runtime.ledger import Ledger


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _png_bytes(*, color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    image = Image.new("RGB", (32, 32), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _world_script(
    *,
    resolution_class: str | None = None,
    spec_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    spec: dict[str, object] = {
        "kind": "comfy",
        "label": "hero_portrait",
        "workflow_template": "portrait_txt2img",
        "prompt": "portrait of a hero",
    }
    if spec_overrides:
        for key, value in spec_overrides.items():
            if value is None:
                spec.pop(key, None)
                continue
            spec[key] = value
    if resolution_class is not None:
        spec["resolution_class"] = resolution_class

    return {
        "label": "comfy_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "label": "start",
                        "content": "Comfy block",
                        "media": [
                            {
                                "spec": spec,
                                "media_role": "avatar_im",
                                "fallback_text": "Portrait pending.",
                                "scope": "story",
                            }
                        ],
                        "actions": [{"text": "Next", "successor": "end"}],
                    },
                    "end": {"label": "end", "content": "Done."},
                }
            }
        },
    }


def _make_story(
    *,
    monkeypatch,
    tmp_path: Path,
    resolution_class: str | None = None,
    spec_overrides: dict[str, object] | None = None,
):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    world = World.from_script_data(
        script_data=_world_script(
            resolution_class=resolution_class,
            spec_overrides=spec_overrides,
        )
    )
    result = world.create_story("comfy-story")
    story = result.graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    dep = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    return story, block, dep


def _make_ledger(story, *, dispatcher):
    ledger = Ledger.from_graph(
        graph=story,
        entry_id=story.initial_cursor_id,
        uid=story.story_id or story.uid,
    )
    ledger.worker_dispatcher = dispatcher
    return ledger


def _advance(ledger):
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    return frame


class FakeDispatcher:
    """Minimal dispatcher for Comfy story lifecycle tests."""

    def __init__(self) -> None:
        self.submitted: list[tuple[str, dict[str, object]]] = []
        self.results: dict[str, WorkerResult] = {}

    def submit(self, spec: dict[str, object]) -> str:
        job_id = f"job-{len(self.submitted) + 1}"
        self.submitted.append((job_id, dict(spec)))
        return job_id

    def poll(self, job_id: str) -> WorkerResult | None:
        return self.results.get(job_id)

    def cancel(self, job_id: str) -> None:
        _ = job_id


class FakeSyncForge:
    """Small sync creator used to prove the FAST_SYNC provisioning path."""

    def __init__(self) -> None:
        self.created_specs = []

    def create_media(self, spec):
        self.created_specs.append(spec.model_copy(deep=True))
        return _png_bytes(color=(0, 128, 255)), spec


class TestComfyStoryLifecycle:
    """Tests for Comfy specs through the existing async story lifecycle."""

    def test_async_comfy_spec_dispatches_and_resolves_to_story_url(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        story, block, dep = _make_story(monkeypatch=monkeypatch, tmp_path=tmp_path)
        provider = dep.provider

        assert isinstance(provider, MediaRIT)
        assert provider.status == MediaRITStatus.PENDING
        assert provider.adapted_spec is not None
        assert isinstance(provider.adapted_spec.get("workflow"), dict)
        assert "workflow_template" not in provider.adapted_spec

        dispatcher = FakeDispatcher()
        ledger = _make_ledger(story, dispatcher=dispatcher)

        _advance(ledger)

        assert provider.status == MediaRITStatus.RUNNING
        assert provider.job_id == "job-1"
        assert len(dispatcher.submitted) == 1
        assert dispatcher.submitted[0][1] == provider.adapted_spec

        dispatcher.results["job-1"] = WorkerResult(
            success=True,
            data=_png_bytes(),
            data_type=MediaDataType.IMAGE,
            execution_spec={**provider.adapted_spec, "worker": "fake"},
            worker_id="fake-comfy",
        )

        _advance(ledger)

        assert provider.status == MediaRITStatus.RESOLVED
        assert provider.job_id is None
        assert provider.path is not None and provider.path.exists()
        assert provider.path.suffix == ".png"
        assert provider.execution_spec is not None
        assert provider.execution_spec_hash is not None

        fragments = render_block_media(caller=block, ctx=SimpleNamespace(get_ns=lambda _caller: {}))
        fragment = next(item for item in fragments if isinstance(item, MediaFragment))
        payload = media_fragment_to_payload(
            fragment,
            story_id=str(story.story_id),
            story_media_root=story.story_resources.resource_path,
        )

        assert payload is not None
        assert payload["content_format"] == "rit"
        assert payload["scope"] == "story"
        assert payload["url"].startswith(f"/media/story/{story.story_id}/hero_portrait-")
        assert payload["url"].endswith(".png")

    def test_async_comfy_shot_type_still_dispatches_final_workflow(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        story, _block, dep = _make_story(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            spec_overrides={
                "shot_type": "portrait",
                "workflow_template": None,
                "prompt": None,
            },
        )
        provider = dep.provider
        dispatcher = FakeDispatcher()
        ledger = _make_ledger(story, dispatcher=dispatcher)

        assert provider.status == MediaRITStatus.PENDING
        assert provider.adapted_spec is not None
        assert provider.adapted_spec.get("workflow") is not None
        assert "workflow_template" not in provider.adapted_spec

        _advance(ledger)

        assert provider.status == MediaRITStatus.RUNNING
        assert dispatcher.submitted[0][1] == provider.adapted_spec

    def test_fast_sync_comfy_spec_resolves_immediately_to_story_url(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        forge = FakeSyncForge()
        monkeypatch.setattr(
            "tangl.media.media_creators.comfy_forge.comfy_spec.ComfySpec.get_creation_service",
            classmethod(lambda cls: forge),
        )

        story, block, dep = _make_story(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            resolution_class="fast_sync",
        )
        provider = dep.provider

        assert isinstance(provider, MediaRIT)
        assert provider.status == MediaRITStatus.RESOLVED
        assert provider.path is not None and provider.path.exists()
        assert provider.path.suffix == ".png"
        assert provider.data_type == MediaDataType.IMAGE
        assert provider.adapted_spec is not None
        assert isinstance(provider.adapted_spec.get("workflow"), dict)
        assert "workflow_template" not in provider.adapted_spec
        assert provider.execution_spec is not None
        assert forge.created_specs and forge.created_specs[0].workflow is not None

        fragments = render_block_media(caller=block, ctx=SimpleNamespace(get_ns=lambda _caller: {}))
        fragment = next(item for item in fragments if isinstance(item, MediaFragment))
        payload = media_fragment_to_payload(
            fragment,
            story_id=str(story.story_id),
            story_media_root=story.story_resources.resource_path,
        )

        assert payload is not None
        assert payload["content_format"] == "rit"
        assert payload["scope"] == "story"
        assert payload["url"].startswith(f"/media/story/{story.story_id}/hero_portrait-")
        assert payload["url"].endswith(".png")


def _run_live_comfy() -> bool:
    return os.environ.get("RUN_COMFY_INTEGRATION") == "1"


@pytest.mark.skipif(
    not _run_live_comfy(),
    reason="Requires RUN_COMFY_INTEGRATION=1",
)
class TestComfyLiveIntegration:
    """Optional live-node smoke test for a real ComfyUI worker through ComfySpec."""

    def test_real_comfy_dispatcher_returns_image_bytes_from_comfy_spec(self) -> None:
        from tangl.media.media_creators.comfy_forge import ComfyDispatcher

        url = os.environ.get("COMFY_URL", "titan2.lan:8188")
        api = ComfyApi(url)
        checkpoint = os.environ.get("COMFY_TEST_CHECKPOINT")
        if checkpoint is None:
            checkpoints = api.list_models("checkpoints")
            if not checkpoints:
                pytest.skip("No checkpoints available on configured ComfyUI worker")
            checkpoint = checkpoints[0]

        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of a hero",
            n_prompt="low quality, blurry, bad anatomy, worst quality",
            model=checkpoint,
            seed=42,
            dims=(512, 768),
            iterations=20,
        )
        adapted_payload = spec.normalized_spec_payload()
        dispatcher = ComfyDispatcher(url=url, api=api)
        snapshot = dispatcher.describe_worker()

        assert "checkpoints" in snapshot.model_types
        assert adapted_payload.get("workflow")
        job_id = dispatcher.submit(adapted_payload)

        deadline = time.time() + 60
        result = None
        while time.time() < deadline:
            result = dispatcher.poll(job_id)
            if result is not None:
                break
            time.sleep(2)

        assert result is not None
        assert result.success is True
        assert isinstance(result.data, bytes)

        image = Image.open(io.BytesIO(result.data))
        image.verify()
