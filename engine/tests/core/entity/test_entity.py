"""Contract tests for ``tangl.core.entity.Entity``.

.. storytangl-topic::
   :topics: entity
   :facets: tests
   :relation: tests
"""

from __future__ import annotations

import pickle
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import Field

from tangl.core.bases import HasIdentity, Unstructurable
from tangl.core.ctx import using_ctx
from tangl.core.dispatch import on_create, on_init
from tangl.core.entity import Entity


class EntityWithAttrib(Entity):
    """Entity subclass used in composition and serialization tests."""

    foo: int = 0


class EntityWithMutableState(Entity):
    """Entity with a marked vs. unmarked mutable collection field.

    ``marked`` opts into snapshot persistence via
    ``json_schema_extra={"include": True}``; ``unmarked`` does not, and exists
    to document the boundary the marker is for.
    """

    marked: set[str] = Field(default_factory=set, json_schema_extra={"include": True})
    unmarked: set[str] = Field(default_factory=set)


class TestEntityComposition:
    """Entity composition and equality semantics."""

    def test_entity_is_unstructurable(self) -> None:
        assert isinstance(Entity(), Unstructurable)

    def test_entity_is_has_identity(self) -> None:
        assert isinstance(Entity(), HasIdentity)

    def test_eq_is_by_value(self) -> None:
        uid = uuid4()
        left = Entity(uid=uid, label="a")
        right = Entity(uid=uid, label="b")
        assert left.eq_by_id(right)
        assert left != right

    def test_same_uid_same_data_equal(self) -> None:
        uid = uuid4()
        left = Entity(uid=uid, label="a")
        right = Entity(uid=uid, label="a")
        assert left == right

    def test_different_uid_not_equal(self) -> None:
        left = Entity(label="same")
        right = Entity(label="same")
        assert left != right

    def test_entity_not_hashable(self) -> None:
        with pytest.raises(TypeError):
            hash(Entity())

    def test_entity_equal_to_itself(self) -> None:
        entity = Entity(label="self")
        assert entity == entity

    def test_subclass_with_same_uid_not_equal(self) -> None:
        uid = uuid4()
        base = Entity(uid=uid, label="a")
        sub = EntityWithAttrib(uid=uid, label="a", foo=0)
        assert base != sub


class TestEntityCreation:
    """Entity constructor behavior."""

    def test_basic_creation(self) -> None:
        entity = Entity()
        assert entity.uid is not None
        assert entity.tags == set()

    def test_creation_with_label(self) -> None:
        entity = Entity(label="my test node")
        assert entity.label == "my test node"

    def test_creation_with_tags(self) -> None:
        entity = Entity(tags=["x", "y", "x"])
        assert entity.tags == {"x", "y"}

    def test_subclass_creation(self) -> None:
        entity = EntityWithAttrib(foo=42)
        assert entity.foo == 42

    def test_uid_is_unique(self) -> None:
        assert Entity().uid != Entity().uid

    def test_templ_hash_defaults_to_none(self) -> None:
        assert Entity().templ_hash is None


class TestEntitySerialization:
    """Entity structuring and persistence-shape behavior."""

    def test_unstructure_includes_kind(self) -> None:
        entity = Entity(label="x")
        data = entity.unstructure()
        assert data["kind"] is Entity

    def test_unstructure_includes_uid(self) -> None:
        entity = Entity()
        assert entity.unstructure()["uid"] == entity.uid

    def test_unstructure_excludes_defaults(self) -> None:
        data = Entity().unstructure()
        assert "label" not in data
        assert "tags" not in data

    def test_structure_roundtrip(self) -> None:
        entity = Entity(label="x", tags={"a"})
        restored = Entity.structure(entity.unstructure())
        assert restored == entity

    def test_structure_resolves_kind_to_subclass(self) -> None:
        entity = EntityWithAttrib(foo=9, label="x")
        restored = Entity.structure(entity.unstructure())
        assert isinstance(restored, EntityWithAttrib)
        assert restored.foo == 9

    def test_structure_with_string_kind_raises(self) -> None:
        with pytest.raises(TypeError):
            Entity.structure({"kind": "Entity", "label": "x"})

    def test_tags_roundtrip_set_list_set(self) -> None:
        entity = Entity(tags={"a", "b"})
        data = entity.unstructure()
        restored = Entity.structure(data)
        assert restored.tags == {"a", "b"}

    def test_pickle_roundtrip(self) -> None:
        entity = EntityWithAttrib(label="x", foo=3)
        restored = pickle.loads(pickle.dumps(entity))
        assert restored == entity

    def test_evolve_preserves_uid(self) -> None:
        entity = Entity(label="v1")
        evolved = entity.evolve(label="v2")
        assert evolved.uid == entity.uid

    def test_evolve_changes_field(self) -> None:
        entity = Entity(label="v1")
        evolved = entity.evolve(label="v2")
        assert evolved.label == "v2"


