import pytest
from pydantic._internal._model_construction import ModelMetaclass

from tangl.core.entity.handlers import SelfFactoring, SelfFactoringHandler, SelfFactoringModel
from tangl.core.graph import Node

_SelfFactorying = type('_SelfFactoring', (SelfFactoring, ModelMetaclass), {})

class SFNode(Node, metaclass=SelfFactoringModel):
    foo: str = "abc"

class SFNodeAlt(Node, metaclass=SelfFactoringModel):
    bar: int = -1

class SFDualNode(SFNode, SFNodeAlt):
    ...

class SFPropertyNode(SFNode):

    @property
    def node_list(self) -> list[Node]:
        ...

def test_self_factorying_node():

    node = SFNode()
    assert isinstance(node, SFNode)
    assert node.foo == "abc"

    node = SFNode(obj_cls="SFNodeAlt")
    assert isinstance(node, SFNodeAlt)
    assert node.bar == -1

    node = SFNode(obj_cls="SFDualNode")
    assert isinstance(node, SFDualNode)
    assert node.foo == "abc"
    assert node.bar == -1

def test_node_with_property_kwargs():

    with pytest.raises(TypeError):
        # SFNode doesn't take a node-list
        node = SelfFactoringHandler.create_node(obj_cls=SFNode, node_list=[{'label': 'abc'}])

    node = SelfFactoringHandler.create_node(obj_cls=SFPropertyNode, node_list=[{'label': 'abc'}])

    assert len(node.children) == 1
    assert isinstance(node.children[0], Node)

    node = SelfFactoringHandler.create_node(obj_cls="SFPropertyNode", node_list=[{'label': 'abc'}])

    assert len(node.children) == 1
    assert isinstance(node.children[0], Node)

    node = SelfFactoringHandler.create_node(obj_cls=SFPropertyNode, node_list=[{'obj_cls': SFNodeAlt, 'label': 'abc'}])

    assert isinstance(node.children[0], SFNodeAlt)

    node = SelfFactoringHandler.create_node(obj_cls="SFPropertyNode", node_list=[{'obj_cls': "SFNodeAlt", 'label': 'abc'}])

    assert isinstance(node.children[0], SFNodeAlt)
