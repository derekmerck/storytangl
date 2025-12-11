import pytest

from tangl.entity.mixins import Lockable, AvailabilityHandler, Renderable, HasEffects, Conditional
from tangl.graph import Graph, Node
from tangl.graph.mixins import TraversableNode, TraversableGraph, Edge, TraversalHandler

# -- classes ------------

class TestTraversableGraph(TraversableGraph, Graph):
    pass

class TestTraversableNode(Lockable, TraversableNode, Node):
    name: str = None
    entered: bool = False
    exited: bool = False

    @TraversalHandler.enter_strategy
    def _set_enter_flag(self, *args, **kwargs):
        print( f"entering {self.label}" )
        self.entered = True
    _set_enter_flag.strategy_priority = 0

    @TraversalHandler.exit_strategy
    def _set_exit_flag(self, *args, **kwargs):
        print( f"exiting {self.label}" )
        self.exited = True
    _set_exit_flag.strategy_priority = 0

class TestCompleteTraversableNode(Lockable, Renderable, HasEffects, Conditional, TraversableNode, Node):
    pass

class TestEdge(HasEffects, Conditional, Edge):
    pass

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
    edge = TestEdge(successor_ref=successor_node.uid)
    traversable_node.add_child(edge)
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
    traversable_node.visit()
    assert traversable_node.visited, "Node should be marked as visited"
    assert len(traversable_node.visits) == 1, "Visits count should be incremented"

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

    edge = TestEdge(successor_ref="Successor")
    pred_node.add_child(edge)

    assert edge.predecessor is pred_node
    assert edge.successor is succ_node

def test_traversal_trigger_types(traversable_node):
    successor_node = create_test_node("TestNode")
    for trigger_type in ["enter", "exit", None]:
        edge = TestEdge(parent=traversable_node,
                        successor_ref=successor_node.uid,
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
    available_edge = TestEdge(successor_ref=available_node.uid, graph=graph)
    unavailable_edge = TestEdge(successor_ref=unavailable_node.uid, graph=graph)

    assert available_edge._check_successor() is True
    assert available_edge.available() is True
    assert unavailable_edge._check_successor() is False
    assert unavailable_node.available() is False

def test_traversable_visit_tracking(setup_graph_and_nodes):
    graph, node1, _ = setup_graph_and_nodes
    assert not node1.visited
    node1.visit()
    assert node1.visited
    assert node1.turns_since() == 0  # Assuming graph.choice_counter is 0

def test_edge_navigation(setup_graph_and_nodes):
    _, node1, node2 = setup_graph_and_nodes
    edge = TestEdge(successor_ref=node2.uid)
    node1.add_child(edge)
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
    edge1 = TestEdge(successor_ref=node2.uid)
    edge2 = TestEdge(successor_ref=node3.uid)
    node1.add_child(edge1)
    node2.add_child(edge2)

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

    edge1.activation = "exit"
    edge2.activation = "exit"

    TraversalHandler.enter(node1)
    # continues through all nodes
    assert node1.entered
    assert node1.visited
    assert node1.exited
    assert node2.entered
    assert node2.visited
    assert node2.exited
    assert node3.entered
    assert node3.visited
    assert not node3.exited


def test_redirects(flat_chain_graph):
    graph, node1, node2, node3, edge1, edge2 = flat_chain_graph

    edge1.activation = "enter"
    edge2.activation = "enter"

    TraversalHandler.enter(node1)
    # jumps node1, node2 and arrives at node3
    assert node1.entered
    assert not node1.visited
    assert node1.exited
    assert node2.entered
    assert not node2.visited
    assert node2.exited
    assert node3.entered
    assert node3.visited
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
    edge = TestEdge(successor_ref=grandchild2.uid)
    grandchild1.add_child(edge)

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

    edge.activation = "enter"

    TraversalHandler.enter(grandchild1)

    assert child1.entered is False
    assert not child1.visited
    assert not child1.exited is True
    assert child2.entered is True
    # This is a side-effect, even though this node was never independently targeted for a visit, it comes from calling enter on parent and not getting a redirect
    assert child2.visited
    # Hanging open, it still wants to be closed
    assert child2.exited is False

    assert grandchild1.entered
    assert not grandchild1.visited
    assert grandchild1.exited
    assert grandchild2.entered
    assert grandchild2.visited
    assert not grandchild2.exited


def test_cross_tree_continue(complex_tree_graph):
    graph, root, child1, child2, grandchild1, grandchild2, edge = complex_tree_graph

    edge.activation = "exit"

    TraversalHandler.enter(grandchild1)

    assert child1.entered is False
    assert not child1.visited
    assert child1.exited is True
    assert child2.entered is True
    assert child2.visited
    assert child2.exited is False

    assert grandchild1.entered
    assert grandchild1.visited
    assert grandchild2.entered
    assert grandchild2.visited


def test_graph_cursor_functionality():
    node = TestTraversableNode()
    graph = TestTraversableGraph()
    graph.add_node(node)
    graph.cursor = node

    assert graph.cursor_id == node.uid
    assert graph.cursor == node


def test_graph_find_entry_functionality():
    node = TestTraversableNode(tags={'is_entry'})
    assert node.is_entry
    graph = TestTraversableGraph()
    graph.add_node(node)
    graph.enter()

    assert graph.cursor_id == node.uid
    assert graph.cursor == node
