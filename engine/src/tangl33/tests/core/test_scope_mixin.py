from tangl33.core import Node, Graph, Service

def test_scope_layers_are_independent():
    n = Node()
    g = Graph()

    n.handler_layer(Service.PROVIDER).append("cap1")
    g.handler_layer(Service.PROVIDER).append("cap2")

    assert "cap1" in n.handler_layer(Service.PROVIDER)
    assert "cap1" not in g.handler_layer(Service.PROVIDER)
