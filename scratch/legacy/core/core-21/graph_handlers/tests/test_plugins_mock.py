import pytest
from unittest.mock import MagicMock, create_autospec

from tangl.entity.mixins import *
from tangl.graph import Node
from tangl.graph.mixins.plugins import *

@pytest.fixture
def mock_plugin_manager():
    # Create a mock PluginManager
    pm = create_autospec(PluginManager)
    pm.hook = create_autospec(GraphPluginSpec, instance=True)
    return pm

class TestPluginNode(HasPluginManager,
                     Renderable,
                     HasNamespace,
                     TraversableNode,
                     Associating,
                     Node):
    ...

class TestPluginGraph(HasPluginManager,
                      TraversableGraph,
                      Graph):
    ...

class TestPluginFactory(HasPluginManager,
                        GraphFactory):
    ...

def test_node_plugin_hooks(mock_plugin_manager):

    test_node = TestPluginNode(plugin_manager=mock_plugin_manager)

    # Simulate a scenario that triggers a plugin hook
    test_node.get_namespace()
    # Assert that the appropriate hook was called
    test_node.pm.hook.on_get_namespace.assert_called_once()

    test_node.render()
    test_node.pm.hook.on_render.assert_called_once()

    test_node.enter()
    test_node.pm.hook.on_enter_node.assert_called_once()

    test_node.exit()
    test_node.pm.hook.on_exit_node.assert_called_once()

    other = TestPluginNode(plugin_manager=mock_plugin_manager)

    test_node.associate_with(other)
    assert test_node.pm.hook.on_associate_with.call_count == 2  # once for each partner

    test_node.disassociate_from(other)
    assert test_node.pm.hook.on_disassociate_from.call_count == 2  # once for each partner

def test_graph_plugin_hooks(mock_plugin_manager):

    test_graph = TestPluginGraph(plugin_manager=mock_plugin_manager)

    test_graph.enter()
    mock_plugin_manager.hook.on_enter_graph.assert_called_once()

    test_graph.exit()
    mock_plugin_manager.hook.on_exit_graph.assert_called_once()

def test_on_new_entity(mock_plugin_manager):
    node = TestPluginNode(obj_cls='TestPluginNode',
                          _pm=mock_plugin_manager,
                          plugin_manager=mock_plugin_manager)
    mock_plugin_manager.hook.on_init_node.assert_called_once()
    mock_plugin_manager.hook.on_new_entity.assert_called_once()

def test_on_new_graph(mock_plugin_manager):
    graph = TestPluginGraph(obj_cls=TestPluginGraph, _pm=mock_plugin_manager, plugin_manager=mock_plugin_manager)
    mock_plugin_manager.hook.on_init_graph.assert_called_once()
    mock_plugin_manager.hook.on_new_entity.assert_called_once()

def test_on_new_factory(mock_plugin_manager):
    factory = TestPluginFactory(obj_cls=TestPluginFactory, _pm=mock_plugin_manager, plugin_manager=mock_plugin_manager)
    mock_plugin_manager.hook.on_init_factory.assert_called_once()
    mock_plugin_manager.hook.on_new_entity.assert_called_once()
