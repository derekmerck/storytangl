"""Tests for sync inline media-spec generation.

Organized by functionality:
- Spec fingerprinting: stable dedupe identifiers for typed inline specs
- Story provisioning: sync-generated story media binds to media deps
- Journal/service flow: generated story media emits canonical fragments and URLs
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tangl.journal.media import MediaFragment
from tangl.media.media_creators.svg_forge.vector_spec import VectorSpec
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.service.media import media_fragment_to_payload
from tangl.story.fabula import World
from tangl.story.system_handlers import render_block_media


# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================


class StubVectorCreator:
    """Deterministic sync SVG creator used by inline media-spec tests."""

    def create_media(self, spec: VectorSpec) -> tuple[str, VectorSpec]:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
            f"<title>{spec.label or 'generated'}</title>"
            '<circle cx="16" cy="16" r="14" fill="red"/></svg>'
        )
        return svg, spec


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _inline_spec_script(*, media_items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "label": "inline_media_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Generated media",
                        "media": media_items,
                    }
                }
            }
        },
    }


def _story_from_inline_spec(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    media_items: list[dict[str, object]],
):
    def _creator_service(cls):
        return StubVectorCreator()

    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    monkeypatch.setattr(
        VectorSpec,
        "get_creation_service",
        classmethod(_creator_service),
    )

    world = World.from_script_data(script_data=_inline_spec_script(media_items=media_items))
    result = world.create_story("inline-media-story")
    story = result.graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    return story, block


# ============================================================================
# Spec Fingerprinting
# ============================================================================


class TestSpecFingerprinting:
    """Tests for identity-free inline media-spec fingerprints."""

    def test_vector_spec_fingerprint_ignores_uid(self) -> None:
        first = VectorSpec(label="portrait")
        second = VectorSpec(label="portrait")

        assert first.uid != second.uid
        assert first.spec_fingerprint() == second.spec_fingerprint()


# ============================================================================
# Story Provisioning
# ============================================================================


class TestSyncInlineSpecProvisioning:
    """Tests for sync-generated inline media specs through story materialization."""

    def test_inline_vector_spec_creates_story_scoped_media_dep(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        story, block = _story_from_inline_spec(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            media_items=[
                {
                    "spec": {"kind": "vector", "label": "hero_portrait"},
                    "media_role": "avatar_im",
                }
            ],
        )

        deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]
        assert len(deps) == 1

        provider = deps[0].provider
        assert isinstance(provider, MediaRIT)
        assert provider.path is not None and provider.path.exists()
        assert provider.path.parent == story.story_resources.resource_path
        assert provider.spec_fingerprint is not None
        assert provider.derivation_spec is not None
        assert provider.execution_spec is not None
        assert deps[0].scope == "story"

    def test_identical_inline_specs_reuse_existing_story_media(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        story, block = _story_from_inline_spec(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            media_items=[
                {
                    "spec": {"kind": "vector", "label": "shared_portrait"},
                    "media_role": "avatar_im",
                },
                {
                    "spec": {"kind": "vector", "label": "shared_portrait"},
                    "media_role": "avatar_im",
                },
            ],
        )

        deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]
        assert len(deps) == 2
        assert deps[0].provider is not None
        assert deps[1].provider is not None
        assert deps[0].provider.uid == deps[1].provider.uid
        assert deps[0].provider.path == deps[1].provider.path


# ============================================================================
# Journal and Service Flow
# ============================================================================


class TestInlineSpecJournalAndServiceFlow:
    """Tests for generated inline specs across journal fragments and service payloads."""

    def test_generated_story_media_dereferences_to_story_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        story, block = _story_from_inline_spec(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            media_items=[
                {
                    "spec": {"kind": "vector", "label": "story_banner"},
                    "media_role": "narrative_im",
                }
            ],
        )

        fragments = render_block_media(caller=block, ctx=SimpleNamespace(get_ns=lambda _caller: {}))
        assert fragments is not None
        fragment = next(item for item in fragments if isinstance(item, MediaFragment))

        payload = media_fragment_to_payload(
            fragment,
            world_id="demo_world",
            story_id=str(story.story_id),
            story_media_root=story.story_resources.resource_path,
        )

        assert payload is not None
        assert payload["content_format"] == "rit"
        assert payload["scope"] == "story"
        assert payload["url"].startswith(f"/media/story/{story.story_id}/story_banner-")
        assert payload["url"].endswith(".svg")

    def test_unknown_inline_spec_keeps_placeholder_behavior(self) -> None:
        world = World.from_script_data(
            script_data=_inline_spec_script(
                media_items=[
                    {
                        "spec": {"kind": "unknown_media_spec"},
                        "media_role": "avatar_im",
                    }
                ]
            )
        )
        result = world.create_story("inline-media-story")
        story = result.graph
        block = next(node for node in story.values() if getattr(node, "label", None) == "start")

        fragments = render_block_media(caller=block, ctx=SimpleNamespace(get_ns=lambda _caller: {}))

        assert fragments is not None
        fragment = next(item for item in fragments if isinstance(item, MediaFragment))
        assert fragment.content_format == "json"
        assert fragment.content["source_kind"] == "potential"
        assert fragment.content["unresolved_reason"] == "unsupported_media_spec"
