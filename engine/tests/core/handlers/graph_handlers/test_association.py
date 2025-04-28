import pytest

from tangl.core import Graph, Node
from tangl.core.graph_handlers import Associating

MyAssociatingNode = type('MyAssociatingNode', (Associating, Node), {} )

@pytest.fixture
def graph():
    return Graph()

@pytest.fixture
def node1(graph):
    return MyAssociatingNode(graph=graph)

@pytest.fixture
def node2(graph):
    return MyAssociatingNode(graph=graph)

def test_basic_parent_child_association(node1, node2):
    """Test basic parent-child association"""
    assert node1.graph is node2.graph
    assert node1 in node1.graph
    assert node2 in node1.graph

    node1.associate(other=node2, relationship="as_parent")

    assert node2 in node1.children
    assert node1 is node2.parent
    assert node2 in node1.associates, "n2 is an Associating child of n1"
    assert node1 not in node2.associates, "n1 is _not_ a child of n2"

def test_peer_association(node1, node2):
    """Test peer association"""
    node1.associate(other=node2, relationship="as_peer")

    assert node2 in node1.children, "Node 1 should be in node 2 children"
    assert node1 in node2.children
    assert node2 in node1.associates
    assert node1 in node2.associates


def test_prevent_cycles(node1, node2):
    """Test cycle prevention in parent-child relationships"""

    node1.associate(other=node2, relationship="as_parent")

    with pytest.raises(ValueError):
        node2.associate(other=node1, relationship="as_parent")


def test_invalid_relationship(node1, node2):
    """Test invalid relationship type"""

    with pytest.raises(ValueError):
        node1.associate(other=node2, relationship="invalid")


def test_recursive_prevention(node1, node2):
    """Test prevention of recursive associations"""
    node1.associate(other=node2, relationship='as_parent')

    with pytest.raises(ValueError):
        node2.associate(other=node1, relationship='as_parent')


def test_disassociation(node1, node2):
    """Test disassociation"""
    node1.associate(other=node2, relationship="as_peer")
    node1.disassociate(other=node2)

    assert node2 not in node1.children
    assert node1 not in node2.children
    assert node2 not in node1.associates
    assert node1 not in node2.associates


def test_multiple_peer_associations(node1, node2):
    """Test multiple peer associations"""
    node3 = Associating(graph=node1.graph)

    node1.associate(other=node2, relationship="as_peer")
    node1.associate(other=node3, relationship="as_peer")

    assert len(node1.associates) == 2
    assert node2 in node1.associates
    assert node3 in node1.associates


def test_idempotent_association(node1, node2):
    """Test associating multiple times has no effect"""
    node1.associate(other=node2, relationship="as_peer")
    node1.associate(other=node2, relationship="as_peer")

    assert len(node1.associates) == 1
