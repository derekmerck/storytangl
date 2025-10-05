import pytest

from pydantic import Field

from tangl.core import Graph, Singleton
from tangl.core.graph import SingletonNode


class TestSingleton(Singleton):
    a: int = 100
    b: int = Field(200, json_schema_extra={'instance_var': True})

@pytest.fixture(autouse=True)
def reset_test_singleton():
    TestSingleton.clear_instances()
    TestSingleton(label="unique_singleton")
    yield
    TestSingleton.clear_instances()

@pytest.fixture
def ws():
    return SingletonNode[TestSingleton](label="unique_singleton", graph=Graph())

def test_wrapped_singleton_creation(ws):

    assert isinstance(ws, SingletonNode)
    assert ws.label == "unique_singleton"
    assert ws.reference_singleton.label == "unique_singleton"

def test_wrapped_singleton_invalid_ref():
    with pytest.raises(ValueError):
        SingletonNode[TestSingleton](label="invalid_singleton")

def test_reference_singleton_missing(ws):
    TestSingleton._instances.clear()  # Simulate instance deletion

    with pytest.raises(ValueError, match="No instance of `TestSingleton` found"):
        _ = ws.reference_singleton  # Should raise ValueError

def test_wrapped_singleton_getattr(ws):

    assert ws.a == 100
    assert ws.b == 200

    with pytest.raises(ValueError):
        # can't set an instance variable
        ws.a = 150

    # can set an instance variable
    ws.b = 250

def test_wrapped_singleton_graph_integration(ws):

    g = Graph()
    g.add(ws)
    assert g.get(ws.uid) is ws
    assert g.find_one(label="unique_singleton") is ws

    # n = Node(label="node")
    # ws.add_child(n)
    # assert n.path == "unique_singleton/node"
