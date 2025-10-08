from uuid import UUID
import pickle

import pytest

from tangl.core.graph import Graph, Node, Subgraph


def test_node_creation():
    n = Node(label="root", graph=Graph())
    assert isinstance(n.uid, UUID)  # Ensure it's a UUID
    assert n.label == "root"
    assert n.parent is None

def test_add_child():
    g = Graph()
    parent = Subgraph(label="parent", graph=g)
    child = Node(label="child", graph=g)

    # g.add(parent)
    parent.add_member(child)

    assert child in parent.members
    assert child.parent == parent

    assert next(parent.members) is child

    with pytest.raises(AttributeError):
        parent.does_not_exist

def test_node_contains():
    g = Graph()
    parent = Subgraph(label="root", tags={"dog"}, graph=g)
    child = Node(label="child", graph=g)
    parent.add_member(child)
    not_child = Node(label="not_child", tags={'cat'}, graph=g)

    print( parent.members )
    assert child in parent.members
    assert not_child not in parent.members

    # assert child in parent
    # assert not_child not in node

    # assert child.uid in node
    from tangl.utils.is_valid_uuid import is_valid_uuid
    assert is_valid_uuid(str(child.uid))
    # assert str(child.uid) in node
    # assert not_child.uid not in node
    assert is_valid_uuid(str(not_child.uid))
    # assert str(not_child.uid) not in node

    # assert "child" in node
    # assert "not_child" not in node

    # assert "dog" in node
    # assert "cat" not in node


def test_remove_child():
    g = Graph()
    parent = Subgraph(label="parent", graph=g)
    child = Node(label="child", graph=g)

    parent.add_member(child)
    assert child in parent.members
    parent.remove_member(child)

    assert child not in parent.members
    assert child.parent is None


def test_node_pickles():

    a = Node(label="test_node")

    s = pickle.dumps( a )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert a == res


def test_node_edges_report_connections():
    graph = Graph()
    alpha = Node(label="alpha", graph=graph)
    beta = Node(label="beta", graph=graph)

    forward = alpha.add_edge_to(beta)
    reverse = alpha.add_edge_from(beta)

    assert {edge.uid for edge in alpha.edges_out()} == {forward.uid}
    assert {edge.uid for edge in alpha.edges_in()} == {reverse.uid}
    assert {edge.uid for edge in alpha.edges()} == {forward.uid, reverse.uid}

    assert {edge.uid for edge in beta.edges_in()} == {forward.uid}
    assert {edge.uid for edge in beta.edges_out()} == {reverse.uid}
    assert {edge.uid for edge in beta.edges()} == {forward.uid, reverse.uid}


def test_node_remove_edge_helpers_are_idempotent():
    graph = Graph()
    alpha = Node(label="alpha", graph=graph)
    beta = Node(label="beta", graph=graph)

    forward = alpha.add_edge_to(beta)
    reverse = alpha.add_edge_from(beta)

    alpha.remove_edge_to(beta)

    assert list(alpha.edges_out()) == []
    assert forward.uid not in {edge.uid for edge in beta.edges_in()}
    assert {edge.uid for edge in beta.edges_in()} == set()
    assert reverse.uid in {edge.uid for edge in alpha.edges_in()}
    assert reverse.uid in {edge.uid for edge in beta.edges_out()}

    alpha.remove_edge_to(beta)
    assert list(alpha.edges_out()) == []

    alpha.remove_edge_from(beta)
    assert list(alpha.edges_in()) == []
    assert list(beta.edges_out()) == []

    alpha.remove_edge_from(beta)
    assert list(alpha.edges_in()) == []
