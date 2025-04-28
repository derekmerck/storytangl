import pytest

pytest.skip(allow_module_level=True)

from tangl.core.entity import Entity
from tangl.core.entity_handlers import Available, HasConditions, HasContext, on_check_conditions, on_gather_context

MyAvailEntity = type('MyAvailEntity', (Available, Entity), {} )


# CONDITIONAL AVAILABILITY

def test_conditional_availability():
    entity = TestConditionalLockableEntity(
        conditions=["condition_met == True"],
        locals={"condition_met": False}
    )
    assert AvailabilityHandler.available(entity) is False, "Entity should be unavailable when condition is False"
    assert not entity.available()

    # Update namespace to meet the condition
    entity.locals['condition_met'] = True
    assert AvailabilityHandler.available(entity) is True, "Entity should be available when condition is True"
    assert entity.available()


def test_conditional_availability2():
    n = TestConditionalLockableEntity( locals={'abc': 'foo'}, conditions=["abc == 'foo'"])
    result = n.check_conditions()
    assert result

    # lock the node
    assert n.available()
    n.locked = True
    assert not n.available()


def test_combined_availability_strategies():
    entity = TestConditionalLockableEntity(
        conditions=["condition_met == True"],
        locals={"condition_met": False},
    )
    assert not entity.locked
    assert not entity.available(), "Entity is unlocked but should be unavailable due to unmet condition"

    # Now, meet the condition
    entity.locals['condition_met'] = True
    assert entity.available(), "Entity is unlocked and should be available given met condition"

    # Now lock the entity
    entity.locked = True
    assert not entity.available(), "Entity should become unavailable due to being locked"


def test_conditional_fail():

    n = TestConditionalLockableEntity( locals={'abc': 'foo'}, conditions=["abc == 'foo123'"])
    result = n.check_conditions()
    assert not result

    assert not n.available()

    # update the conditions
    n.conditions = ["True"]
    result = n.check_conditions()
    assert result

    assert n.available()
    n.locked = True
    assert not n.available()


