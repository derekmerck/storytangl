from typing import *

import attr

from tangl.entity import Entity, EntityFactory, EntityMap
from tangl.entity.utils import reduce_defaults


@attr.define(slots=False, init=False)
class MyEntity(Entity):

    factory: EntityFactory = attr.ib( default=None, repr=False )

    test1: int = attr.ib(default=["abc", "def"],
                         metadata={"state": True},
                         converter=reduce_defaults)

    test2: int = attr.ib( default=["abc", "def"],
                          metadata={"state": True},
                          converter=reduce_defaults)

    item_dict: Dict[str, "MyEntity"] = attr.ib( factory=dict, metadata={"state": True} )
    item_list: List["MyEntity"] = attr.ib( factory=list, metadata={"state": True} )

    __init__ = Entity.__init__


# make sure attrib hints are resolved
attr.resolve_types(MyEntity)



def test_factoried_children():

    F = EntityFactory()
    F.add_entity_class( MyEntity )
    e = MyEntity( item_list=[{"test1": "foo"}], factory=F )
    print( e )
    assert( isinstance(e.item_list[0], MyEntity) and e.item_list[0].test1=="foo" )

    F.templates.add_template( 'MyEntity', 'foo',
                              test2=['bar', 'spam'],
                              item_list=[{'test1': 1}],
                              item_dict = { "dog": {'test1': 2} } )
    e = MyEntity( uid="foo", factory=F )

    # e = F.new_entity( "MyEntity", uid="foo" )
    print( e )

    assert e.item_list[0].uid == "it0" and e.item_list[0].test1 == 1
    assert e.item_dict['dog'].uid == "dog" and e.item_dict["dog"].test1 == 2

    F.templates.add_template( 'MyEntity', 'dog',
                              test2=['alpha', 'beta'] )

    e = F.new_entity( "MyEntity", uid="foo" )
    print( e )

    assert e.item_dict['dog'].uid == "dog"
    assert e.item_dict["dog"].test2 in ["alpha", "beta"]

    F.templates.add_template( 'MyEntity', 'cat',
                              test1=['gamma', 'delta'] )

    e = F.new_entity( "MyEntity", uid="foo", templates=["cat"] )
    print( e )

    assert e.item_list[0].uid == "it0" and e.item_list[0].test1 == 1
    assert e.item_dict['dog'].uid == "dog" and e.item_dict["dog"].test2 in ["alpha", "beta"]
    assert e.test1 in ["gamma", "delta"]


def test_factoried_subclasses():

    F = EntityFactory()
    F.templates.add_template( 'MyEntity', 'foo',
                              test2=['bar', 'spam'],
                              item_list=[{'test1': 1}],
                              item_dict = { "dog": {'test1': 2} } )
    F.add_entity_class( MyEntity )

    e = MyEntity( factory=F, templates='foo' )
    print( e )

    assert e.item_list[0].uid == "it0" and e.item_list[0].test1 == 1
    assert e.item_dict['dog'].uid == "dog" and e.item_dict["dog"].test1 == 2

    # e = MyEntity( item_list = [ {'test1': 1} ],
    #               item_dict = { "foo": {'test1': 2} } )
    # print( e )
    #
    # e = MyEntity( item_list = [ {'test1': 1} ],
    #               item_dict = { "foo": {'test1': 2} },
    #               factory=F )
    # print( e )
    #
    # f = F.new_entity( 'MyEntity', 'foo' )  # type: MyEntity
    # print( f )
    # assert( isinstance( f, MyEntity) )
    # assert( f.test2 in ['bar', 'spam'] )
    # assert( isinstance( f.item_dict["foo"], MyEntity ) )
    #
    # # flatten and inflate
    # flat = f.as_dict()
    # print( flat )
    # ff = F.new_entity( entity_typ="MyEntity", **flat )
    # print( ff )
    # assert f == ff
    #
    # # kwargs and children
    # g = F.new_entity( 'MyEntity', 'foo',
    #                   test2="cat",
    #                   locals={"hello": "goodbye", "a": 2},
    #                   item_dict={'foo': {}, 'bird': {'locals': {'a': 1}}},
    #                   item_list=[ {'test2': "blah"} ] )
    # print( g )
    # assert g.test2 == 'cat'
    # assert g.path == "foo"
    #
    # # namespaces
    # h = g.item_dict['foo']   # first child
    # assert h.path == "foo/foo"
    # i = g.item_dict['bird']  # second child
    # assert i.path == "foo/bird"
    #
    # print( h.ns() )
    # print( i.ns() )
    #
    # assert h.ns()['a'] == 2  # parent value
    # assert i.ns()['a'] == 1  # private value


from tangl.entity import *


def test_factory_map():

    F = EntityFactory()
    F.templates.add_template( 'MyEntity', 'foo', test2=['bar', 'spam'] )
    F.add_entity_class( MyEntity )

    ctx = EntityMap()
    g = F.new_entity( 'MyEntity',
                      uid='foo',
                      test2="cat",
                      locals={"hello": "goodbye", "a": 2},
                      item_dict={'foo': {}, 'bird': {'locals': {'a': 1}}},
                      item_list=[ {'test2': "blah"} ],
                      ctx=ctx )

    h = g.item_dict['foo']   # children items

    print( ctx )
    print( ctx.keys() )

    assert h.eid in ctx

    assert "foo/foo" in ctx
    assert "foo/bird" in ctx
    assert "foo/dog" not in ctx


def test_entity_map_persistence():
    import pickle

    ctx = EntityMap()
    el = Entity(uid="abc", ctx=ctx)

    print(ctx.keys())
    assert (el in ctx)
    assert (el.eid in ctx)
    assert (el.path in ctx)

    assert ctx["abc"] == el

    ser = pickle.dumps(ctx)
    out = pickle.loads(ser)

    assert out == ctx


def test_factoried_map_persistence():

    F = EntityFactory()
    F.templates.add_template( 'MyEntity', 'foo', test2=['bar', 'spam'] )
    F.add_entity_class( MyEntity )

    ctx1 = EntityMap()
    F.new_entity(entity_typ='MyEntity', ctx=ctx1, uid="elephant", item_dict={"foo": {}})
    assert "elephant" in ctx1

    from pickle import loads, dumps

    pik = dumps( ctx1 )
    print( pik )

    ctx2 = loads( pik )
    print( ctx2 )
    assert ctx1 == ctx2

    el2 = ctx2['elephant']
    print( el2.factory )
    assert isinstance(el2.factory, EntityFactory)

    # ctx structure / unstructure

    # basic pickle
    pik = ctx1.unstructure()
    ctx3 = EntityMap.structure(pik)

    assert ctx1 == ctx3


def test_templates():

    f = EntityFactory( uid="templates" )
    f.add_entity_class( MyEntity )
    f.add_template( MyEntity, "template1", test1 = "foo", templates = "template2" )
    f.add_template( MyEntity, "template2", test1 = "cat", test2 = "dog" )

    print( f.templates )

    e = f.new_entity( MyEntity, templates="template2" )
    print( e )
    assert( e.test1 == "cat" and e.test2 == "dog" )

    e = f.new_entity( MyEntity, uid="template2" )
    assert( e.test1 == "cat" and e.test2 == "dog" )

    e = f.new_entity( MyEntity, templates="template1" )  # uses template 2 and overrides test1=foo
    print( e )
    assert( e.test1 == "foo" and e.test2 == "dog" )

    e = f.new_entity( MyEntity, uid="template1" )
    assert( e.test1 == "foo" and e.test2 == "dog" )

