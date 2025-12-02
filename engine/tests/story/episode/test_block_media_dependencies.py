from pathlib import Path
from types import SimpleNamespace

import pytest

from tangl.media.media_resource.media_dependency import MediaDep
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.story.fabula.world_loader import WorldLoader
from tangl.story.fabula.world import World
from tangl.story.episode.block import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import ResolutionPhase as P
from tangl.vm.frame import Frame


@pytest.fixture(autouse=True)
def clear_world_singleton():
    World.clear_instances()
    yield
    World.clear_instances()


class _MediaGraph(StoryGraph):
    def __contains__(self, item):
        from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag

        if isinstance(item, MediaResourceInventoryTag):
            return True
        return super().__contains__(item)


class _StubWorld:
    def __init__(self, resource_manager: ResourceManager, name: str) -> None:
        self.resource_manager = resource_manager
        self.name = name

    def unstructure(self) -> dict[str, str]:
        return {"name": self.name}


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


def test_planning_provisions_inline_media(tmp_path) -> None:
    graph = _MediaGraph(label="inline-media")
    world = _StubWorld(resource_manager=ResourceManager(tmp_path), name="inline")
    graph.world = world

    block = graph.add_node(obj_cls=Block, label="start")
    graph.initial_cursor_id = block.uid

    dep = MediaDep(graph=graph, source=block, media_data=b"inline-bytes")
    graph.add(dep)

    frame = Frame(graph=graph, cursor_id=block.uid)
    frame.run_phase(P.PLANNING)

    assert dep.destination is not None
    assert world.resource_manager.registry.find_one(uid=dep.destination.uid) is not None
