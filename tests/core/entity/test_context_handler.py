import pytest

from tangl.core.entity.handlers import on_gather_context, HasContext
from tangl.core.graph import Node, Graph

@pytest.fixture
def context_entity():
    yield HasContext(locals={'entity': 'hello entity'})


def test_context_entity(context_entity):

    result = on_gather_context.execute(context_entity)
    assert result == {"entity": "hello entity"}

class ContextNode(HasContext, Node):
    ...

@pytest.fixture
def context_node():
    g = Graph()
    n = ContextNode(locals={'node': 'hello node'})
    g.add(n)
    yield n

@pytest.fixture
def context_node_child(context_node):
    c = ContextNode(locals={'child': 'hello child'})
    context_node.add_child(c)
    yield c

def test_context_node(context_node):

    result = on_gather_context.execute(context_node)
    assert result == {"node": "hello node"}

def test_context_node_child(context_node_child):

    result = on_gather_context.execute(context_node_child)
    assert result == {"node": "hello node", "child": "hello child"}

class ContextGraph(HasContext, Graph):
    ...

@pytest.fixture
def context_graph_node():
    g = ContextGraph(locals={'graph': 'hello graph'})
    n = ContextNode(locals={'node': 'hello node'})
    g.add(n)
    yield n

def test_context_graph(context_graph_node):

    result = on_gather_context.execute(context_graph_node)
    assert result == {"node": "hello node", 'graph': 'hello graph'}
