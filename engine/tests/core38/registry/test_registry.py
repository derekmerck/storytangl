"""Contract tests for ``tangl.core38.registry`` classes."""

from __future__ import annotations

import pickle
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tangl.core38.dispatch import on_add_item, on_get_item, on_remove_item
from tangl.core38.entity import Entity
from tangl.core38.registry import EntityGroup, HierarchicalGroup, Registry, RegistryAware
from tangl.core38.selector import Selector


class TrackedEntity(RegistryAware):
    value: int = 0


class SimpleGroup(EntityGroup):
    pass


class NestedGroup(HierarchicalGroup):
    pass


class TestRegistryCRUD:
    def test_add_and_get(self) -> None:
        reg = Registry()
        item = Entity(label="a")
        reg.add(item)
        assert reg.get(item.uid) is item

    def test_add_overwrites_duplicate_uid(self) -> None:
        reg = Registry()
        uid = uuid4()
        first = Entity(uid=uid, label="one")
        second = Entity(uid=uid, label="two")
        reg.add(first)
        reg.add(second)
        assert reg.get(uid) is second

    def test_remove_missing_key(self) -> None:
        reg = Registry()
        reg.remove(uuid4())
        assert len(reg) == 0

    def test_mapping_dunder_helpers(self) -> None:
        reg = Registry()
        item = Entity(label="x")
        reg.add(item)
        assert reg[item.uid] is item
        del reg[item.uid]
        assert reg.get(item.uid) is None

    def test_setitem_raises(self) -> None:
        reg = Registry()
        with pytest.raises(KeyError):
            reg[uuid4()] = Entity()


class TestRegistrySelection:
    def test_find_all_and_find_one(self) -> None:
        reg = Registry()
        a = Entity(label="a")
        b = Entity(label="b")
        reg.add(a)
        reg.add(b)
        assert list(reg.find_all(Selector(label="a"))) == [a]
        assert reg.find_one(Selector(label="b")) is b

    def test_find_all_no_selector_yields_all(self) -> None:
        reg = Registry()
        items = [Entity(label="a"), Entity(label="b")]
        for item in items:
            reg.add(item)
        assert list(reg.find_all()) == items

    def test_chain_find_all_across_registries(self) -> None:
        left = Registry()
        right = Registry()
        a = Entity(label="x")
        b = Entity(label="x")
        left.add(a)
        right.add(b)
        result = list(Registry.chain_find_all(left, right, selector=Selector(label="x")))
        assert result == [a, b]

    def test_all_labels(self) -> None:
        reg = Registry()
        reg.add(Entity(label="a"))
        reg.add(Entity(label="b"))
        assert reg.all_labels() == {"a", "b"}


class TestRegistrySerialization:
    def test_unstructure_includes_members(self) -> None:
        reg = Registry(label="r")
        reg.add(Entity(label="x"))
        data = reg.unstructure()
        assert data["label"] == "r"
        assert len(data["members"]) == 1

    def test_structure_roundtrip(self) -> None:
        reg = Registry(label="r")
        reg.add(Entity(label="x"))
        restored = Registry.structure(reg.unstructure())
        assert restored == reg

    def test_pickle_roundtrip(self) -> None:
        reg = Registry(label="r")
        reg.add(Entity(label="x"))
        restored = pickle.loads(pickle.dumps(reg))
        assert restored == reg


class TestRegistryDispatchHooks:
    def test_add_with_ctx_fires_hook(self, null_ctx: SimpleNamespace) -> None:
        on_add_item(func=lambda *, item, **_: item.evolve(label="mutated"))
        reg = Registry()
        item = Entity(label="original")
        reg.add(item, _ctx=null_ctx)
        assert reg.get(item.uid).label == "mutated"

    def test_get_with_ctx_fires_hook(self, null_ctx: SimpleNamespace) -> None:
        on_get_item(func=lambda *, item, **_: item.evolve(label="fetched"))
        reg = Registry()
        item = Entity(label="original")
        reg.add(item)
        assert reg.get(item.uid, _ctx=null_ctx).label == "fetched"

    def test_remove_with_ctx_fires_hook(self, null_ctx: SimpleNamespace) -> None:
        called = {"seen": False}

        def mark(*, item, **_):
            called["seen"] = item is not None

        on_remove_item(func=mark)
        reg = Registry()
        item = Entity(label="x")
        reg.add(item)
        reg.remove(item.uid, _ctx=null_ctx)
        assert called["seen"] is True


class TestRegistryAwareAndGroups:
    def test_bind_and_unbind_registry(self) -> None:
        reg = Registry()
        item = TrackedEntity(label="x")
        reg.add(item)
        assert item.registry is reg
        reg.remove(item.uid)
        assert item.registry is None

    def test_rebind_raises(self) -> None:
        first = Registry()
        second = Registry()
        item = TrackedEntity(label="x")
        first.add(item)
        with pytest.raises(ValueError):
            second.add(item)

    def test_validate_linkable_uses_registry_identity(self) -> None:
        reg1 = Registry()
        reg2 = Registry()
        item = TrackedEntity(label="x")
        reg1.add(item)
        with pytest.raises(ValueError):
            reg2._validate_linkable(item)

    def test_entity_group_membership(self) -> None:
        reg = Registry()
        a = TrackedEntity(label="a")
        b = TrackedEntity(label="b")
        group = SimpleGroup(label="g")
        reg.add(a)
        reg.add(b)
        reg.add(group)
        group.add_members(a, b)
        assert list(group.members()) == [a, b]
        assert group.has_member(a)
        group.remove_member(a)
        assert not group.has_member(a)

    def test_group_members_requires_registry(self) -> None:
        group = SimpleGroup(label="g")
        with pytest.raises(ValueError):
            list(group.members())

    def test_hierarchical_group_reparenting_and_path(self) -> None:
        reg = Registry()
        root = NestedGroup(label="root", registry=reg)
        left = NestedGroup(label="left", registry=reg)
        right = NestedGroup(label="right", registry=reg)

        root.add_child(left)
        assert left.parent is root
        assert left.path == "root.left"

        right.add_child(left)
        assert left.parent is right
        assert left.path == "right.left"
        assert left.ancestors == [left, right]
        assert left.root is right

    def test_parent_cache_invalidation_on_remove(self) -> None:
        reg = Registry()
        parent = NestedGroup(label="p", registry=reg)
        child = TrackedEntity(label="c", registry=reg)
        parent.add_child(child)
        assert child.parent is parent
        parent.remove_child(child)
        assert child.parent is None
