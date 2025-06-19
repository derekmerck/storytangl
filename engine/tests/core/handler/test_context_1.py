import pytest

from tangl.core.entity import Node, Graph
from tangl.core.handler import HasContext, on_gather_context


class MyNode(HasContext, Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.locals = {"foo": "bar"}


def test_gather_locals():
    node = MyNode()
    # print(list(MyNode._handler_registry))
    assert node.locals == {"foo": "bar"}
    ctx = HasContext.gather_context(node)
    print(ctx)
    assert ctx["foo"] == "bar"


@pytest.mark.xfail(reason="graph needs to be implemented as a scope now")
def test_gather_context_aggregation():
    class RoleNode(MyNode):
        @on_gather_context.register(priority=20)
        def role_handler(self, **_):
            return {"shopkeeper": "npc123"}

    class MyGraph(Graph, HasContext):
        @on_gather_context.register(priority=50)
        def directory_handler(self, **_):
            return {"nodes": {"test": "node123"}}

    node = RoleNode(label="testnode")
    graph = MyGraph()
    ctx = HasContext.gather_context(node)
    assert ctx["foo"] == "bar"
    assert ctx["shopkeeper"] == "npc123"
    assert ctx["nodes"]["test"] == "node123"
