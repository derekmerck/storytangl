from __future__ import annotations
import logging

import pydantic
import pytest

from tangl.type_hints import Typelike
from tangl.entity import Entity, SingletonEntity
from tangl.entity.smart_new import SmartNewHandler

######################
# Template Tests
######################


@pytest.fixture
def template_maps():
    return [
        {"Base": {"a": 1, "b": 2}},
        {"Extended": {"templates": ["Base"], "b": 3, "c": 4}},
        {"Custom": {"templates": ["Extended"], "c": 5, "d": 6}}
    ]

def test_single_template(template_maps):
    result = SmartNewHandler.aggregate_templates(["Base"], template_maps)
    assert result == {"a": 1, "b": 2}

def test_template_inheritance(template_maps):
    result = SmartNewHandler.aggregate_templates(["Extended"], template_maps)
    assert result == {"a": 1, "b": 3, "c": 4}

def test_multiple_templates(template_maps):
    result = SmartNewHandler.aggregate_templates(["Base", "Custom"], template_maps)
    assert dict(result) == {"a": 1, "b": 2, "c": 5, "d": 6}

def test_template_ordering(template_maps):
    result = SmartNewHandler.aggregate_templates(["Extended", "Custom", "Base"], template_maps)
    # Expected result depends on how you want to handle conflicting keys when multiple templates are specified.
    assert dict(result) == {"a": 1, "b": 3, "c": 4, "d": 6}

######################
# Class Tests
######################

class SubClassEntity(Entity):
    ...

class SubSubClassEntity(SubClassEntity):
    foo: str

class SubClassSingleton(SingletonEntity):

    foo: str

    def __new__(cls, *args, **kwargs):
        print("setting a flag in _instances that custom new was called")
        cls._instances["hello"] = "world"
        try:
            return super().__new__(cls, *args, **kwargs)
        except TypeError:
            return object.__new__(cls)

class SubSubClassSingleton(SubClassSingleton):
    ...

class SubSubSubClassSingleton(SubSubClassSingleton):
    ...


def test_smart_entity():

    assert isinstance(Entity(), Entity)
    assert isinstance(Entity(obj_cls="SubClassEntity"), SubClassEntity)
    assert isinstance(SubClassEntity(), SubClassEntity)
    assert isinstance(Entity(obj_cls="SubSubClassEntity", foo="bar"), SubSubClassEntity)
    assert isinstance(SubClassEntity(obj_cls="SubSubClassEntity", foo="bar"), SubSubClassEntity)
    assert isinstance(SubSubClassEntity(obj_cls="SubSubClassEntity", foo="bar"), SubSubClassEntity)

    with pytest.raises(pydantic.ValidationError):
        SubSubClassEntity(), "should flag missing 'foo' param"

    with pytest.raises(pydantic.ValidationError):
        SubClassEntity(obj_cls="SubSubClassEntity"), "should flag missing 'foo' param"

    with pytest.raises(pydantic.ValidationError):
        Entity(obj_cls="SubSubClassEntity"), "should flag missing 'foo' param"

@pytest.fixture(autouse=True)
def clear_singletons():
    SingletonEntity.clear_instances()
    SubClassSingleton.clear_instances()

def test_smart_singleton():
    abc = SingletonEntity(label='abc')

    assert isinstance(abc, Entity)
    assert isinstance(abc, SingletonEntity)

    defg = SingletonEntity(label='abc')
    assert defg is abc

def test_subclass_singleton():
    abc = SubClassSingleton(label='abc', foo="bar")
    defg = SubClassSingleton(label='abc')

    # check that the custom new got called properly
    assert SubClassSingleton._instances['hello'] == "world"

    assert defg is abc
    assert isinstance(defg, SubClassSingleton)
    assert defg.foo == "bar"

    with pytest.raises(ValueError):
        SubClassSingleton(), "should flag required 'label' param"

    with pytest.raises(pydantic.ValidationError):
        SubClassSingleton(label="defg"), "should flag missing 'foo' param"


def test_subclass_singleton_different_classes():
    abc = SubClassSingleton(label='abc2', foo="bar")
    defg = SingletonEntity(label='abc2')

    assert defg is not abc, "should be different object types with the same label"
    assert isinstance(defg, SingletonEntity)


def test_smart_subclass_singleton():
    abc = SingletonEntity(obj_cls="SubClassSingleton", label='abc3', foo="bar")
    assert isinstance(abc, SubClassSingleton)

    # check that the custom new got called properly in this class
    assert SubClassSingleton._instances['hello'] == "world"

    defg = SubClassSingleton(label='abc3')
    assert defg is abc
    assert defg.foo == "bar"
    assert isinstance(defg, SubClassSingleton)

def test_new_called_subsub():

    abc = SingletonEntity(obj_cls="SubSubClassSingleton", label='abc3', foo="bar")

    # check that the custom new in super got called properly
    assert SubSubClassSingleton._instances['hello'] == "world"

def test_new_called_subsubsub():

    abc = SingletonEntity(obj_cls="SubSubSubClassSingleton", label='abc3', foo="bar")

    # check that the custom new in super^2 got called properly
    assert SubSubSubClassSingleton._instances['hello'] == "world"
