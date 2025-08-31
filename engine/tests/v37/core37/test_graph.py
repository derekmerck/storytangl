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
