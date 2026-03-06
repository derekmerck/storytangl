from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.journal.media import MediaFragment
from tangl.media import system_media
from tangl.media.media_resource.media_dependency import MediaDep
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.vm import AnonymousEdge, Frame, ResolutionPhase as P

from media.helpers import MediaWorld, build_world_with_logo_media_block

pytestmark = pytest.mark.skip(
    reason="Deferred media planning parity; tracked as a dedicated follow-up.",
)


def _make_frame(story, block):
    try:
        return Frame(graph=story, cursor=block)
    except TypeError:
        return Frame(graph=story, cursor_id=block.uid)


def _run_planning(frame, block):
    if hasattr(frame, "run_phase"):
        frame.run_phase(P.PLANNING)
        return
    frame.follow_edge(AnonymousEdge(successor=block, entry_phase=P.PLANNING))


def _run_journal(frame, block):
    if hasattr(frame, "run_phase"):
        return frame.run_phase(P.JOURNAL)
    frame.follow_edge(AnonymousEdge(successor=block, entry_phase=P.JOURNAL))
    return [record for record in frame.output_stream.values() if isinstance(record, MediaFragment)]


def test_system_media_fallback(tmp_path, monkeypatch):
    """PLANNING should resolve media from system scope when world assets are missing."""

    sys_media_dir = tmp_path / "sys_media"
    sys_media_dir.mkdir()
    (sys_media_dir / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>'
    )

    system_media.get_system_resource_manager.cache_clear()
    monkeypatch.setattr(system_media, "get_sys_media_dir", lambda: sys_media_dir)

    media_world = build_world_with_logo_media_block(world_media_dir=tmp_path / "world_media")
    world, story, block = media_world
    story.uid = uuid4()

    frame = _make_frame(story, block)
    _run_planning(frame, block)

    media_dep = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    assert media_dep.destination is not None
    assert media_dep.scope == "sys"

    fragments = _run_journal(frame, block)
    media_frag = next(frag for frag in fragments if isinstance(frag, MediaFragment))

    controller = RuntimeController()
    result = controller._dereference_media(media_frag, world_id=str(world.label))

    assert result["scope"] == "sys"
    assert result["url"].startswith("/media/sys/")
    assert result["url"].endswith("logo.svg")


def test_world_media_preferred_over_system(tmp_path, monkeypatch):
    world_media_dir = tmp_path / "world_media"
    world_media_dir.mkdir()
    world_asset = world_media_dir / "logo.svg"
    world_asset.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<rect width="32" height="32" fill="green"/></svg>'
    )

    sys_media_dir = tmp_path / "sys_media"
    sys_media_dir.mkdir()
    (sys_media_dir / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<rect width="32" height="32" fill="blue"/></svg>'
    )

    system_media.get_system_resource_manager.cache_clear()
    monkeypatch.setattr(system_media, "get_sys_media_dir", lambda: sys_media_dir)

    media_world: MediaWorld = build_world_with_logo_media_block(world_media_dir=world_media_dir)
    world, story, block = media_world

    frame = _make_frame(story, block)
    _run_planning(frame, block)

    media_dep = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    assert media_dep.destination is not None
    assert media_dep.scope == "world"
    assert getattr(media_dep.destination, "path", None) == world_asset
