from typing import Type, Mapping, Optional, Any

from pluggy import HookimplMarker
import pytest

from tangl.entity.mixins import HasNamespace, Renderable
from tangl.graph import Node, GraphFactory
from tangl.graph.mixins import Associating, TraversableNode, TraversableGraph, Edge
from tangl.world import World, WorldHandler
from tangl.script import ScriptManager
from tangl.story import StoryHandler
from tangl.service.response_handler import ResponseHandler
from tangl.plugin_spec import PLUGIN_LABEL

hookimpl = HookimplMarker(PLUGIN_LABEL)

class TestPlugin:
    def __init__(self):
        self.on_new_entity_called = False
        self.on_get_namespace_called = False
        self.on_render_called = False

        self.on_init_factory_called = False

        self.on_init_graph_called = False
        self.on_enter_graph_called = False
        self.on_exit_graph_called = False
        self.on_get_traversal_status_called = False

        self.on_init_node_called = False
        self.on_enter_node_called = False
        self.on_exit_node_called = False
        self.on_associate_with_called = False
        self.on_disassociate_from_called = False

        self.on_prepare_media_called = False
        self.on_handle_response_called = False


    @hookimpl
    def on_new_entity(self, obj_cls: Type[Node], data: dict) -> Type[Node]:
        self.on_new_entity_called = True

    @hookimpl
    def on_get_namespace(self, entity: HasNamespace) -> Mapping:
        self.on_get_namespace_called = True

    @hookimpl
    def on_render(self, entity: Renderable) -> Mapping:
        self.on_render_called = True

    # graph/node hooks

    @hookimpl
    def on_init_node(self, node: Node):
        self.on_init_node_called = True
        node.locals['test_called'] = True

    @hookimpl
    def on_associate_with(self, node: Associating, other: Associating, as_parent: bool):
        self.on_associate_with_called = True

    @hookimpl
    def on_disassociate_from(self, node: Associating, other: Associating):
        self.on_disassociate_from_called = True

    @hookimpl
    def on_enter_node(self, node: TraversableNode) -> Optional[Edge]:
        self.on_enter_node_called = True

    @hookimpl
    def on_exit_node(self, node: TraversableNode) -> Optional[Edge]:
        self.on_exit_node_called = True

    @hookimpl
    def on_init_graph(self, graph: TraversableGraph):
        self.on_init_graph_called = True
        graph.locals['test_called'] = True

    @hookimpl
    def on_exit_graph(self, graph: TraversableGraph):
        self.on_exit_graph_called = True

    @hookimpl
    def on_get_traversal_status(self, graph: TraversableGraph) -> Mapping | list[Mapping]:
        self.on_get_traversal_status_called = True
        return [{"current_block": graph.cursor.label}]

    # other hooks

    @hookimpl
    def on_init_factory(self, factory: GraphFactory):
        self.on_init_factory_called = True
        factory.locals['test_called'] = True

    @hookimpl
    def on_prepare_media(self, node: 'MediaNode', forge_kwargs: dict, spec_overrides: dict) -> Any:
        self.on_prepare_media_called = True

    @hookimpl
    def on_handle_response(self, response: 'ServiceResponse') -> Any:
        self.on_handle_response_called = True

def test_plugin_callbacks(sample_world_sf_dict):

    World.clear_instances()
    # get rid of unique block class since we don't care if we can instantiate specials right now
    sample_world_sf_dict['scenes']['scene1']['blocks']['child2'].pop('obj_cls')
    sm = ScriptManager.from_dict(sample_world_sf_dict)

    # Register the test plugin
    test_plugin = TestPlugin()
    # Create a dummy world
    world = World(label=sm.script.label, script_manager=sm, plugins=test_plugin)
    # should call factory-init
    assert test_plugin.on_init_factory_called

    # Initialize a world, story, and node
    story = WorldHandler.create_story(world)
    # should call story-init
    assert test_plugin.on_init_graph_called

    StoryHandler.enter(story)
    # should call graph-enter
    # todo: enter graph not called
    # assert test_plugin.on_enter_graph_called
    assert story.cursor.path == "scene1/start"

    StoryHandler.enter(story.cursor)
    update = StoryHandler.get_update(story)
    print( update )

    ResponseHandler.format_response(update)
    # should call handle_response
    # todo: handle response not called
    # assert test_plugin.on_handle_response_called

    status = StoryHandler.get_status(story)
    print( status )

    action = story.cursor.actions[0]
    assert action.available()
    StoryHandler.follow_edge( action )
    status = StoryHandler.get_status(story)

    story.exit()

    assert test_plugin.on_new_entity_called
    assert test_plugin.on_get_namespace_called
    assert test_plugin.on_render_called

    assert test_plugin.on_init_node_called
    assert test_plugin.on_enter_node_called
    assert test_plugin.on_exit_node_called

    assert test_plugin.on_init_graph_called
    # assert test_plugin.on_enter_graph_called
    assert test_plugin.on_exit_graph_called
    assert test_plugin.on_get_traversal_status_called

    # todo: association plugin test
    # assert test_plugin.on_associate_with_called
    # assert test_plugin.on_disassociate_from_called

    assert test_plugin.on_init_factory_called
    # todo: prepare media plugin test
    # assert test_plugin.on_prepare_media_called
    # assert test_plugin.on_handle_response_called
