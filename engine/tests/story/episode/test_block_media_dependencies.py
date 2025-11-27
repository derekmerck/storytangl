from pathlib import Path

from tangl.media.media_resource.media_dependency import MediaDep
from tangl.story.fabula.world_loader import WorldLoader
from tangl.story.fabula.world import World
from tangl.vm import ResolutionPhase as P
from tangl.vm.frame import Frame


def _load_media_world(media_mvp_path: Path) -> World:
    loader = WorldLoader([media_mvp_path.parent])
    loader.discover_bundles()
    return loader.load_world("media_mvp")


def test_block_media_dependencies_are_attached(media_mvp_path) -> None:
    world = _load_media_world(media_mvp_path)
    story = world.create_story("Media MVP Story")

    block = story.get(story.initial_cursor_id)
    deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]

    assert len(deps) == 1
    dep = deps[0]
    assert dep.requirement.criteria == {"path": "test_image.svg"}
    assert dep.destination is None


def test_planning_binds_media_deps_to_registry(media_mvp_path) -> None:
    world = _load_media_world(media_mvp_path)
    story = world.create_story("Media MVP Story")
    block = story.get(story.initial_cursor_id)

    frame = Frame(graph=story, cursor_id=story.initial_cursor_id)
    frame.run_phase(P.PLANNING)

    deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]
    assert deps and deps[0].destination is not None
    assert deps[0].destination.path.name == "test_image.svg"
