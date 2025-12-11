import pydantic
import pytest

from tangl.entity import Entity, SingletonEntity

class SelfCastingEntity(Entity):
    extra_field1: str = "Extra"

class SubSelfCastingEntity(SelfCastingEntity):
    extra_field2: str = "ExtraExtra"

def test_subclass_handling():
    subclass_name = "SelfCastingEntity"
    found_class = Entity.get_subclass_by_name(subclass_name)
    assert found_class is not None
    assert found_class == SelfCastingEntity

    subclass_name = "SubSelfCastingEntity"
    found_class = Entity.get_subclass_by_name(subclass_name)
    assert found_class is not None
    assert found_class == SubSelfCastingEntity


def test_subclass_casting():
    obj = SelfCastingEntity(obj_cls="SubSelfCastingEntity", extra_field2="abc")
    assert isinstance(obj, SubSelfCastingEntity)

class SelfCastingSingleton(SingletonEntity):
    extra_field1: str = "Extra"

class SubSelfCastingSingleton(SelfCastingSingleton):
    extra_field2: str = "ExtraExtra"

def test_singleton_handling():
    obj = SingletonEntity(obj_cls="SelfCastingSingleton", label="hello", extra_field1="abc")
    assert isinstance(obj, SelfCastingSingleton)
    assert SelfCastingSingleton.get_instance("hello") is obj

    obj = SingletonEntity(obj_cls="SubSelfCastingSingleton", label="hello2", extra_field2="abc")
    assert isinstance(obj, SubSelfCastingSingleton)
    assert SubSelfCastingSingleton.get_instance("hello2") is obj


def test_singleton_subclass_casting():

    obj = SelfCastingSingleton(obj_cls="SubSelfCastingSingleton", label="hello3", extra_field2="abc")
    assert isinstance(obj, SubSelfCastingSingleton)
    assert SubSelfCastingSingleton.get_instance("hello3") is obj

def test_default_behavior():
    obj = SelfCastingEntity(extra_field1="default")
    assert isinstance(obj, SelfCastingEntity)

def test_invalid_class_name():
    with pytest.raises(KeyError):
        SelfCastingEntity(obj_cls="NonExistentClass")

def test_field_inheritance_and_integrity():
    obj = SubSelfCastingEntity(extra_field1="test1", extra_field2="test2")
    assert obj.extra_field1 == "test1"
    assert obj.extra_field2 == "test2"

    with pytest.raises(pydantic.ValidationError):
        SubSelfCastingEntity(extra_field1=123)

class DeepSubSelfCastingEntity(SubSelfCastingEntity):
    extra_field3: str = "DeeperExtra"

def test_deep_subclass_casting():
    obj = Entity(obj_cls="DeepSubSelfCastingEntity", extra_field3="abc")
    assert isinstance(obj, DeepSubSelfCastingEntity)

def test_singleton_identity():
    obj1 = SelfCastingSingleton(obj_cls="SubSelfCastingSingleton", label="singleton", extra_field2="abc")
    obj2 = SubSelfCastingSingleton.get_instance("singleton")
    assert obj1 is obj2
