from tangl.entity import Entity, SingletonEntity
from tangl.graph import Graph, Node
from tangl.entity.mixins import *
from tangl.utils.inheritance_aware import InheritanceAware


class TestMixinSubclass(Renderable):
    ...

class TestSubclassEntity(TestMixinSubclass, HasNamespace, Node):
    ...

def test_simple_superclass_introspection():

    assert Entity.get_all_superclasses() == { Entity, InheritanceAware }
    assert SingletonEntity.get_all_superclasses() == { SingletonEntity, Entity, InheritanceAware }
    assert Node.get_all_superclasses() == { Entity, Node, InheritanceAware }
    assert Graph.get_all_superclasses() == { Entity, Graph, InheritanceAware }

def test_complex_superclass_introspection():

    assert TestSubclassEntity.get_all_superclasses() == {
        Renderable, TestSubclassEntity, TestMixinSubclass, Node, Entity, HasNamespace, InheritanceAware
    }


def test_get_superclass_source():
    res = TestSubclassEntity.get_all_superclass_source(as_yaml=True)
    assert isinstance(res, str)

    res = TestSubclassEntity.get_all_superclass_source(ignore=(Entity, TestMixinSubclass),
                                                        as_yaml=False)
    assert isinstance(res, dict)
    assert 'Node' in res
    assert 'Entity' not in res

