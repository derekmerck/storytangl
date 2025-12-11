import logging

import pytest

from tangl.core.entity.handlers import HasTags
from tangl.core.entity.handlers import Lockable, AvailabilityHandler, Renderable, HasEffects, Conditional
from tangl.core.graph import Graph, Node, Edge
from tangl.core.graph.handlers import TraversableNode, TraversableGraph, TraversalHandler, TraversalStage

logger = logging.getLogger(f"tangl.test.graph")

# -- classes ------------

TestTraversableGraph  = type('TestTraversableGraph',  (TraversableGraph, Graph), {} )

class TestTraversableNode(HasTags, Lockable, TraversableNode, Node):
    name: str = None
    entered: bool = False
    exited: bool = False

    @TraversalHandler.enter_strategy(priority=0)
    def _set_enter_flag(self, **kwargs):
        logger.info( f"Test enter func: entering {self!r}" )
        self.entered = True

    @TraversalHandler.exit_strategy(priority=0)
    def _set_exit_flag(self, **kwargs):
        logger.info( f"Test exit func: exiting {self!r}" )
        self.exited = True

TestCompleteTraversableNode  = type('TestCompleteTraversableNode',  (Lockable, Renderable, HasEffects, Conditional, TraversableNode, Node), {} )

TestEdge  = type('TestEdge',  (HasEffects, Conditional, Lockable, Edge), {} )

# -- fixtures ------------

@pytest.fixture
def test_graph():
    return TestTraversableGraph()

def create_test_node(label: str, **kwargs) -> TraversableNode:
    # Create a simple Traversable node for testing
    return TestTraversableNode(label=label, **kwargs)

@pytest.fixture
def traversable_node(test_graph):
    node = create_test_node(label="test_node", name="Test Node")
    test_graph.add_node(node)
    return node

@pytest.fixture
def setup_graph_and_nodes(test_graph):
    node1 = TestTraversableNode(label='node1')
    node2 = TestTraversableNode(label='node2')
    test_graph.add_node(node1)
    test_graph.add_node(node2)
    return test_graph, node1, node2

@pytest.fixture
def graph_with_edge(traversable_node):
    successor_node = TestTraversableNode(graph=traversable_node.graph, label="successor", name="Node A")
    edge = TestEdge(successor=successor_node, predecessor=traversable_node)
    return traversable_node.graph, traversable_node, edge, successor_node

# @pytest.fixture
# def mock_graph():
#     graph = create_autospec(TraversableGraph)
#     graph.journal = Journal()
#     graph.choice_counter = 0
#     return graph
#
# @pytest.fixture
# def mock_edge():
#     edge = create_autospec(EdgeNode)
#     edge.available.return_value = True
#     edge.trigger = EdgeNode.TraversalTrigger.CHOICE  # Manually specify trigger
#     edge.successor = CompleteTraversableNode(text="You made it!")
#     return edge

# -- tests ------------

def test_node_initialization(traversable_node):
    assert traversable_node.label == "test_node"
    assert traversable_node.name == "Test Node"

    assert traversable_node.graph.get_node("test_node") == traversable_node

def test_node_visit(traversable_node):
    assert not traversable_node.visited, "Node should not be visited initially"
    traversable_node._departure_bookkeeping()
    assert traversable_node.visited, "Node should be marked as visited"
    # assert len(traversable_node.visits) == 1, "Visits count should be incremented"

def test_node_ancestor_tracking(traversable_node):
    test_graph = traversable_node.graph
    parent_node = TestTraversableNode(graph=test_graph, label="parent_node", name="Parent Node")
    test_graph.add_node(parent_node)
    parent_node.add_child(traversable_node)
    assert traversable_node.ancestors() == [traversable_node, parent_node], "Node should correctly track its ancestors"
    assert traversable_node.path == "parent_node/test_node"

def test_edge_construction_and_addition(graph_with_edge):
    graph, traversable_node, edge, successor_node = graph_with_edge
    assert edge in traversable_node.edges, "Graph should correctly add and track edges between nodes"

def test_predecessor_successor_relationships():
    graph = Graph()
    pred_node = create_test_node("Predecessor")
    graph.add_node(pred_node)
    succ_node = create_test_node("Successor")
    graph.add_node(succ_node)

    edge = TestEdge(successor="Successor", predecessor=pred_node)
    pred_node.add_child(edge)

    assert edge.predecessor is pred_node
    assert edge.successor is succ_node

def test_traversal_trigger_types(traversable_node):
    successor_node = create_test_node("TestNode")
    for trigger_type in ["first", "last", None]:
        edge = TestEdge(predecessor=traversable_node,
                        successor=successor_node,
                        activation=trigger_type)
        assert edge.activation is trigger_type

def test_edge_availability():
    available_node = create_test_node("Available")
    unavailable_node = create_test_node("Unavailable", locked=True)

    assert available_node.available() is True
    assert unavailable_node.available() is False

    graph = Graph()
    graph.add_node(available_node)
    graph.add_node(unavailable_node)
    available_edge = TestEdge(successor=available_node, graph=graph)
    unavailable_edge = TestEdge(successor=unavailable_node, graph=graph)

    assert available_edge._check_successor_avail() is True
    assert available_edge.available() is True
    assert unavailable_edge._check_successor_avail() is False
    assert unavailable_node.available() is False

def test_traversable_visit_tracking(setup_graph_and_nodes):
    graph, node1, _ = setup_graph_and_nodes
    assert not node1.visited
    node1._departure_bookkeeping()
    assert node1.visited
    # assert node1.turns_since() == 0  # Assuming graph.choice_counter is 0

