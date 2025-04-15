import pytest

from tangl.core.handlers import on_gather_context, HasContext
from tangl.core.graph import Graph, Node

MyContextNode = type('MyContextNode', (HasContext, Node), {} )
MyContextGraph = type('MyContextGraph', (HasContext, Graph), {} )

@pytest.fixture
def context_node():
    g = MyContextGraph(locals={'graph': 'hello graph'})
    n = MyContextNode(locals={'node': 'hello node'})
    g.add(n)
    yield n

@pytest.fixture
def context_node_child(context_node):
    c = MyContextNode(locals={'child': 'hello child'})
    context_node.add_child(c)
    yield c

def test_context_graph(context_node):

    result = on_gather_context.execute(context_node.graph)
    assert result == {'graph': 'hello graph'}

def test_context_node(context_node):

    result = on_gather_context.execute(context_node)
    assert result == {"node": "hello node", 'graph': 'hello graph'}

def test_context_node_child(context_node_child):

    result = on_gather_context.execute(context_node_child)
    assert result == {"node": "hello node", "child": "hello child", 'graph': 'hello graph'}

