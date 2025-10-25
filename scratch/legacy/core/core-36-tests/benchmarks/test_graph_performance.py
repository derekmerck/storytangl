import pytest
from tangl.core36.graph import Graph, Node


@pytest.mark.skip(reason="boring")
@pytest.mark.benchmark
def test_graph_operations(benchmark):
    def create_large_graph():
        g = Graph()
        for i in range(1000):
            g._add_node_silent(Node(label=f"node_{i}"))
        return g

    result = benchmark(create_large_graph)
    assert len(result) == 1000
