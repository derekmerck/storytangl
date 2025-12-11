# No longer supported

import pytest

import attr

from tangl.core import Node, Graph
from tangl.core.mixins import Runtime, Renderable, Owner, Ownable, Traversable, Edge
from tangl.core.utils.cattrs_converter import NodeConverter

# pytestmark = pytest.mark.skip(reason="Skip all tests in this file")

def test_node_creation_and_unstructuring():
    n = Node()
    cc = NodeConverter()
    n_ = cc.unstructure(n)
    nn = cc.structure(n_, Node)
    assert n == nn
    assert n is not nn
    assert isinstance(nn, Node)

def test_node_registry():
    r = Graph()
    n = Node()
    r.add_node(n)
    m = Node(parent=n)
    assert m.graph is r
    assert m in r.values()
    assert n in r.values()

def test_node_relink():
    r = Graph()
    n = Node()
    r.add_node(n)
    m = Node(parent=n)
    cc = NodeConverter()
    m_ = cc.unstructure(m)
    mm = cc.structure(m_, Node)
    cc.relink_node(mm, r)  # Requires manual relink
    assert m == mm
    assert m is not mm
    assert isinstance(mm, Node)

def test_registry_unstructure_relink():
    r = Graph()
    n = Node()
    r.add_node(n)
    cc = NodeConverter()
    r_ = cc.unstructure(r)
    rr = cc.structure(r_, Graph)
    assert r == rr
    assert r is not rr
    assert n in rr.values()

def test_yaml_preconf_converter_class():
    n = Node()
    cc = NodeConverter.get_preconf('yaml')
    n_ = cc.unstructure(n)
    print( n_ )
    nn = cc.structure(n_, Node)
    assert n == nn
    assert n is not nn
    assert isinstance(nn, Node)
    # todo: need yaml-specific test

def test_bson_preconf_converter_class():
    n = Node()
    cc = NodeConverter.get_preconf('bson')
    n_ = cc.unstructure(n)
    print( n_ )
    nn = cc.structure(n_, Node)
    assert n == nn
    assert n is not nn
    assert isinstance(nn, Node)
    # todo: need bson-specific test

RuntimeNode = attr.make_class("RuntimeNode", (), (Runtime, Node))

def test_runtime_node_serialization():
    n = RuntimeNode(conditions=["foo > 5"], effects=["foo = 10"], locals={"foo": 0})
    cc = NodeConverter()
    n_ = cc.unstructure(n)
    nn = cc.structure(n_, RuntimeNode)
    assert n.conditions == nn.conditions
    assert n.effects == nn.effects
    assert n.locals == nn.locals

RenderableNode = attr.make_class("RenderableNode", (), (Renderable, Node))

def test_renderable_node_serialization():
    content_template = "Hello, {{ name }}!"
    n = RenderableNode(text=content_template, locals={"name": "World", "foo": 3})
    cc = NodeConverter()
    n_ = cc.unstructure(n)
    nn = cc.structure(n_, RenderableNode)
    assert n.text == nn.text
    assert n.locals == nn.locals
    assert n.render().text == "Hello, World!"

TravNode = attr.make_class("TravNode", (), (Traversable, Node))
EdgeNode = attr.make_class("EdgeNode", (), (Edge, Node))

def test_traversable_node_serialization():
    n = TravNode(conditions=["foo > 5"], effects=["foo = 10"], text="Test Traversable Node", locals={"foo": 0})
    cc = NodeConverter()
    n_ = cc.unstructure(n)
    nn = cc.structure(n_, TravNode)
    assert n.conditions == nn.conditions
    assert n.effects == nn.effects
    assert n.text == nn.text
    assert n.locals == nn.locals
    assert n.visited == nn.visited


def test_weakref_serialization():
    from tangl.core.utils.has_weakrefs import HasWeakRefs, WeakRef

    @attr.define
    class WRNode(Node, metaclass=HasWeakRefs):
        _my_attrib: WeakRef[Node] = attr.ib(default=None, converter=WeakRef)

    g = Graph()
    n = Node(graph=g)
    w = WRNode(graph=g, my_attrib=n)
    print( w.my_attrib )

    cc = NodeConverter()
    w_ = cc.unstructure(w)
    print( w_ )
    assert not isinstance( w_['my_attrib'], WeakRef )


