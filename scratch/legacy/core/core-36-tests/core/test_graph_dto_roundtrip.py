from tangl.core36.entity import Node, Edge
from tangl.core36.graph import Graph
from tangl.vm36.execution.patch import resolve_fqn

def test_graph_to_from_dto_preserves_items_and_adjacency():
    g = Graph()
    a = Node(label="A"); b = Node(label="B")
    e = Edge(src_id=a.uid, dst_id=b.uid, kind="contains")
    for it in (a,b,e):
        (g._add_node_silent if isinstance(it, Node) else g._add_edge_silent)(it)

    dto = g.to_dto()
    print(dto)
    g2 = Graph.from_dto(dto, resolve_fqn)
    assert set(x.uid for x in g.nodes()) == set(x.uid for x in g2.nodes())
    assert set(x.uid for x in g.edges()) == set(x.uid for x in g2.edges())
    assert g.out_idx == g2.out_idx and g.in_idx == g2.in_idx