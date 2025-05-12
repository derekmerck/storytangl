from tangl33.core import Node, Graph, CoreService

def test_scope_layers_are_independent():
    n = Node()
    g = Graph()

    n.handler_layer(CoreService.PROVIDER).append("cap1")
    g.handler_layer(CoreService.PROVIDER).append("cap2")

    assert "cap1" in n.handler_layer(CoreService.PROVIDER)
    assert "cap1" not in g.handler_layer(CoreService.PROVIDER)