# @pytest.mark.skip(reason="weakrefs")
def test_weakref_edge_serialization():
    g = Graph()
    t = TravNode(graph=g)
    e = EdgeNode(graph=g, target_node=t)

    cc = NodeConverter()

    e_ = cc.unstructure(e)
    print( e_ )
    ee = cc.structure(e_, EdgeNode)
    # this won't work wo the reference graph
    ee._graph = g

    print( e._target_node.value )
    print( e.target_node )
    print( ee._target_node.value )
    print( ee.target_node )

    assert ee == e

    n = TravNode(graph=g)
    n.add_child(e)

    n_ = cc.unstructure(n)
    nn = cc.structure(n_, TravNode)
    assert n.conditions == nn.conditions
    assert n.effects == nn.effects
    assert n.text == nn.text
    assert n.locals == nn.locals
    assert n.visited == nn.visited

OwnerNode = attr.make_class("OwnerNode", (), (Owner, Node))
OwnableNode = attr.make_class("OwnableNode", (), (Ownable, Node))

def test_ownable_node_serialization():
    r = Graph()
    owner_a = OwnerNode(label="owner_a", graph=r)
    item_a = OwnableNode(label="item_a")
    item_a.associate(owner_a)
    assert item_a in owner_a.owned

    cc = NodeConverter()
    owner_a_ = cc.unstructure(owner_a)
    owner_a_restructured = cc.structure(owner_a_, OwnerNode)
    cc.relink_node( owner_a_restructured, r )
    assert item_a in owner_a_restructured.owned


from tangl.utils.singletons import Singletons
SingletonNode = attr.make_class("SingletonNode", (), (Singletons, Node))

def test_singleton_serialization():
    # this should just convert to the class and the label
    foo = SingletonNode(label="foo")
    print( foo )

    cc = NodeConverter()
    foo_flat = cc.unstructure(foo)

    print( foo_flat )

    cc.structure(foo_flat, SingletonNode)


from typing import ClassVar
import uuid

import attr
import cattrs

from tangl.6.core import Node

def test_from_dict():

    @attr.s
    class Trivial:
        guid: uuid.UUID = attr.ib( factory=uuid.uuid4, converter=uuid.UUID )

    test_dict = {
        'guid': '12345678-1234-5678-1234-567812345678',
    }

    test_inst_newd = Trivial(**test_dict)
    converter = cattrs.Converter()
    test_inst_structured = converter.structure(test_dict, Trivial)

    assert test_inst_newd == test_inst_structured

    # Use from_dict to create an instance of Node
    test_node = Node.from_dict(test_dict)

    # Check the type and attributes of the created instance
    assert isinstance(test_node, Node)
    assert test_node.guid == uuid.UUID('12345678-1234-5678-1234-567812345678')

from tangl.6.core.subtyped import Subtyped

@attr.s(auto_attribs=True)
class MockNode(Subtyped, Node):
    node_cls: ClassVar = "mock"

    name: str = ""
    test_attr: str = "test"

def test_subtype_registration():

    # MockNode is automatically added to the _class_map of Subtyped
    assert Subtyped._class_map['mock'] is MockNode

def test_subtype_from_dict():
    # Create a dictionary representing a MockNode
    mock_node_dict = {
        'guid': '12345678-1234-5678-1234-567812345678',
        'name': 'MockNode',
        'children': [],
        'node_cls': 'mock',
        'test_attr': 'test'
    }

    # Use from_dict to create an instance of MockNode
    mock_node = Subtyped.from_dict(mock_node_dict)

    # Check the type and attributes of the created instance
    assert isinstance(mock_node, MockNode)
    assert mock_node.guid == uuid.UUID('12345678-1234-5678-1234-567812345678')
    assert mock_node.name == 'MockNode'
    assert mock_node.children == []
    assert mock_node.test_attr == 'test'