class TestIncludeMarkerRoundTrip:
    """`json_schema_extra={"include": True}` snapshot-fidelity contract.

    Regression for the ``exclude_unset`` footgun: a field that starts at its
    default and is then mutated *in place* (never reassigned) must still
    survive ``unstructure()``/``structure()`` when marked ``include=True``.
    """

    def test_in_place_mutated_marked_field_round_trips(self) -> None:
        entity = EntityWithMutableState()
        entity.marked.add("acquired")  # in place; field never reassigned

        data = entity.unstructure()
        assert data["marked"] == {"acquired"}

        restored = Entity.structure(data)
        assert restored.marked == {"acquired"}

    def test_default_marked_field_is_still_elided(self) -> None:
        # No chumming: an untouched marked field stays out of the snapshot.
        data = EntityWithMutableState().unstructure()
        assert "marked" not in data

    def test_unmarked_in_place_mutation_is_dropped(self) -> None:
        # Documents the boundary: without the marker, in-place mutation is
        # lost (this is exactly the footgun the marker exists to close).
        entity = EntityWithMutableState()
        entity.unmarked.add("ghost")

        restored = Entity.structure(entity.unstructure())
        assert restored.unmarked == set()

    def test_marker_does_not_resurrect_excluded_fields(self) -> None:
        entity = EntityWithMutableState()
        entity.marked.add("kept")
        restored = Entity.structure(entity.unstructure())
        assert restored.marked == {"kept"}
        assert restored.unmarked == set()


class TestEntityDispatchHooks:
    """Entity launch-point dispatch contract tests."""

    def test_init_without_ctx_no_dispatch(self) -> None:
        on_init(func=lambda *, caller, **_: setattr(caller, "label", "mutated"))
        entity = Entity(label="original")
        assert entity.label == "original"

    def test_init_with_ctx_fires_do_init(self, null_ctx: SimpleNamespace) -> None:
        on_init(func=lambda *, caller, **_: setattr(caller, "label", "mutated"))
        entity = Entity(label="original", _ctx=null_ctx)
        assert entity.label == "mutated"

    def test_init_with_ambient_ctx(self) -> None:
        calls = {"registries": 0}

        def get_authorities() -> list[object]:
            calls["registries"] += 1
            return []

        ctx = SimpleNamespace(
            get_authorities=get_authorities,
            get_inline_behaviors=lambda: [],
        )
        with using_ctx(ctx):
            _ = Entity(label="original")
        assert calls["registries"] == 1

    def test_structure_without_ctx_no_dispatch(self) -> None:
        on_create(func=lambda *, data, **_: {"label": "mutated"})
        created = Entity.structure({"label": "original"})
        assert created.label == "original"

    def test_structure_with_ctx_fires_do_create(self, null_ctx: SimpleNamespace) -> None:
        on_create(func=lambda *, data, **_: {"label": "mutated"})
        created = Entity.structure({"label": "original"}, _ctx=null_ctx)
        assert created.label == "mutated"

    def test_create_hook_can_override_kind(self, null_ctx: SimpleNamespace) -> None:
        on_create(func=lambda *, data, **_: {"kind": EntityWithAttrib, "foo": 7})
        created = Entity.structure({"label": "x"}, _ctx=null_ctx)
        assert isinstance(created, EntityWithAttrib)
        assert created.foo == 7

    def test_dispatch_chains_global_and_ctx_registries(
        self,
        mock_ctx_with_registry: tuple[SimpleNamespace, object],
    ) -> None:
        ctx, registry = mock_ctx_with_registry
        on_init(func=lambda *, caller, **_: caller.tags.add("global"))
        registry.register(task="init", func=lambda *, caller, **_: caller.tags.add("ctx"))
        entity = Entity(label="x", _ctx=ctx)
        assert entity.has_tags("global", "ctx")

    def test_ctx_without_get_authorities_is_graceful(self) -> None:
        bad_ctx = SimpleNamespace(get_inline_behaviors=lambda: [])
        entity = Entity(label="x", _ctx=bad_ctx)
        assert entity.label == "x"
