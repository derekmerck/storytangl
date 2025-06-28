from __future__ import annotations
import types

import pytest

from tangl.core.entity import Entity
from tangl.core.handlers import Satisfiable, HasEffects, RuntimeEffect

MyEffectEntity = type('MyEffectEntity', (HasEffects, Entity), {} )


def test_on_apply_effects_builtins():
    r = MyEffectEntity()

    # can access "safe builtins"
    assert RuntimeEffect.exec_raw_expr("2+3", ctx={}) == {}, "returns empty context dict"

    # no access for other builtins
    with pytest.raises(NameError):
        RuntimeEffect.exec_raw_expr('print("hello")', ctx={})

def test_apply_effects():
    # Setup an entity with a mutable object in its namespace
    mutable_obj = {'key': 'initial value'}
    test_entity = MyEffectEntity(
        effects=["mutable_obj['key'] = 'changed value'"],
        locals={'mutable_obj': mutable_obj}
    )

    # Apply effect
    test_entity.apply_effects()
    updated_namespace = test_entity.gather_context()

    # Verify that the change is reflected in the namespace
    assert updated_namespace['mutable_obj']['key'] == 'changed value', "The effect should modify the value within the referenced object"

def test_apply_effect1():
    n = MyEffectEntity( locals={'abc': {} },
                        effects=["abc['foo'] = 'bar'"])
    n.apply_effects()
    assert n.locals['abc']['foo'] == 'bar'


def test_apply_effect2():

    statement = "name = 'Alice'"
    namespace = {"name": "Bob"}

    node = MyEffectEntity(locals=namespace, effects=[ statement ])
    assert node.locals["name"] == "Bob"

    ctx = node.gather_context()
    print( ctx )
    assert ctx.maps[0] is node.locals

    node.apply_effects()
    assert node.locals["name"] == "Alice"

def test_apply_effects3():
    effects = ["x += 5"]
    namespace = {"x": 10}

    mixin = MyEffectEntity(effects=effects, locals=namespace)
    mixin.apply_effects()
    assert mixin.locals["x"] == 15

def test_apply_effects_to():
    ref_node = MyEffectEntity(locals={"x": 1})
    mixin = MyEffectEntity(effects=["x += 1"])

    mixin.apply_effects(ctx=ref_node.gather_context())
    assert ref_node.locals["x"] == 2

def test_multiple_effects():
    n = MyEffectEntity(
        locals={'abc': {}},
        effects=["abc['foo'] = 'bar'", "abc['foobar'] = abc['foo']"])
    n.apply_effects()
    assert n.locals['abc']['foo'] == 'bar'
    assert n.locals['abc']['foobar'] == 'bar'

def test_effect_conditional_execution():
    n = MyEffectEntity(locals={'condition': True, 'foo': {}},
                            effects=["if condition: foo['abc'] = 1"])
    n.apply_effects()
    assert n.locals['foo']['abc'] == 1

def test_effect_no_local_change():
    n = MyEffectEntity(effects=["non_existent['foo'] = 'bar'"])
    with pytest.raises(NameError):
        n.apply_effects()  # Expecting NameError since 'non_existent' is not in locals

    n.locals['non_existent'] = 0

    with pytest.raises(TypeError):
        n.apply_effects()  # Expecting TypeError since can't assign kv to an int

def test_effect_dynamic_namespace_update():
    n = MyEffectEntity(locals={'foo': types.SimpleNamespace(counter=0)},
                       effects=["foo.counter += 1", "foo.counter += 1"])
    n.apply_effects()
    assert n.locals['foo'].counter == 2

# todo: this should not work as implemented, i think?  maybe b/c it's a chainmap?
def test_effect_dynamic_locals_update():
    n = MyEffectEntity(locals={'foo': 0},
                       effects=["foo += 1", "foo += 1"])
    n.apply_effects()
    assert n.locals['foo'] == 2

def test_conditional_applyable():

    MyCEEntity = type('MyCEEntity', (HasEffects, Satisfiable, Entity), {} )

    conditions = ["'sword' in inventory"]
    effects = ["inventory.remove('sword')", "inventory.append('elixir')"]
    namespace = {"inventory": ['sword', 'shield']}

    mixin = MyCEEntity(locals=namespace, predicates=conditions, effects=effects)

    assert mixin.is_satisfied() is True
    mixin.apply_effects()
    assert mixin.locals["inventory"] == ['shield', 'elixir']

    A = MyCEEntity( conditions=["A is None"], locals={"A": None} )
    assert( A.is_satisfied() is True )

    B = MyCEEntity( effects=["B['foo']=5"], locals={"B": {'bar': 10}} )
    B.apply_effects()
    assert B.locals['B']['foo'] == 5

    D = MyCEEntity( effects=["d=5"], locals={"d": 10} )
    assert D.locals['d'] == 10

