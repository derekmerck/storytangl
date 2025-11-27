from __future__ import annotations

from pathlib import Path

from tangl.journal.media import MediaFragment
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.media_dependency import MediaDep
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.story.episode.block import Block
from tangl.story.fabula.world_loader import WorldLoader
from tangl.vm import ResolutionPhase as P
from tangl.vm.context import Context
from tangl.vm.frame import Frame


WORLD_ROOT = Path("engine/tests/resources/worlds")


def test_media_full_flow_world_scope() -> None:
    """E2E: YAML world -> MediaDeps -> bound RITs -> media fragments with URLs."""

    loader = WorldLoader(world_dirs=[WORLD_ROOT])
    loader.discover_bundles()
    world = loader.load_world("media_e2e")

    story = world.create_story("Media E2E Story")

    blocks = [node for node in story.values() if isinstance(node, Block)]
    assert blocks
    block = next(b for b in blocks if b.label == "tavern_entrance")

    frame = Frame(graph=story, cursor_id=block.uid)
    ctx = Context(graph=story, cursor_id=block.uid)
    frame.context = ctx
    frame.run_phase(P.PLANNING)

    media_deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]
    assert media_deps
    dep = media_deps[0]
    assert dep.destination is not None
    assert isinstance(dep.destination, MediaRIT)

    fragments = frame.run_phase(P.JOURNAL)
    assert fragments

    media_frags = [frag for frag in fragments if isinstance(frag, MediaFragment)]
    assert media_frags
    frag = media_frags[0]

    controller = RuntimeController()
    world_id = getattr(world, "uid", "media_e2e")
    deref = controller._dereference_media(frag, world_id=world_id)

    assert deref["fragment_type"] == "media"
    assert deref["url"].startswith(f"/media/world/{world_id}/")
    assert deref["url"].endswith(".png")
