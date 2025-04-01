import pytest
from uuid import UUID

from tangl.core import DynamicEdge, Node, Graph


def test_dynamic_edge_validation():
    """Test edge requires at least one linking method"""

    parent = Node()
    edge = DynamicEdge(predecessor_id=parent.uid, successor_ref="abc")

    with pytest.raises(ValueError):
        DynamicEdge(predecessor_id=parent.uid)

@pytest.fixture
def graph() -> Graph:
    graph = Graph()
    parent = Node(label="parent")
    graph.add(parent)
    return graph

def test_resolve_by_ref(graph):
    """Test resolving successor by reference"""
    # Setup
    target = Node(label="target")
    graph.add(target)

    parent_id = graph.find_one(label="parent").uid
    edge = DynamicEdge(
        predecessor_id=parent_id,
        successor_ref="target",
        graph=graph
    )

    # Test resolution
    assert edge.successor == target
    assert edge.successor_id == target.uid


def test_resolve_by_template(graph):
    """Test creating successor from template"""
    template = {
        "label": "new_node",
        "tags": ["test"]
    }

    parent_id = graph.find_one(label="parent").uid
    edge = DynamicEdge(
        predecessor_id=parent_id,
        successor_template=template,
        graph=graph
    )

    # Test resolution
    successor = edge.successor
    assert successor is not None
    assert successor.label == "new_node"
    assert "test" in successor.tags
    assert successor.uid in graph


def test_resolve_by_criteria(graph):
    """Test finding successor by criteria"""
    # Setup
    target = Node(label="target", tags=["special"])
    graph.add(target)

    parent_id = graph.find_one(label="parent").uid
    edge = DynamicEdge(
        predecessor_id=parent_id,
        successor_criteria={"tags": ["special"]},
        graph=graph
    )

    # Test resolution
    assert edge.successor is target


def test_clear_successor(graph):
    """Test clearing resolved successor"""
    # Setup
    target = Node(label="target")
    graph.add(target)

    parent_id = graph.find_one(label="parent").uid
    edge = DynamicEdge(
        predecessor_id=parent_id,
        successor_ref="target",
        graph=graph
    )

    # Initial resolution
    assert edge.successor == target

    # Clear and verify
    edge.clear_successor()
    assert edge.successor_id is None

def test_no_successor(graph):
    """Test clearing resolved successor"""
    # Setup
    parent_id = graph.find_one(label="parent").uid
    edge = DynamicEdge(
        predecessor_id=parent_id,
        successor_ref="target",
        graph=graph
    )

    assert edge.successor is None
