from __future__ import annotations

import pytest

from scratch.core210.strategy import StrategyHandler, DomainStrategyManager

class Entity:
    def __init__(self, domain: str = None):
        self.domain = domain

    @StrategyHandler.strategy("process", priority=10)
    def base_process(self: Entity):
        return {"base": "processed"}

class SubEntity(Entity):

    @StrategyHandler.strategy("process", priority=20)
    def sub_process(self: SubEntity):
        return {"sub": "processed"}

class OverrideEntity(Entity):

    @StrategyHandler.strategy("process", priority=80)
    def override_process(self: OverrideEntity):
        return {"base": "override"}

    @StrategyHandler.strategy("process", priority=80)
    def conditional_override_domain(self: OverrideEntity):
        if self.domain:
            return {"domain": "override"}

def domain_specific_process(entity: Entity):
    return {"domain": "processed"}

# handler.register_domain_strategy("special_domain", "process", domain_specific_process, priority=30)

@DomainStrategyManager.strategy('special_domain', 'process')
def _decorator_domain_registration(entity: Entity):
    return {'decorated_domain': 'processed'}

@pytest.fixture(autouse=True)
def _reset_domain_handler():
    DomainStrategyManager.discard_instance('special_domain')
    DomainStrategyManager.get("special_domain").register_strategy("process", domain_specific_process, priority=30)

def test_basic():
    entity = Entity()
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'base': 'processed'}
    assert {'base'} == {*result}

def test_domain():

    entity = Entity("special_domain")
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'base': 'processed', 'domain': 'processed'}
    assert {'base', 'domain'} == {*result}

def test_domain_register_via_strategy_handler():

    DomainStrategyManager.discard_instance('special_domain')
    StrategyHandler.register_domain_strategy('special_domain', 'process', domain_specific_process)

    entity = Entity("special_domain")
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'base': 'processed', 'domain': 'processed'}
    assert {'base', 'domain'} == {*result}

def test_domain_register_via_decorator():

    DomainStrategyManager.discard_instance('special_domain')

    @DomainStrategyManager.strategy('special_domain', 'process')
    def domain_specific_process(entity: Entity):
        return {"domain": "processed"}

    entity = Entity("special_domain")
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'base': 'processed', 'domain': 'processed'}
    assert {'base', 'domain'} == {*result}

def test_mro():
    entity = SubEntity()
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'sub': 'processed', 'base': 'processed'}
    assert {'base', 'sub'} == {*result}

def test_mro_and_domain():
    entity = SubEntity("special_domain")
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'domain': 'processed', 'sub': 'processed', 'base': 'processed'}
    assert {'base', 'sub', 'domain'} == {*result}

def test_priority_mro():
    entity = OverrideEntity()
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'base': 'override'}
    assert {'base'} == {*result}
    assert result['base'] == "override"

def test_priority_mro_domain():
    entity = OverrideEntity("special_domain")
    result = StrategyHandler.execute_task(entity, "process", result_mode="merge")
    print(result)  # Output: {'base': 'override', 'domain': 'processed'}
    assert {'base', 'domain'} == {*result}
    assert result['base'] == "override"
    assert result['domain'] == "override"

def test_return_first_mode():
    entity = SubEntity()
    first_result = StrategyHandler.execute_task(entity, "process", result_mode="first")
    print(first_result)
    assert isinstance(first_result, dict)
    assert len(first_result) == 1

def test_return_iter():
    entity = SubEntity()
    iter_result = StrategyHandler.execute_task(entity, "process", result_mode="iter")
    assert hasattr(iter_result, '__next__'), "return_iter should return an iterator"


