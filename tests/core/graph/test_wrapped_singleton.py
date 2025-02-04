import pytest

from pydantic import Field

from tangl.core.entity import Singleton
from tangl.core.graph import Node, Graph, WrappedSingleton


class TestSingleton(Singleton):
    a: int = 100
    b: int = Field(200, json_schema_extra={'instance_var': True})


@pytest.fixture(autouse=True)
def reset_test_singleton():
    TestSingleton._instances.clear()
    TestSingleton(label="unique_singleton")
    yield
    TestSingleton._instances.clear()

@pytest.fixture
def ws():
    return WrappedSingleton[TestSingleton](label="unique_singleton")


class TestWrappedSingleton:

    def test_wrapped_singleton_creation(self, ws):

        assert isinstance(ws, WrappedSingleton)
        assert ws.label == "unique_singleton"
        assert ws.reference_singleton.label == "unique_singleton"

    def test_wrapped_singleton_invalid_ref(self):
        with pytest.raises(ValueError):
            WrappedSingleton[TestSingleton](label="invalid_singleton")

    def test_reference_singleton_missing(self, ws):
        TestSingleton._instances.clear()  # Simulate instance deletion

        with pytest.raises(ValueError, match="No instance of `TestSingleton` found"):
            _ = ws.reference_singleton  # Should raise ValueError

    def test_wrapped_singleton_getattr(self, ws):

        assert ws.a == 100
        assert ws.b == 200

        with pytest.raises(ValueError):
            # can't set an instance variable
            ws.a = 150

        # can set an instance variable
        ws.b = 250

    def test_wrapped_singleton_graph_integration(self, ws):

        g = Graph()
        g.add(ws)
        assert g[ws.uid] == ws
        assert g["unique_singleton"] == ws

        n = Node(label="node")
        ws.add_child(n)

        assert n.path == "unique_singleton/node"
