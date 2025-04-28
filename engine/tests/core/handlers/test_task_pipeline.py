from __future__ import annotations

import pytest

from tangl.core import Entity, HandlerPriority, HandlerPipeline, PipelineStrategy

MyPipeline = HandlerPipeline(
    label="MyPipeline",
    pipeline_strategy=PipelineStrategy.GATHER)

class BaseEntity(Entity):

    domain: str = None

    @MyPipeline.register(priority=HandlerPriority.NORMAL)
    def base_process(self: Entity, **kwargs):
        return {"base": "processed"}

class SubEntity(BaseEntity):

    @MyPipeline.register(priority=HandlerPriority.EARLY)
    def sub_process(self: SubEntity, **kwargs):
        return {"sub": "processed"}

class OverrideEntity(BaseEntity):

    @MyPipeline.register(priority=HandlerPriority.LATE)
    def override_process(self: OverrideEntity, **kwargs):
        return {"base": "override"}

    @MyPipeline.register(priority=HandlerPriority.LATE, domain="special_domain")
    def conditional_override_domain(self: OverrideEntity, **kwargs):
        if self.domain:
            return {"domain": "override"}

# class DomainHandler:
#
#     @MyPipeline.register(priority=HandlerPriority.LATE,
#                          domain="special_domain",
#                          caller_cls=BaseEntity)
#     @staticmethod
#     def domain_specific_process(self: Entity, **kwargs):
#         return {"domain": "processed"}


# @pytest.fixture(autouse=True)
# def _reset_domain_handler():
#     StrategyRegistry.discard_instance('special_domain')
#     BaseHandler.register_strategy(
#         DomainEntity.domain_specific_process, 'process', 'special_domain', priority=100)

def test_basic():
    entity = BaseEntity()
    result = MyPipeline.execute(entity)
    print(result)  # Output: {'base': 'processed'}
    assert {'base'} == {*result}

@pytest.mark.xfail(reason="Domain locking not working")
def test_domain():

    entity = BaseEntity(domain="special_domain")
    result = MyPipeline.execute(entity)
    print(result)  # Output: {'base': 'processed', 'domain': 'processed'}
    assert {'base', 'domain'} == {*result}

def test_mro():
    entity = SubEntity()
    result = MyPipeline.execute(entity)
    print(result)  # Output: {'sub': 'processed', 'base': 'processed'}
    assert {'base', 'sub'} == {*result}

@pytest.mark.xfail(reason="Domain locking not working")
def test_mro_and_domain():
    entity = SubEntity(domain="special_domain")
    result = MyPipeline.execute(entity)
    print(result)  # Output: {'domain': 'processed', 'sub': 'processed', 'base': 'processed'}
    assert {'base', 'sub', 'domain'} == {*result}

def test_priority_mro():
    entity = OverrideEntity()
    result = MyPipeline.execute(entity)
    print(result)  # Output: {'base': 'override'}
    assert {'base'} == {*result}
    assert result['base'] == "override"

@pytest.mark.xfail(reason="Domain locking not working")
def test_priority_mro_domain():
    entity = OverrideEntity(domain="special_domain")
    result = MyPipeline.execute(entity)
    print(result)  # Output: {'base': 'override', 'domain': 'processed'}
    assert {'base', 'domain'} == {*result}
    assert result['base'] == "override"
    assert result['domain'] == "override"

def test_return_first_mode():
    entity = SubEntity()
    first_result = MyPipeline.execute(entity, pipeline_strategy="first")
    print(first_result)
    assert isinstance(first_result, dict)
    assert len(first_result) == 1

def test_return_iter():
    entity = SubEntity()
    iter_result = MyPipeline.execute(entity, pipeline_strategy="iter")
    assert hasattr(iter_result, '__next__'), "return_iter should return an iterator"