def test_edge_navigation(setup_graph_and_nodes):
    _, node1, node2 = setup_graph_and_nodes
    edge = TestEdge(successor=node2, predecessor=node1)
    # node1.add_child(edge)
    assert edge.predecessor == node1
    assert edge.successor == node2


# -- auto-traversal ---------------

@pytest.fixture
def flat_chain_graph():
    graph = TestTraversableGraph()
    node1 = TestTraversableNode(label="node1")
    node2 = TestTraversableNode(label="node2")
    node3 = TestTraversableNode(label="node3")
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)
    edge1 = TestEdge(successor=node2, predecessor=node1)
    edge2 = TestEdge(successor=node3, predecessor=node2)

    # paranoid confirmation...
    assert node1.entered is False
    assert node1.visited is False
    assert node1.exited is False
    assert node2.entered is False
    assert node2.visited is False
    assert node2.exited is False
    assert node3.entered is False
    assert node3.visited is False
    assert node3.exited is False

    return graph, node1, node2, node3, edge1, edge2


def test_continues(flat_chain_graph):
    graph, node1, node2, node3, edge1, edge2 = flat_chain_graph

    edge1.activation = "last"
    edge2.activation = "last"

    TraversalHandler.enter_node(node1)
    # continues through all nodes
    assert node1.entered
    assert node1.visited
    assert node1.exited
    assert node2.entered
    assert node2.visited
    assert node2.exited
    assert node3.entered
    assert not node3.visited  # doesn't count as visited until it exits
    assert not node3.exited


def test_redirects(flat_chain_graph):
    graph, node1, node2, node3, edge1, edge2 = flat_chain_graph

    edge1.activation = "first"
    edge2.activation = "first"

    TraversalHandler.enter_node(node1)
    # jumps node1, node2 and arrives at node3
    assert node1.entered
    assert not node1.visited
    assert not node1.exited
    assert node2.entered
    assert not node2.visited
    assert not node2.exited
    assert node3.entered
    assert not node3.visited
    assert not node3.exited


@pytest.fixture
def complex_tree_graph():
    graph = TestTraversableGraph()
    root = TestTraversableNode(label="root")
    child1 = TestTraversableNode(label="child1")
    child2 = TestTraversableNode(label="child2")
    grandchild1 = TestTraversableNode(label="grandchild1")
    grandchild2 = TestTraversableNode(label="grandchild2")
    graph.add_node(root)
    root.add_child(child1)
    root.add_child(child2)
    child1.add_child(grandchild1)
    child2.add_child(grandchild2)
    edge = TestEdge(successor=grandchild2, predecessor=grandchild1)
    # grandchild1.add_child(edge)

    assert child1.entered is False
    assert child1.visited is False
    assert child1.exited is False
    assert child2.entered is False
    assert child2.visited is False
    assert child2.exited is False

    assert grandchild1.entered is False
    assert grandchild1.visited is False
    assert grandchild1.exited is False
    assert grandchild2.entered is False
    assert grandchild2.visited is False
    assert grandchild2.exited is False

    return graph, root, child1, child2, grandchild1, grandchild2, edge


def test_cross_tree_redirect(complex_tree_graph):
    graph, root, child1, child2, grandchild1, grandchild2, edge = complex_tree_graph

    edge.activation = "first"

    TraversalHandler.enter_node(grandchild1)
    # there is a redirect between root/child1/grandchild1 and root/child2/grandchild2

    # what behavior do we actually want?

    # -> enter grandchild1
    # -> redirect to grandchild2
    # -> no visit for grandchild2

    # context rectification
    # -> exit grandchild1/doesn't want
    # -> exit child1/doesn't want
    # -> enter child2 (ignore redirects?)

    # -> enter grandchild2
    # -> visit grandchild2

    assert not child1.entered  # never entered
    assert not child1.wants_exit
    assert not child1.visited  # never exits since never entered
    assert not child1.exited

    assert grandchild1.entered  # entered, but redirected before visit
    assert not grandchild1.wants_exit
    assert not grandchild1.visited
    assert not grandchild1.exited

    assert child2.entered      # entered, but hanging open
    assert child2.wants_exit
    assert not child2.visited  # not yet exited
    assert not child2.exited

    assert grandchild2.entered  # entered, but hanging open
    assert grandchild2.wants_exit
    assert not grandchild2.visited
    assert not grandchild2.exited


def test_cross_tree_continue(complex_tree_graph):
    graph, root, child1, child2, grandchild1, grandchild2, edge = complex_tree_graph

    edge.activation = "last"

    TraversalHandler.enter_node(grandchild1)

    assert not child1.entered
    assert not child1.visited
    assert not child1.exited

    assert grandchild1.entered
    assert grandchild1.visited

    assert child2.entered
    assert not child2.visited
    assert not child2.exited

    assert grandchild2.entered
    assert not grandchild2.visited


def test_graph_cursor_functionality():
    node = TestTraversableNode()
    graph = TestTraversableGraph()
    graph.add_node(node)
    graph.cursor = node

    assert graph.cursor_id == node.uid
    assert graph.cursor == node


def test_graph_find_entry_functionality():
    node = TestTraversableNode(tags={'is_entry'}, locked=True)
    graph = TestTraversableGraph()
    graph.add_node(node)

    assert graph.find_entry_node() is None
    node.unlock()
    assert graph.find_entry_node() is node
    assert not node.wants_exit

    graph.enter()
    assert node.wants_exit
    assert graph.cursor_id == node.uid
    assert graph.cursor == node

    with pytest.raises(RuntimeError):
        # should throw if cursor is already set
        graph.enter()
