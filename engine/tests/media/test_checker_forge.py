"""Tests for the deterministic checkerboard media harness."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from tangl.journal.media import MediaFragment
from tangl.media.media_creators.checker_forge import (
    CheckerDispatcher,
    CheckerForge,
    CheckerSpec,
    make_checkerboard,
)
from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaDep, MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
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


def _world_script(*, resolution_class: str | None = None) -> dict[str, object]:
    spec: dict[str, object] = {
        "kind": "checker",
        "label": "checker_scene",
        "color_a": "#ff0000",
        "color_b": "#0000ff",
        "tile_size": 16,
        "dims": [64, 64],
    }
    if resolution_class is not None:
        spec["resolution_class"] = resolution_class

    return {
        "label": "checker_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "label": "start",
                        "content": "Checker block",
                        "media": [
                            {
                                "spec": spec,
                                "media_role": "scene_bg",
                                "fallback_text": "Checker pending.",
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
    story_label: str = "checker-story",
):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    world = World.from_script_data(script_data=_world_script(resolution_class=resolution_class))
    result = world.create_story(story_label)
    story = result.graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    dep = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    return world, story, block, dep


def _make_ledger(story, *, dispatcher=None):
    ledger = Ledger.from_graph(
        graph=story,
        entry_id=story.initial_cursor_id,
        uid=story.story_id or story.uid,
    )
    if dispatcher is not None:
        ledger.worker_dispatcher = dispatcher
    return ledger


def _advance(ledger):
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    return frame


class TestCheckerSpec:
    """Spec-model behavior for the checkerboard harness."""

    def test_defaults_are_sensible(self) -> None:
        spec = CheckerSpec()

        assert spec.color_a == "#000000"
        assert spec.color_b == "#ffffff"
        assert spec.tile_size == 32
        assert spec.dims == (256, 256)
        assert spec.data_type == MediaDataType.IMAGE
        assert spec.resolution_class == MediaResolutionClass.FAST_SYNC

    def test_from_authoring_resolves_checker_alias(self) -> None:
        spec = MediaSpec.from_authoring(
            {
                "kind": "checker",
                "color_a": "#aabbcc",
                "tile_size": 8,
            }
        )

        assert isinstance(spec, CheckerSpec)
        assert spec.color_a == "#aabbcc"
        assert spec.tile_size == 8

    def test_spec_fingerprint_is_deterministic(self) -> None:
        first = CheckerSpec(color_a="#112233", color_b="#445566")
        second = CheckerSpec(color_a="#112233", color_b="#445566")

        assert first.spec_fingerprint() == second.spec_fingerprint()


class TestCheckerForge:
    """Sync creator behavior for checkerboard media."""

    def test_make_checkerboard_has_expected_colors(self) -> None:
        image = make_checkerboard("#ff0000", "#0000ff", tile_size=32, dims=(64, 64))

        assert image.size == (64, 64)
        assert image.getpixel((0, 0)) == (255, 0, 0)
        assert image.getpixel((32, 0)) == (0, 0, 255)

    def test_create_media_returns_png_compatible_image(self) -> None:
        image, realized = CheckerForge().create_media(CheckerSpec(dims=(32, 32)))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        assert isinstance(image, Image.Image)
        assert realized.dims == (32, 32)
        assert buffer.getvalue()[:4] == b"\x89PNG"


class TestCheckerDispatcher:
    """In-process async dispatcher behavior for checkerboard media."""

    def test_immediate_dispatcher_returns_png_bytes(self) -> None:
        dispatcher = CheckerDispatcher()
        job_id = dispatcher.submit(CheckerSpec().normalized_spec_payload())
        result = dispatcher.poll(job_id)

        assert result is not None
        assert result.success is True
        assert isinstance(result.data, bytes)
        assert result.data_type == MediaDataType.IMAGE
        assert isinstance(result.execution_spec, dict)

    def test_deferred_dispatcher_waits_until_resolved(self) -> None:
        dispatcher = CheckerDispatcher(immediate=False)
        job_id = dispatcher.submit(CheckerSpec().normalized_spec_payload())

        assert dispatcher.poll(job_id) is None
        dispatcher.resolve(job_id)

        result = dispatcher.poll(job_id)
        assert result is not None
        assert result.success is True

    def test_deferred_dispatcher_can_fail_job(self) -> None:
        dispatcher = CheckerDispatcher(immediate=False)
        job_id = dispatcher.submit(CheckerSpec().normalized_spec_payload())
        dispatcher.fail(job_id, error="forced failure")

        result = dispatcher.poll(job_id)
        assert result is not None
        assert result.success is False
        assert result.error == "forced failure"


class TestCheckerForgeIntegration:
    """End-to-end sync and async story media behavior for checker specs."""

    def test_fast_sync_checker_spec_generates_story_scoped_png(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        _, story, block, dep = _make_story(monkeypatch=monkeypatch, tmp_path=tmp_path)

        provider = dep.provider
        assert isinstance(provider, MediaRIT)
        assert provider.status == MediaRITStatus.RESOLVED
        assert provider.path is not None and provider.path.exists()
        assert provider.path.suffix == ".png"
        assert provider.path.parent == story.story_resources.resource_path
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
        assert payload["scope"] == "story"
        assert payload["content_format"] == "rit"
        assert payload["url"].startswith(f"/media/story/{story.story_id}/checker_scene-")
        assert payload["url"].endswith(".png")

    def test_async_checker_spec_dispatches_and_reconciles(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        _, story, _, dep = _make_story(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            resolution_class="async",
        )
        provider = dep.provider

        assert isinstance(provider, MediaRIT)
        assert provider.status == MediaRITStatus.PENDING
        assert provider.derivation_spec is not None
        assert provider.adapted_spec is not None

        dispatcher = CheckerDispatcher(immediate=False)
        ledger = _make_ledger(story, dispatcher=dispatcher)

        _advance(ledger)

        assert provider.status == MediaRITStatus.RUNNING
        assert provider.job_id is not None
        assert len(dispatcher.submitted) == 1
        assert dispatcher.submitted[0][1] == provider.adapted_spec

        dispatcher.resolve_all()
        _advance(ledger)

        assert provider.status == MediaRITStatus.RESOLVED
        assert provider.job_id is None
        assert provider.path is not None and provider.path.exists()
        assert provider.data_type == MediaDataType.IMAGE
        assert provider.execution_spec is not None
        assert provider.execution_spec_hash is not None
        assert len(dispatcher.submitted) == 1
