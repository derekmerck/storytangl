"""Tests for Phase 2 server-side async media lifecycle behavior."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaDep, MediaInventory
from tangl.media.media_resource import MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.worker_dispatcher import WorkerResult
from tangl.service.media import MediaRenderProfile, media_fragment_to_payload
from tangl.story.fabula import World
from tangl.vm.provision.resolver import Resolver
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.runtime.ledger import Ledger


class FakeDispatcher:
    """Minimal in-process dispatcher for lifecycle tests."""

    def __init__(self) -> None:
        self.submitted: list[tuple[str, dict[str, object]]] = []
        self.results: dict[str, WorkerResult] = {}
        self.cancelled: list[str] = []

    def submit(self, spec: dict[str, object]) -> str:
        job_id = f"job-{len(self.submitted) + 1}"
        self.submitted.append((job_id, dict(spec)))
        return job_id

    def poll(self, job_id: str) -> WorkerResult | None:
        return self.results.get(job_id)

    def cancel(self, job_id: str) -> None:
        self.cancelled.append(job_id)


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _async_spec_script() -> dict[str, object]:
    return {
        "label": "async_media_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "label": "start",
                        "content": "Async media block",
                        "media": [
                            {
                                "spec": {
                                    "kind": "stable",
                                    "label": "hero_portrait",
                                    "prompt": "hero portrait",
                                },
                                "media_role": "avatar_im",
                                "fallback_text": "Portrait pending.",
                                "scope": "story",
                            }
                        ],
                        "actions": [
                            {
                                "text": "Continue",
                                "successor": "after",
                            }
                        ],
                    },
                    "after": {
                        "label": "after",
                        "content": "After",
                    },
                }
            }
        },
    }


def _story_from_async_spec(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    story_label: str = "async-media-story",
    world_label: str = "async_media_world",
):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    script = _async_spec_script()
    script["label"] = world_label
    world = World.from_script_data(script_data=script)
    result = world.create_story(story_label)
    story = result.graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    dep = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    return world, story, block, dep


def _fallback_inventory(tmp_path: Path) -> tuple[MediaInventory, Path]:
    path = tmp_path / "placeholder.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<rect width="32" height="32" fill="gray"/></svg>',
        encoding="utf-8",
    )
    from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry

    media_registry = MediaResourceRegistry(label="fallback_media")
    media_registry.add(MediaRIT(path=path, data_type=MediaDataType.VECTOR, label=path.name))
    return MediaInventory(registry=media_registry, scope="world"), path


class TestAsyncMediaRitModel:
    """Validation and compatibility behavior for unresolved media RITs."""

    def test_pending_rit_allows_missing_source_and_aliases_spec_hash(self) -> None:
        rit = MediaRIT(status=MediaRITStatus.PENDING, spec_fingerprint="abc123")

        assert rit.adapted_spec_hash == "abc123"
        assert rit.spec_fingerprint == "abc123"

    def test_resolved_rit_without_source_still_raises(self) -> None:
        with pytest.raises(ValueError):
            MediaRIT(status=MediaRITStatus.RESOLVED, data_type=MediaDataType.IMAGE)

    def test_missing_path_falls_through_to_inline_data(self, tmp_path: Path) -> None:
        fragment = MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.RESOLVED,
                path=tmp_path / "missing.svg",
                data=(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                    '<circle cx="16" cy="16" r="14" fill="red"/></svg>'
                ),
                data_type=MediaDataType.VECTOR,
            ),
            content_format="rit",
            content_type=MediaDataType.VECTOR,
            source_id=uuid4(),
            scope="story",
        )

        payload = media_fragment_to_payload(
            fragment,
            render_profile="inline_data",
            story_id="story-1",
        )

        assert payload is not None
        assert payload["content_format"] == "xml"


class TestAsyncInlineLifecycle:
    """Lifecycle tests for inline async media specs."""

    def test_async_inline_spec_creates_pending_story_media_dep(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _, _, _, dep = _story_from_async_spec(monkeypatch=monkeypatch, tmp_path=tmp_path)

        provider = dep.provider
        assert isinstance(provider, MediaRIT)
        assert provider.status == MediaRITStatus.PENDING
        assert provider.path is None
        assert provider.adapted_spec_hash is not None
        assert provider.spec_fingerprint == provider.adapted_spec_hash
        assert isinstance(provider.derivation_spec, dict)
        assert isinstance(provider.adapted_spec, dict)

    def test_adapted_seed_and_hash_are_deterministic_across_story_creations(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _, _, _, dep_one = _story_from_async_spec(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            story_label="story-one",
            world_label="async_media_world_one",
        )
        _, _, _, dep_two = _story_from_async_spec(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            story_label="story-two",
            world_label="async_media_world_two",
        )

        first = dep_one.provider
        second = dep_two.provider
        assert isinstance(first, MediaRIT) and isinstance(second, MediaRIT)
        assert first.adapted_spec_hash == second.adapted_spec_hash
        assert first.adapted_spec["seed"] == second.adapted_spec["seed"]

    def test_later_resolve_pass_reuses_existing_pending_rit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _, story, block, dep = _story_from_async_spec(monkeypatch=monkeypatch, tmp_path=tmp_path)

        duplicate_dep = MediaDep(
            label="duplicate_media",
            predecessor_id=block.uid,
            media_spec={
                "kind": "stable",
                "label": "hero_portrait",
                "prompt": "hero portrait",
            },
            media_role="avatar_im",
            scope="story",
        )
        story.add(duplicate_dep)

        ctx = PhaseCtx(
            graph=story,
            cursor_id=block.uid,
        )
        Resolver.from_ctx(ctx).resolve_dependency(duplicate_dep, allow_stubs=False, _ctx=ctx)

        assert dep.provider is not None
        assert duplicate_dep.provider is not None
        assert duplicate_dep.provider.uid == dep.provider.uid

    def test_dispatch_and_reconcile_only_once_per_planning_pass(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _, story, _, dep = _story_from_async_spec(monkeypatch=monkeypatch, tmp_path=tmp_path)
        dispatcher = FakeDispatcher()

        ledger = Ledger.from_graph(
            graph=story,
            entry_id=story.initial_cursor_id,
            uid=story.story_id or story.uid,
        )
        ledger.worker_dispatcher = dispatcher

        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)

        provider = dep.provider
        assert isinstance(provider, MediaRIT)
        assert provider.status == MediaRITStatus.RUNNING
        assert provider.job_id == "job-1"
        assert len(dispatcher.submitted) == 1
        assert dispatcher.submitted[0][1] == provider.adapted_spec

        dispatcher.results["job-1"] = WorkerResult(
            success=True,
            data=(
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                '<circle cx="16" cy="16" r="14" fill="red"/></svg>'
            ),
            data_type=MediaDataType.VECTOR,
            execution_spec={**provider.adapted_spec, "sampler": "fake-worker"},
            worker_id="fake-worker",
        )

        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)

        assert len(dispatcher.submitted) == 1
        assert provider.status == MediaRITStatus.RESOLVED
        assert provider.job_id is None
        assert provider.execution_spec_hash is not None
        assert provider.path is not None and provider.path.exists()

    def test_failed_job_is_not_resubmitted(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _, story, _, dep = _story_from_async_spec(monkeypatch=monkeypatch, tmp_path=tmp_path)
        dispatcher = FakeDispatcher()

        ledger = Ledger.from_graph(
            graph=story,
            entry_id=story.initial_cursor_id,
            uid=story.story_id or story.uid,
        )
        ledger.worker_dispatcher = dispatcher

        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)
        provider = dep.provider
        assert isinstance(provider, MediaRIT)
        assert provider.job_id == "job-1"

        dispatcher.results["job-1"] = WorkerResult(success=False, error="boom")
        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)

        assert provider.status == MediaRITStatus.FAILED
        assert provider.job_id is None
        assert len(dispatcher.submitted) == 1

        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)
        assert len(dispatcher.submitted) == 1


class TestAsyncServiceFallbacks:
    """Service-layer fallback behavior for pending and failed media."""

    def test_pending_media_uses_static_fallback_rit_when_available(self, tmp_path: Path) -> None:
        inventory, fallback_path = _fallback_inventory(tmp_path)
        fragment = MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.PENDING,
                adapted_spec_hash="pending-1",
                derivation_spec={"fallback_ref": fallback_path.name},
                data_type=MediaDataType.VECTOR,
            ),
            content_format="rit",
            content_type=MediaDataType.VECTOR,
            media_role="avatar_im",
            source_id=uuid4(),
            scope="world",
            fallback_text="Portrait pending.",
        )

        payload = media_fragment_to_payload(
            fragment,
            render_profile=MediaRenderProfile(static_inventories=(inventory,)),
            world_id="demo",
            world_media_root=tmp_path,
        )

        assert payload is not None
        assert payload["fragment_type"] == "media"
        assert payload["content_format"] == "rit"
        assert payload["url"] == "/media/world/demo/placeholder.svg"

    def test_story_scoped_pending_media_uses_fallback_asset_scope(self, tmp_path: Path) -> None:
        inventory, fallback_path = _fallback_inventory(tmp_path)
        fragment = MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.PENDING,
                adapted_spec_hash="pending-3",
                derivation_spec={"fallback_ref": fallback_path.name},
                data_type=MediaDataType.VECTOR,
            ),
            content_format="rit",
            content_type=MediaDataType.VECTOR,
            media_role="avatar_im",
            source_id=uuid4(),
            scope="story",
            fallback_text="Portrait pending.",
        )

        payload = media_fragment_to_payload(
            fragment,
            render_profile=MediaRenderProfile(static_inventories=(inventory,)),
            world_id="demo",
            story_id="story-1",
            world_media_root=tmp_path,
            story_media_root=tmp_path / "story_media" / "story-1",
        )

        assert payload is not None
        assert payload["scope"] == "world"
        assert payload["url"] == "/media/world/demo/placeholder.svg"

    def test_pending_media_falls_back_to_text_when_no_static_fallback(self) -> None:
        fragment = MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.PENDING,
                adapted_spec_hash="pending-2",
                data_type=MediaDataType.IMAGE,
            ),
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            media_role="avatar_im",
            source_id=uuid4(),
            scope="story",
            fallback_text="Portrait pending.",
        )

        payload = media_fragment_to_payload(fragment)

        assert payload == {
            "fragment_type": "content",
            "content": "Portrait pending.",
            "text": "Portrait pending.",
            "source_id": str(fragment.source_id),
        }

    def test_failed_media_without_fallback_is_discarded(self) -> None:
        fragment = MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.FAILED,
                adapted_spec_hash="failed-1",
                data_type=MediaDataType.IMAGE,
            ),
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            media_role="avatar_im",
            source_id=uuid4(),
            scope="story",
        )

        assert media_fragment_to_payload(fragment) is None
