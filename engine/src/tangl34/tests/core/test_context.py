import pytest

from tangl34.core.structure import Node, Graph
from tangl34.core.handlers import HasContext


class MyNode(HasContext, Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.locals = {"foo": "bar"}


def test_gather_locals():
    node = MyNode()
    print(list(MyNode._handler_registry))
    assert node.locals == {"foo": "bar"}
    ctx = HasContext.gather_context(node)
    print(ctx)
    assert ctx["foo"] == "bar"


def test_gather_context_aggregation():
    class RoleNode(MyNode):
        @HasContext.context_handler(priority=20)
        def role_handler(self, _):
            return {"shopkeeper": "npc123"}

    class MyGraph(Graph, HasContext):
        @HasContext.context_handler(priority=50)
        def directory_handler(self, _):
            return {"nodes": {"test": "node123"}}

    node = RoleNode(label="testnode")
    graph = MyGraph()
    ctx = HasContext.gather_context(node, graph)
    assert ctx["foo"] == "bar"
    assert ctx["shopkeeper"] == "npc123"
    assert ctx["nodes"]["test"] == "node123"
