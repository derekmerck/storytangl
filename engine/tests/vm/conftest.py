import pytest

from tangl.core.graph import Graph, Node
from tangl.vm.context import Context
from tangl.vm.frame import Frame

@pytest.fixture
def graph():
    g = Graph()
    g.add_node(label="abc")
    return g

@pytest.fixture
def context(graph):
    abc = next( graph.find_nodes(label="abc") )
    return Context(graph=graph, cursor_id=abc.uid)

@pytest.fixture
def frame(graph):
    abc = next( graph.find_nodes(label="abc") )
    return Frame(graph=graph, cursor_id=abc.uid)
