import pytest

from tangl.core import Entity, Node
from tangl.core.behavior import HandlerLayer
from tangl.story.story_graph import StoryGraph
from tangl.story.fabula import World

from .conftest import _make_world, _base_script

@pytest.fixture
def world():
    World.clear_instances()
    yield _make_world(_base_script())
    World.clear_instances()

def test_world_serializes(world):

    unstructured = world.unstructure()
    print(unstructured)
    structured = world.structure(unstructured)
    assert structured is world

def test_story_graph_serializes(world):
    story_graph = StoryGraph(world=world)

    unstructured = story_graph.unstructure()
    print( unstructured )
    structured = Entity.structure(unstructured)

    assert story_graph.world is world
    assert story_graph == structured

def test_story_graph_surfaces_story_disp(world):
    graph = StoryGraph(world=world)
    start = Node(label="start")
    graph.add(start)
    from tangl.vm import Frame
    f = Frame(graph=graph, cursor_id=start.uid)

    # Check active layers for APPLICATION layer, provided by story graph
    active_layers = [reg.handler_layer for reg in f.context.get_active_layers()]
    print(active_layers)
    assert HandlerLayer.APPLICATION in active_layers

    # Check active layers for LOCAL layer, provided by context itself in this case
    f.context.local_behaviors.add_behavior(lambda _, **__: "foo")
    active_layers = [reg.handler_layer for reg in f.context.get_active_layers()]
    print( active_layers )
    assert HandlerLayer.LOCAL in active_layers

    # todo: once world has an associated dispatch, we can check for AUTHOR layer too.