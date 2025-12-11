# No longer supported

from __future__ import annotations
from typing import *
from pprint import pprint

import attr

from tangl.core import Templated, Node, Automorphic, SelfStructuring

import pytest

@attr.define(init=False)
class Test(Automorphic, Templated, SelfStructuring, Node):
    a: int = attr.ib(default=100, metadata={"reduce": True})
    b: Test = None
    c: list[Test] = attr.ib(factory=list)

@attr.define(init=False)
class Test2( Test ):
    d: str = "foo"

attr.resolve_types(Test)

template_maps = {
    'Test': {
        "dog": {"a": -1000},
        "cat": {"a": 10000}
    },
    'Test2': {'cat': {"a": 5000}}}

def test_classes():

    el = Test()
    print( el )
    assert( el.a == 100 )

    el = Test2()
    assert( el.d == "foo" )

def test_reducer():
    el = Test(a=[1000, 2000])
    print( el )
    assert( 1000 <= el.a <= 2000 )

def test_templates():
    template_maps = {
        'Test': {
            "dog": { "a": -1000 },
            "cat": { "a": 10000 }
        }
    }

    el = Test(templates=["dog"], template_maps=template_maps['Test'])
    print( el )
    assert( el.a == -1000 )

    # test template order priority
    el = Test(templates=["cat", "dog"], template_maps=template_maps['Test'])
    print( el )
    assert( el.a == 10000 )

def test_automorphism():

    el = Test2( _cls="Test", a=99 )
    # print( el )
    assert isinstance( el, Test )
    assert el.a == 99

def test_child_structuring():

    el = Test( b={"a": 99 })
    print( el )
    assert isinstance( el.b, Node )
    assert el.b.parent == el
    assert el.b.root == el

    el = Test( c=[{'a': 999}, {'b': {'a': 9999}}] )
    print( el )
    assert len( el.c ) == 2
    assert el.c[0].parent == el
    assert el.c[1].b.a == 9999

@pytest.mark.skip(reason="Does not still work like this")
def test_child_templates():

    el = Test2( d="bar", b={"templates": ["dog"]}, templates=["cat"], template_maps=template_maps['Test'] )
    assert el.d == "bar"
    assert el.b.a == -1000
    assert el.a == 10000

@pytest.mark.skip(reason="Not sure it still works like this")
def test_subclass_template_priority():
    el = Test2( templates=["cat"], template_maps=template_maps['Test2'] )
    assert el.a == 5000
