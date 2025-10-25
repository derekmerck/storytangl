import pytest

from tangl.core import Available, HasScopedContext, Node

pytest.skip(allow_module_level=True, reason="Not sure how inherited availability is supposed to work yet")

# ---------------
# Availability
# ---------------

class TestAvailabilityNode(Available, HasScopedContext, Node):
    ...


def test_lock_unlock():
    node = TestAvailabilityNode()

    assert node.available() is True

    node.lock()
    assert node.available() is False

    node.unlock()
    assert node.available() is True


def test_available_no_children():
    node = TestAvailabilityNode()
    assert node.available()

def test_available_all_children_unlocked():
    parent = TestAvailabilityNode(label="parent")
    child1 = TestAvailabilityNode(label="child1")
    child2 = TestAvailabilityNode(label="child2")
    parent.add_child(child1)
    parent.add_child(child2)
    assert parent.available()
    assert child1.available()
    assert child2.available()

def test_available_parent_locked():
    parent = TestAvailabilityNode(label="parent", locked=True)
    child1 = TestAvailabilityNode(label="child1")
    parent.add_child(child1)
    assert not parent.available()
    assert not child1.available()

def test_available_children_locked():
    parent = TestAvailabilityNode(label="parent")
    child1 = TestAvailabilityNode(label="child1", locked=True)
    child2 = TestAvailabilityNode(label="child2")
    parent.add_child(child1)
    parent.add_child(child2)
    assert parent.available()
    assert not child1.available()
    assert child2.available()

def test_force_unlock_parent1():
    root = TestAvailabilityNode()
    child = TestAvailabilityNode()

    root.add_child(child)
    child.lock()
    assert child.available() is False

    root.unlock(True)
    assert root.forced
    assert child.available() is True

    child.lock()
    assert child.available() is True  # Here, force unlock has overridden lock state

def test_force_unlock_parent2():
    root = TestAvailabilityNode()
    node1 = TestAvailabilityNode()
    node2 = TestAvailabilityNode()

    root.add_child(node1)
    node1.add_child(node2)

    node1.lock()
    node2.lock()

    assert node1.available() is False
    assert node2.available() is False

    root.unlock(True)

    assert node1.available() is True
    assert node2.available() is True

def test_force_unlock_child():
    parent = TestAvailabilityNode(label="parent", locked=True)
    child1 = TestAvailabilityNode(label="child1", locked=True)
    child2 = TestAvailabilityNode(label="child2", locked=True)
    parent.add_child(child1)
    parent.add_child(child2)
    child1.unlock(force=True)
    assert not parent.available()
    # todo: should forced propagate up as well?  It probably doesn't matter b/c
    #       forcing a scene open on enter will force all of the blocks.
    assert child1.available()
    assert not child2.available()

def test_available_grandparent_locked():
    grandparent = TestAvailabilityNode(label="grandparent", locked=True)
    parent = TestAvailabilityNode(label="parent")
    grandparent.add_child(parent)
    child = TestAvailabilityNode(label="child")
    parent.add_child(child)
    assert not grandparent.available()
    assert not parent.available()
    assert not child.available()

def test_force_unlock_grandparent():
    root = TestAvailabilityNode()
    node1 = TestAvailabilityNode()
    node2 = TestAvailabilityNode()

    root.add_child(node1)
    node1.add_child(node2)

    node1.lock()
    node2.lock()

    assert node1.available() is False
    assert node2.available() is False

    node1.unlock(True)

    assert root.available() is True
    assert node1.available() is True
    assert node2.available() is True
