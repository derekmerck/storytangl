from __future__ import annotations
import logging

import pytest

from tangl.core import Entity, Available, HasConditions


logging.basicConfig(level=logging.DEBUG)

TestLockableEntity = type('TestLockableEntity', (Available, Entity), {} )
TestConditionalLockableEntity = type('TestConditionalLockableEntity', (Available, HasConditions, Entity), {} )


def test_lock():
    n = TestLockableEntity(locked=True)
    assert not n.available()
    assert n.locked
    assert not n.forced

    n.unlock()
    assert n.available()
    assert not n.locked
    assert not n.forced

def test_locked_status():
    entity = TestLockableEntity(locked=False)
    assert entity.available(), "Entity should be available when not locked"

    entity.locked = True
    assert not entity.available(), "Entity should be unavailable when locked"

def test_conditional_availability():
    entity = TestConditionalLockableEntity(
        conditions=["condition_met == True"],
        locals={"condition_met": False}
    )
    assert not entity.available(), "Entity should be unavailable when condition is False"

    # Update namespace to meet the condition
    entity.locals['condition_met'] = True
    assert entity.available(), "Entity should be available when condition is True"


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

def test_force_unlock():
    node = TestLockableEntity(locked=True)
    assert node.locked
    assert not node.available()

    node.force()
    assert node.locked, "Should still be locked"
    assert node.forced, "Should be forced open now"
    assert node.available(), "Should be available now"

    node.lock()
    assert node.locked, "Should be able to relock"
    assert node.forced, "Should still be forced"
    assert node.available(), "Should remain available even if relocked"

