from typing import Mapping, Iterator

import pytest

from tangl.core.entity import Entity, Graph
from tangl.core.dispatch import HandlerRegistry, HasHandlers, Handler

on_mock_task = HandlerRegistry(label="mock_task")
on_pipeline_task = HandlerRegistry(label="pipeline_task")

# Mock entity has a built-in strategy with no class bound
class MockEntity(Entity):

    @on_mock_task.register(priority=90)
    def strategy_low_priority(self, *args, **kwargs):
        return 'low_priority_result'


# Register some mock strategies for testing
class MockHandler(HasHandlers):

    @on_mock_task.register(priority=10)
    @staticmethod
    def strategy_high_priority(caller: MockEntity, **kwargs):
        return 'high_priority_result'

    # @on_pipeline_task.register(priority=10)
    # @staticmethod
    # def strategy_pipeline_step_1(caller: MockEntity, **kwargs):
    #     # add a new kwarg
    #     print( "step 1")
    #     return entity, {**kwargs, 'new_kwarg': 'value'}
    #
    # @on_pipeline_task.register(priority=20)
    # @staticmethod
    # def strategy_pipeline_step_2(caller: MockEntity, **kwargs):
    #     # consume initial kwarg2
    #     print('step 2', {*kwargs})
    #     return entity, kwargs

    # @BaseHandler.strategy('test_task', domain="test_domain")
    # @staticmethod
    # def strategy_domain_val(entity, **kwargs):
    #     # consume initial kwarg2
    #     return entity, {'domain': 'test_value', **kwargs}

@pytest.fixture
def entity():
    return MockEntity()

def test_execute_task_default(entity):
    result = on_mock_task.execute_all_for(entity, ctx=None)
    assert result == [ 'high_priority_result', 'low_priority_result' ]

def test_execute_task_first_mode(entity):
    result = on_mock_task.execute_all_for(entity, ctx=None, strategy='first')
    assert result == 'high_priority_result'

def test_execute_task_flatten_dict(entity):
    on_flatten_task = HandlerRegistry(label="flatten_task", aggregation_strategy="merge")
    h1 = Handler(func=lambda caller, **kwargs: {'key1': 'value1'}, caller_cls=MockEntity, priority=30)
    on_flatten_task.add(h1)
    h2 = Handler(func=lambda caller, **kwargs: {'key2': 'value2'}, caller_cls=MockEntity, priority=40)
    on_flatten_task.add(h2)

    result = on_flatten_task.execute_all_for(entity, ctx=None)

    assert isinstance(result, Mapping)
    assert result['key1'] == 'value1'
    assert result['key2'] == 'value2'

    # Used to be able to create a chainmap or update single dict
    # result = handler.execute_task(entity, 'merge_task', result_mode='chain')
    # from collections import ChainMap
    # assert isinstance(result, ChainMap)
    # assert result['key1'] == 'value1'
    # assert result['key2'] == 'value2'

def test_execute_task_flatten_list(entity):
    on_flatten_task = HandlerRegistry(label="flatten_task", aggregation_strategy="merge")
    h1 = Handler(func=lambda caller, **kwargs: [1, 2], caller_cls=MockEntity, priority=30)
    on_flatten_task.add(h1)
    h2 = Handler(func=lambda caller, **kwargs: [3, 4], caller_cls=MockEntity, priority=40)
    on_flatten_task.add(h2)

    result = on_flatten_task.execute_all_for(entity, ctx=None)
    assert result == [1, 2, 3, 4]

def test_execute_task_all_true_mode(entity):
    on_all_true_task = HandlerRegistry(label="all_true_task", aggregation_strategy="all_true")
    h1 = Handler(func=lambda caller, **kwargs: True, caller_cls=MockEntity)
    on_all_true_task.add(h1)

    assert on_all_true_task.execute_all_for(entity, ctx=None)

    h2 = Handler(func=lambda caller, **kwargs: False, caller_cls=MockEntity)
    on_all_true_task.add(h2)
    assert not on_all_true_task.execute_all_for(entity, ctx=None)

# def test_execute_task_pipeline_mode(handler, entity):
#     kwargs = {'initial_kwarg': 'value', 'initial_kwarg2': 'value2'}
#     result = handler.execute_task(entity, 'pipeline_task', result_mode='pipeline', **kwargs)
#     assert result == (entity, {'initial_kwarg': 'value', 'new_kwarg': 'value'})
#
def test_execute_task_iter_mode(entity):
    iter_result = on_mock_task.execute_all_for(entity, ctx=None, strategy='iter')
    assert isinstance(iter_result, Iterator)
    assert list(iter_result) == ['high_priority_result', 'low_priority_result']

# class MockEntityWithDomain(MockEntity):
#     domain = 'test_domain'
#
#     def strategy_domain(self, *args, **kwargs):
#         return 'domain_low_priority_result'
#
# # @pytest.fixture(autouse=True)
# # def reset_test_domain_registry():
# #
# #
# #     StrategyRegistry.discard_instance('test_domain')
# #     BaseHandler.register_strategy(MockEntityWithDomain.strategy_domain, 'test_task', 'test_domain', priority=100)
#
# @pytest.fixture
# def domain_entity():
#     return MockEntityWithDomain()
#
# def test_execute_domain_task(handler, entity, domain_entity):
#     result = handler.execute_task(entity, 'test_task')
#     assert result == [ 'high_priority_result', 'low_priority_result' ]
#
#     result = handler.execute_task(domain_entity, 'test_task', ['test_domain'])
#     assert result == [ 'high_priority_result', 'low_priority_result', 'domain_low_priority_result' ]
#
#     result = handler.execute_task(domain_entity, 'test_task')
#     assert result == [ 'high_priority_result', 'low_priority_result', 'domain_low_priority_result' ]

class MockEntitySub(MockEntity):

    @on_mock_task.register(priority=0)
    def strategy_sub_entity(self, **kwargs):
        return 'sub_high_priority_result'

@pytest.fixture
def sub_entity():
    return MockEntitySub()

def test_execute_sub_task(sub_entity):
    result = on_mock_task.execute_all_for(sub_entity, ctx=None)
    assert result == [ 'sub_high_priority_result', 'high_priority_result', 'low_priority_result' ]
