from __future__ import annotations
import logging

import pytest

from tangl.core.entity import Entity
from tangl.core.entity.handlers import Lockable, AvailabilityHandler


logging.basicConfig(level=logging.DEBUG)

TestLockableEntity = type('TestLockableEntity', (Lockable, Entity), {} )

def test_baseline():
    n = TestLockableEntity()
    assert n.available()

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
    assert AvailabilityHandler.available(entity) is True, "Entity should be available when not locked"
    assert entity.available(), "Entity should be available when not locked"

    entity.locked = True
    assert AvailabilityHandler.available(entity) is False, "Entity should be unavailable when locked"
    assert not entity.available(), "Entity should be unavailable when locked"

def test_force_unlock():
    node = TestLockableEntity(locked=True)
    assert node.locked
    assert not node.available()

    node.unlock(True)
    assert not node.locked
    assert node.forced
    assert node.available()

    node.lock()
    assert node.locked, "Should be able to relock"
    assert node.forced, "Should still be forced"
    assert node.available(), "Should remain available even if relocked"

