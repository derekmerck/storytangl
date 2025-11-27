from tangl.core.graph.edge import Edge
from tangl.core.graph.graph import Graph
from pathlib import Path
import pytest

from tangl.core.graph.edge import Edge
from tangl.core.graph.node import Node
from tangl.story.episode.block import Block as ReferenceBlock
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.frame import ChoiceEdge

class SimpleBlock(Node):
    content: str | None = None


class SimpleAction(Edge):
    text: str | None = None


def _make_world(script_data: dict) -> World:
    World.clear_instances()
    script_manager = ScriptManager.from_data(script_data)
    world = World(label="test_world", script_manager=script_manager)
    world.domain_manager.register_class("Block", SimpleBlock)
    world.domain_manager.register_class("SimpleAction", SimpleAction)
    return world


def _base_script() -> dict:
    return {
        "label": "test_script",
        "metadata": {"title": "Test", "author": "Tester"},
        "actors": {
            "hero": {"obj_cls": "tangl.core.graph.node.Node"},
        },
        "locations": {
            "town": {"obj_cls": "tangl.core.graph.node.Node"},
        },
    }


@pytest.fixture
def media_mvp_path() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "worlds" / "media_mvp"
