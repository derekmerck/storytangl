from __future__ import annotations

from uuid import uuid4

from tangl.journal.media import MediaFragment
from tangl.media.media_resource.media_dependency import MediaDep
from tangl.media import system_media
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.vm import ResolutionPhase as P
from tangl.vm.context import Context
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.frame import Frame

from .helpers import build_world_with_logo_media_block


def test_system_media_fallback(tmp_path, monkeypatch):
    """PLANNING should resolve media from system scope when world assets are missing."""

    sys_media_dir = tmp_path / "sys_media"
    sys_media_dir.mkdir()
    (sys_media_dir / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>'
    )

    system_media.get_system_media_context.cache_clear()
    monkeypatch.setattr(system_media, "get_sys_media_dir", lambda: sys_media_dir)

    media_world = build_world_with_logo_media_block(world_media_dir=tmp_path / "world_media")
    world, story, block = media_world
    story.uid = uuid4()

    frame = Frame(graph=story, cursor_id=block.uid)
    ctx = Context(graph=story, cursor_id=block.uid)
    frame.context = ctx

    list(vm_dispatch.dispatch(caller=frame.cursor, ctx=ctx, task=P.INIT))
    assert getattr(world, "system_resource_manager", None) is not None

    frame.run_phase(P.PLANNING)

    media_dep = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    assert media_dep.destination is not None
    assert media_dep.scope == "sys"

    fragments = frame.run_phase(P.JOURNAL)
    media_frag = next(frag for frag in fragments if isinstance(frag, MediaFragment))

    controller = RuntimeController()
    result = controller._dereference_media(media_frag, world_id=str(world.uid))

    assert result["scope"] == "sys"
    assert result["url"].startswith("/media/sys/")
    assert result["url"].endswith("logo.svg")
