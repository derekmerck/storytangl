"""Media payloads carry their staging, and their sprite sheets beside the still.

Two claims. First, per-use staging reaches clients at all: before this, every media
payload dropped ``staging_hints``, so only an in-process client could place, flip
or animate anything. Second, a still's sheets are transported exactly as the still
is -- URL beside URL, path beside path, bytes beside bytes -- because they go
through the same resolution function.
"""

from __future__ import annotations

from base64 import b64decode
from pathlib import Path

import pytest
from PIL import Image

from tangl.core import Graph
from tangl.journal.fragments import MediaFragment
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.presentation.hints import StagingHints
from tangl.service.media import MediaContentProfile, MediaRenderProfile, media_fragment_to_payload

PROFILES = [MediaContentProfile.MEDIA_SERVER, MediaContentProfile.PASSTHROUGH, MediaContentProfile.INLINE_DATA]


@pytest.fixture
def world(tmp_path: Path):
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGBA", (10, 12), (10, 10, 10, 255)).save(images / "hero.png")
    Image.new("RGBA", (20, 12), (20, 20, 20, 255)).save(images / "hero-idle-2x1-400ms.png")
    manager = ResourceManager(tmp_path)
    manager.index_directory("images")
    return tmp_path, manager


def _fragment(rit: MediaRIT, **hints) -> MediaFragment:
    return MediaFragment(
        content=rit, content_format="rit", media_role="dialog_im",
        staging_hints=StagingHints(**hints) if hints else None,
    )


def _payload(fragment: MediaFragment, root: Path, profile: MediaContentProfile) -> dict:
    return media_fragment_to_payload(
        fragment, render_profile=MediaRenderProfile(content_profile=profile), world_id="w", world_media_root=root
    )


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.value)
def test_staging_hints_travel_with_the_media_they_stage(world, profile) -> None:
    root, manager = world
    payload = _payload(_fragment(manager.get_rit("hero.png"), media_x="right", media_flip_h=True,
                                 media_clip="idle", media_timing="loop"), root, profile)

    assert payload["staging_hints"] == {"media_x": "right", "media_flip_h": True,
                                        "media_timing": "loop", "media_clip": "idle"}


def test_media_without_hints_carries_no_empty_hint_object(world) -> None:
    root, manager = world

    assert "staging_hints" not in _payload(_fragment(manager.get_rit("hero.png")), root, PROFILES[0])


@pytest.mark.parametrize(
    ("profile", "transport"),
    [(MediaContentProfile.MEDIA_SERVER, "url"), (MediaContentProfile.PASSTHROUGH, "path"),
     (MediaContentProfile.INLINE_DATA, "data")],
    ids=lambda v: getattr(v, "value", v),
)
def test_a_sheet_is_transported_the_way_its_still_is(world, profile, transport) -> None:
    root, manager = world
    payload = _payload(_fragment(manager.get_rit("hero.png"), media_clip="idle"), root, profile)
    [sheet] = payload["sprite_sheets"]

    assert payload["content_format"] == sheet["content_format"] == transport
    assert transport in payload and transport in sheet
    assert sheet[transport] != payload[transport]
    assert sheet["manifest"]["meta"]["frameTags"][0]["name"] == "idle"
    assert sheet["content_hash"] and sheet["rit_id"] != payload["rit_id"]


def test_inline_sheet_bytes_are_the_sheet_not_the_still(world) -> None:
    root, manager = world
    payload = _payload(_fragment(manager.get_rit("hero.png")), root, MediaContentProfile.INLINE_DATA)

    sheet_bytes = b64decode(payload["sprite_sheets"][0]["data"])

    assert sheet_bytes == (root / "images" / "hero-idle-2x1-400ms.png").read_bytes()


def test_a_sheet_only_carries_transport_not_the_stills_role_or_identity(world) -> None:
    root, manager = world
    [sheet] = _payload(_fragment(manager.get_rit("hero.png")), root, PROFILES[0])["sprite_sheets"]

    assert set(sheet) <= {"content_format", "media_type", "url", "path", "data", "rit_id", "content_hash", "manifest"}


def test_a_sheet_that_cannot_be_resolved_is_left_out_and_the_still_still_arrives(world) -> None:
    root, manager = world
    rit = manager.get_rit("hero.png")
    (root / "images" / "hero-idle-2x1-400ms.png").unlink()

    payload = _payload(_fragment(rit), root, MediaContentProfile.PASSTHROUGH)

    assert payload["content_format"] == "path"
    assert "sprite_sheets" not in payload


def test_a_still_restored_from_a_saved_graph_still_delivers_its_sheet(world) -> None:
    """End to end over the seam that decided the design: persistence, then the wire."""

    root, manager = world
    graph = Graph()
    graph.add(MediaRIT.structure(manager.get_rit("hero.png").unstructure()))
    restored = next(e for e in Graph.structure(graph.unstructure()).values() if isinstance(e, MediaRIT))

    payload = _payload(_fragment(restored, media_clip="idle"), root, MediaContentProfile.MEDIA_SERVER)

    assert [s["manifest"]["meta"]["image"] for s in payload["sprite_sheets"]] == ["hero-idle-2x1-400ms.png"]
