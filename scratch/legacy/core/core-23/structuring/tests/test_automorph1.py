# No longer supported

from __future__ import annotations

from pprint import pprint
from typing import Mapping
from collections import ChainMap

import attr
import pytest

from tangl.core import Node, Templated, Automorphic, NodeIndex, SelfStructuring

# import pytest


def test_automorphism():

    class MorphNode1( Automorphic ):
        a: int = 0

    class MorphNode2( Automorphic ):
        b: int = 0

    print(Automorphic._subclass_map)
    assert MorphNode2 is Automorphic._subclass_map['MorphNode2']

    n = MorphNode1()
    assert isinstance(n, MorphNode1)
    assert not isinstance(n, MorphNode2)
    assert hasattr(n, 'a')
    assert not hasattr(n, 'b')
    print(n)

    n = MorphNode2()
    assert not isinstance(n, MorphNode1)
    assert isinstance(n, MorphNode2)
    assert not hasattr(n, 'a')
    assert hasattr(n, 'b')
    print(n)

    n = MorphNode1(node_cls=MorphNode2)
    assert not isinstance(n, MorphNode1)
    assert isinstance(n, MorphNode2)
    assert not hasattr(n, 'a')
    assert hasattr(n, 'b')
    print(n)

    n = MorphNode1(node_cls='MorphNode2')
    assert not isinstance(n, MorphNode1)
    assert isinstance(n, MorphNode2)
    assert not hasattr(n, 'a')
    assert hasattr(n, 'b')
    print(n)

    n = MorphNode2(node_cls=MorphNode1)
    assert isinstance(n, MorphNode1)
    assert not isinstance(n, MorphNode2)
    assert hasattr(n, 'a')
    assert not hasattr(n, 'b')
    print( n )

    n = MorphNode2(node_cls='MorphNode1')
    assert isinstance(n, MorphNode1)
    assert not isinstance(n, MorphNode2)
    assert hasattr(n, 'a')
    assert not hasattr(n, 'b')
    print(n)


def test_node_automorphism():

    @attr.define(init=False)
    class MorphNode1( Automorphic, Node ):
        a: int = 0

    @attr.define(init=False)
    class MorphNode2( Automorphic, Node ):
        b: int = 0

    print(Automorphic._subclass_map)
    assert MorphNode1 is Automorphic._subclass_map['MorphNode1']
    assert MorphNode2 is Automorphic._subclass_map['MorphNode2']

    n = MorphNode1()
    assert isinstance(n, MorphNode1)
    assert not isinstance(n, MorphNode2)
    assert hasattr(n, 'a')
    assert not hasattr(n, 'b')
    print(n)

    n = MorphNode2()
    assert not isinstance(n, MorphNode1)
    assert isinstance(n, MorphNode2)
    assert not hasattr(n, 'a')
    assert hasattr(n, 'b')
    print(n)

    n = MorphNode1(node_cls=MorphNode2)
    assert not isinstance(n, MorphNode1)
    assert isinstance(n, MorphNode2)
    assert not hasattr(n, 'a')
    assert hasattr(n, 'b')
    print(n)

    n = MorphNode1(node_cls='MorphNode2')
    assert not isinstance(n, MorphNode1)
    assert isinstance(n, MorphNode2)
    assert not hasattr(n, 'a')
    assert hasattr(n, 'b')
    print(n)

    n = MorphNode2(node_cls=MorphNode1)
    assert isinstance(n, MorphNode1)
    assert not isinstance(n, MorphNode2)
    assert hasattr(n, 'a')
    assert not hasattr(n, 'b')
    print( n )

    n = MorphNode2(node_cls='MorphNode1')
    assert isinstance(n, MorphNode1)
    assert not isinstance(n, MorphNode2)
    assert hasattr(n, 'a')
    assert not hasattr(n, 'b')
    print(n)

def test_templates():

    @attr.define(init=False)
    class AutoNode(Templated, Node):
        value: int = 0

    n = AutoNode()
    assert n.value == 0

    m = AutoNode(
        template_maps = {'abc': {'value': 100}},
        templates = ['abc']
    )
    assert m.value == 100

    m = AutoNode(
        template_maps = {'abc': {'value': 100}},
        templates = ['abc'],
        value = 200
    )
    assert m.value == 200

    @attr.define(init=False)
    class AutoNode2(AutoNode):

        my_template_maps = {'def': {'value': 300}}

        def _get_template_kwargs(self, templates: list, template_maps: dict = None) -> Mapping:
            template_maps = template_maps or {}
            template_maps |= self.my_template_maps
            return super()._get_template_kwargs(templates, template_maps)

    o = AutoNode2(
        templates = ['def'],
    )
    assert o.value == 300

    p = AutoNode2(
        template_maps = {'abc': {'value': 100}},
        templates = ['abc', 'def'],
    )
    assert p.value == 100

    q = AutoNode2(
        template_maps = {'abc': {'value': 100}},
        templates = ['abc', 'def'],
        value = 200
    )
    assert q.value == 200

def test_structuring():

    @attr.define(init=False)
    class NodeWithChildren(SelfStructuring, Node):
        value: int = 0
        children: list[NodeWithChildren] = attr.ib( factory=list, metadata={"f_uid": "my_child_{0}"})

    attr.resolve_types(NodeWithChildren, localns=locals())

    n = NodeWithChildren(
        children = [ {'value': 1}, {'value': 2}]
    )
    print( n )
    assert isinstance( n.children[0], Node )
    assert n.children[0].uid == "my_child_0"

    print( n.index.by_path.keys() )
    assert f"{n.uid}/my_child_0" in n.index
    assert n.find( "my_child_0" ) == n.children[0]

    m = NodeWithChildren(
        uid = "mmm",
        children = [ {'value': 1}, {'value': 2}]
    )
    assert "mmm/my_child_0" in m.index


def test_templated_self_structuring():

    @attr.define(init=False)
    class NodeWithTemplateChildren(SelfStructuring, Templated, Node):
        value: int = 0
        children: list[NodeWithTemplateChildren] = attr.ib( factory=list, metadata={"f_uid": "my_child_{0}"})

    attr.resolve_types(NodeWithTemplateChildren, localns=locals())

    template_maps = {
        'abc': {'value': 123, 'children': [{'value': 456}]}
    }

    n = NodeWithTemplateChildren( templates=['abc'], template_maps=template_maps )
    print( n )
    assert isinstance( n.children[0], NodeWithTemplateChildren )


def test_consumes_str():

    @attr.define(init=False)
    class NodeWithChildren(SelfStructuring, Node):
        value: str = attr.ib( default=None, metadata={"consumes_str": True})
        children: list[NodeWithChildren] = attr.ib( factory=list, metadata={"f_uid": "my_child_{0}"})

    attr.resolve_types(NodeWithChildren, localns=locals())

    n = NodeWithChildren(
        children = [ "abc", "def" ]
    )
    print( n )
    assert isinstance( n.children[0], Node )
    assert n.children[0].uid == "my_child_0"


def test_cascaded_ns():

    # print( attr.fields(Node2) )

    n = Node(locals={"var1": 10, "var2": 100})
    m = Node(locals={"var2": 1000}, parent=n)

    assert n.ns()['var1'] == 10

    assert m.ns()['var1'] == 10
    assert m.ns()['var2'] == 1000
