import pytest
from typing import Type
import logging

from tangl.core.handler import BaseHandler, Priority
from tangl.core.entity import Entity
from tangl.core.entity.handlers import SelfFactoringModel, SelfFactoring, SelfFactoringHandler

# Mock classes for testing
class BaseMock(metaclass=SelfFactoring):
    def __init__(self, value):
        self.value = value

    def __new__(cls, *args, **kwargs):
        logging.debug(f"BaseMock.__new__ called for {cls.__name__}")
        return super().__new__(cls)

    def __init__(self, value):
        logging.debug(f"BaseMock.__init__ called with value={value}")
        self.value = value

class SubMock(BaseMock):
    pass


class AnotherSubMock(BaseMock):
    pass


def test_basic_instantiation():
    obj = BaseMock(42)
    assert isinstance(obj, BaseMock)
    assert obj.value == 42


def test_subclass_instantiation():
    obj = SubMock(42)
    assert isinstance(obj, SubMock)
    assert isinstance(obj, BaseMock)
    assert obj.value == 42


def test_obj_cls_casting_with_type():
    obj = BaseMock(value=42, obj_cls=SubMock)
    assert isinstance(obj, SubMock)
    assert obj.value == 42


def test_obj_cls_casting_with_string():
    obj = BaseMock(value=42, obj_cls="SubMock")
    assert isinstance(obj, SubMock)
    assert obj.value == 42


def test_obj_cls_casting_invalid_subclass():
    class UnrelatedClass:
        pass

    with pytest.raises(TypeError):
        BaseMock(value=42, obj_cls=UnrelatedClass)


def test_obj_cls_casting_invalid_string():
    with pytest.raises(KeyError):
        BaseMock(value=42, obj_cls="NonExistentClass")


def test_obj_cls_casting_invalid_type():
    with pytest.raises(ValueError):
        BaseMock(value=42, obj_cls=42)  # Invalid obj_cls type


def test_custom_strategy():
    @BaseHandler.strategy('on_new', priority=Priority.LATE)
    @staticmethod
    def custom_strategy(base_cls: Type, special = None, **kwargs):
        if special is not None:
            return AnotherSubMock, {**kwargs, 'value': special}
        return base_cls, kwargs

    obj = BaseMock(special=99)
    assert isinstance(obj, AnotherSubMock)
    assert obj.value == 99

    BaseHandler.deregister_strategy('on_new', custom_strategy)

def test_multiple_strategies():
    @BaseHandler.strategy('on_new', priority=Priority.EARLY)
    @staticmethod
    def strategy1(base_cls: Type, **kwargs):
        kwargs['value'] = [ 'step1' ]
        return base_cls, kwargs

    @BaseHandler.strategy('on_new', priority=Priority.LATE)
    @staticmethod
    def strategy2(base_cls: Type, **kwargs):
        kwargs['value'].append('step2')
        return base_cls, kwargs

    obj = BaseMock(value=42)
    assert obj.value == [ 'step1', 'step2' ]

    BaseHandler.deregister_strategy('on_new', strategy1, strategy2)

def test_strategy_order():
    order = []

    @BaseHandler.strategy('on_new', priority=Priority.EARLY)
    @staticmethod
    def strategy1(base_cls: Type, **kwargs):
        logging.debug('strategy 1')
        order.append(1)
        return base_cls, kwargs

    @BaseHandler.strategy('on_new', priority=Priority.NORMAL)
    @staticmethod
    def strategy2(base_cls: Type, **kwargs):
        logging.debug('strategy 2')
        order.append(2)
        return base_cls, kwargs

    @BaseHandler.strategy('on_new', priority=Priority.LATE)
    @staticmethod
    def strategy3(base_cls: Type, **kwargs):
        logging.debug('strategy 3')
        order.append(3)
        return base_cls, kwargs

    SelfFactoringHandler.register_strategy(strategy1, 'on_new')
    SelfFactoringHandler.register_strategy(strategy2, 'on_new')
    SelfFactoringHandler.register_strategy(strategy3, 'on_new')

    BaseMock(value=42)
    assert order == [1, 2, 3]

    BaseHandler.deregister_strategy('on_new', strategy1, strategy2, strategy3)


class SelfFactoringEntity(Entity, metaclass=SelfFactoringModel):
    ...

def test_sf_entity():

    sf_entity = SelfFactoringEntity()
    assert isinstance(sf_entity, SelfFactoringEntity)

    class SelfFactoringEntity2(SelfFactoringEntity, metaclass=SelfFactoringModel):
        ...

    sf_entity2 = SelfFactoringEntity(obj_cls=SelfFactoringEntity2)
    assert isinstance(sf_entity2, SelfFactoringEntity2)


def test_sf_entity_mixins():
    from tangl.core.entity.handlers import HasNamespace

    class SelfFactoringEntityNs(HasNamespace, Entity, metaclass=SelfFactoringModel):
        abc: int = 1
        foo: str

    sf_entity = SelfFactoringEntityNs(foo="abc")
    assert sf_entity.abc == 1
    assert sf_entity.foo == "abc"
    assert sf_entity.locals == {}
    assert isinstance(sf_entity, SelfFactoringEntityNs)

