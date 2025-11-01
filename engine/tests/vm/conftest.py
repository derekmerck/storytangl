import pytest
from pydantic import create_model, Field

from tangl.type_hints import StringMap
from tangl.core.graph import Graph, Node, Subgraph
from tangl.core.record import StreamRegistry
from tangl.vm import Ledger
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

@pytest.fixture
def ledger(graph):
    abc = next( graph.find_nodes(label="abc") )
    return Ledger(graph=graph, cursor_id=abc.uid, records=StreamRegistry())

@pytest.fixture
def trivial_ctx():
    class Ctx:
        def get_active_layers(self):
            from tangl.vm.dispatch import vm_dispatch
            return vm_dispatch,
    return Ctx()
