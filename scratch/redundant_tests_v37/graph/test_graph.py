import pytest

from tangl.core.graph import Graph

# ---------- Graph topology ----------

def test_graph_add_and_link_and_path_root():
    g = Graph()
    a = g.add_node(label="A")
    b = g.add_node(label="B")
    e = g.add_edge(a, b)  # no type semantics tested here

    sg = g.add_subgraph(label="Top")
    sg.add_member(a)
    sg2 = g.add_subgraph(label="Mid")
    sg2.add_member(b)
    sg.add_member(sg2)  # nesting subgraph; parent chain: b -> sg2 -> sg

    # parent/ancestors
    assert b.parent == sg2
    assert list(b.ancestors()) == [sg2, sg]  # nearest -> farthest

    # root must be the farthest
    assert b.root == sg

    # path should print root..self
    assert b.path == "Top.Mid.B"

def test_subgraph_remove_member_by_uuid_no_attr_error():
    g = Graph()
    n = g.add_node(label="X")
    sg = g.add_subgraph(label="G", members=[n])

    # remove by UUID should not try to touch GraphItem methods
    sg.remove_member(n.uid)
    assert n.uid not in sg.member_ids


def test_graph_add_find_and_path():
    g = Graph()
    n1 = g.add_node(label="root")
    n2 = g.add_node(label="scene")
    e  = g.add_edge(n1, n2)
    sg = g.add_subgraph(label="book", members=[n1, n2])

    assert n2.parent == sg
    assert list(n2.ancestors()) == [sg]
    assert n2.path.endswith(".scene") or n2.path == "book.scene"

    # get by label and by uid
    assert g.get("root") == n1
    assert g.get(n2.uid) == n2

    # edges API
    assert list(n1.edges_out()) == [e]
    assert list(n2.edges_in()) == [e]


def test_graph_duplicate_labels_resolve_first_match_and_uid_lookup_unambiguous():
    g = Graph()
    a = g.add_node(label="X")
    b = g.add_node(label="X")
    assert g.get("X") in (a, b)
    assert g.get(a.uid) is a and g.get(b.uid) is b

def test_subgraph_reparent_member_updates_parent_chain():
    g = Graph()
    a = g.add_node(label="A")
    s1 = g.add_subgraph(label="S1", members=[a])
    assert a in s1.members

    import logging
    logging.debug(f"has a: {list(g.find_subgraphs(has_member=a))}" )

    assert a.parent is s1

    s2 = g.add_subgraph(label="S2")
    s2.add_member(a)
    assert a.parent is s2
    assert list(a.ancestors())[0] == s2
    assert s1 is not a.parent

# structuring and eq

def test_unstructure_and_eq_on_data_attr():

    from tangl.core import Entity

    g = Graph()
    a = g.add_node(label="A")
    b = g.add_node(label="B")
    e = g.add_edge(a, b)  # no type semantics tested here

    ud = g.model_dump()
    assert 'data' not in ud
    assert '_data' in ud

    ud3 = Entity.unstructure(g)
    assert 'data' not in ud3
    assert '_data' in ud3

    ud2 = g.unstructure()
    assert 'data' not in ud2
    assert '_data' in ud2

    # structure w Entity
    gg = Entity.structure(ud2)
    assert g == gg

    # Changing data results in neq
    gg.add_node(label="C")
    assert g != gg

    ud4 = g.unstructure()
    # structuring didn't mutate the unstructured data
    assert ud2 == ud4

    # structure directly w Graph
    ggg = Graph.structure(ud4)
    assert g == ggg
