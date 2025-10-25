from __future__ import annotations
import dataclasses
import pytest
from uuid import UUID

from tangl.core.graph import Graph, GraphItem, Node, Edge, Subgraph



# --- Graph relinkage test: graph subclass re-attaches items in add() -------------

def test_graph_unstructure_structure_relinks_items():
    g = Graph(label="G")
    n1 = GraphItem(label="n1")
    n2 = GraphItem(label="n2")
    g.add(n1)
    g.add(n2)

    # Sanity: items are linked to the graph before serialization
    assert n1.graph is g and n2.graph is g

    blob = g.unstructure()

    # Ensure graph backlink is not serialized
    for item_blob in blob["_data"]:
        assert "graph" not in item_blob  # excluded by metadata{"serialize": False}

    # Rebuild a fresh Graph
    g2 = Graph.structure(dict(blob))

    # Items should have been added via Graph.add(), which re-attaches .graph
    rebuilt_items = list(g2.values())
    assert len(rebuilt_items) == 2
    for item in rebuilt_items:
        assert isinstance(item, GraphItem)
        assert item.graph is g2  # relinked to the new graph


# --- Sanity helpers ---------------------------------------------------------------

def _uuids_unique(items):
    seen = set()
    for it in items:
        assert isinstance(it.uid, UUID)
        assert it.uid not in seen
        seen.add(it.uid)


# --- Basic add/find/get for nodes/edges/subgraphs ---------------------------------

def test_graph_add_and_find_nodes_edges_subgraphs():
    g = Graph(label="G")

    # Nodes
    n1 = g.add_node(label="n1")
    n2 = g.add_node(label="n2")
    _uuids_unique([n1, n2])

    # Edges (n1 -> n2)
    e = g.add_edge(n1, n2, edge_type=None, label="e1")
    assert isinstance(e, Edge)
    assert e.source_id == n1.uid
    assert e.destination_id == n2.uid

    # Subgraph with members
    sg = g.add_subgraph(label="sg1", members=[n1, n2])
    assert isinstance(sg, Subgraph)
    assert sg.has_member(n1) and sg.has_member(n2)
    assert list(sg.members) == [n1, n2]  # ordering preserved by append

    # find_* helpers default to class filters
    assert {x.label for x in g.find_nodes()} == {"n1", "n2"}
    assert {x.label for x in g.find_subgraphs()} == {"sg1"}
    assert {x.label for x in g.find_edges()} == {"e1"}

    # Directional edge queries
    out_from_n1 = list(g.find_edges(source=n1))
    into_n2 = list(g.find_edges(destination=n2))
    assert out_from_n1 == [e]
    assert into_n2 == [e]

    # Graph.get by UUID and by label
    assert g.get(n1.uid) is n1
    assert g.get("n2") is n2
    assert g.get(UUID(int=0)) is None


def test_edge_source_destination_properties_and_type_safety():
    g = Graph(label="G")
    a = g.add_node(label="a")
    b = g.add_node(label="b")

    e = g.add_edge(a, b, label="ab")
    # Property accessors resolve through the graph
    assert e.source is a
    assert e.destination is b

    # Reassign via properties updates *_id fields
    c = g.add_node(label="c")
    e.destination = c
    assert e.destination_id == c.uid and e.destination is c

    # Type safety
    with pytest.raises(TypeError):
        e.source = "not-a-node"  # type: ignore[assignment]

    # Clear
    e.source = None
    assert e.source_id is None and e.source is None


def test_node_parent_and_edge_helpers_without_ancestors_chain():
    """Covers Node.parent, edges_in/out, and edges() without exercising Node.ancestors()."""
    g = Graph(label="G")
    n1 = g.add_node(label="n1")
    n2 = g.add_node(label="n2")
    sg = g.add_subgraph(label="S", members=[n1])

    # parent present for n1, absent for n2
    assert n1.parent is sg
    assert n2.parent is None

    # edge helpers
    e = g.add_edge(n1, n2, label="e")
    assert list(n1.edges_out()) == [e]
    assert list(n2.edges_in()) == [e]
    assert n1.edges() == [e]
    assert n2.edges() == [e]


# --- Subgraph membership API ------------------------------------------------------

def test_subgraph_membership_add_remove_and_find():
    g = Graph(label="G")
    a = g.add_node(label="a")
    b = g.add_node(label="b")
    c = g.add_node(label="c")

    sg = g.add_subgraph(label="S", members=[a])
    # add/remove enforce Node type
    sg.add_member(b)
    assert sg.has_member(a) and sg.has_member(b) and not sg.has_member(c)

    # remove member
    sg.remove_member(a)
    assert not sg.has_member(a) and sg.has_member(b)

    # find / find_one delegate to Node.matches()
    got = list(sg.find_all(label="b"))
    assert got == [b]
    assert sg.find_one(label="b") is b
    assert sg.find_one(label="z") is None

    # type safety
    with pytest.raises(TypeError):
        sg.add_member("not-a-node")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sg.remove_member("not-a-node")  # type: ignore[arg-type]


# --- Round-trip: unstructure/structure for Graph preserves links ------------------

def test_graph_unstructure_structure_roundtrip_preserves_links_and_members():
    g = Graph(label="G")
    n1 = g.add_node(label="n1")
    n2 = g.add_node(label="n2")
    e = g.add_edge(n1, n2, label="e1")
    sg = g.add_subgraph(label="S", members=[n1, n2])

    # Pre-conditions
    assert e.source is n1 and e.destination is n2
    assert list(sg.members) == [n1, n2]

    blob = g.unstructure()

    # Ensure backlink to graph is not serialized for items
    for item_blob in blob["_data"]:
        assert "graph" not in item_blob
        if item_blob['obj_cls'] == Subgraph:
            print( item_blob )

    # Rebuild
    g2 = Graph.structure(dict(blob))

    # Items are re-added via Graph.add(), so .graph re-links
    nodes2 = {x.label: x for x in g2.find_nodes()}
    edges2 = {x.label: x for x in g2.find_edges()}
    sg2 = next(g2.find_subgraphs())

    assert set(nodes2.keys()) == {"n1", "n2"}
    assert set(edges2.keys()) == {"e1"}

    e2 = edges2["e1"]
    assert isinstance(e2, Edge)
    # Endpoints resolve correctly in the new graph
    assert e2.source.label == "n1"
    assert e2.destination.label == "n2"

    # Subgraph members preserved
    print( sg.short_uid(), sg.member_ids )
    print( sg.short_uid(), sg2.member_ids )
    assert [m.label for m in sg2.members] == ["n1", "n2"]


def test_node_ancestors_root_and_path():
    g = Graph(label="G")
    n = g.add_node(label="n")
    sg = g.add_subgraph(label="A", members=[n])
    assert n.parent is sg
    assert list(n.ancestors()) == [sg]
    assert n.root is sg
    assert n.path == "A.n"
