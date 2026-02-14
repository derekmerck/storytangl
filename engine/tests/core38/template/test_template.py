"""Contract tests for ``tangl.core38.template``."""

from __future__ import annotations

from typing import Iterator

import pytest
from pydantic import ValidationError

from tangl.core38.entity import Entity
from tangl.core38.selector import Selector
from tangl.core38.template import EntityTemplate, Snapshot, TemplateGroup, TemplateRegistry

from ..conftest import Block, Scene, SpecialScene


class TestEntityTemplateCreation:
    def test_from_entity(self) -> None:
        entity = Scene(label="scene-a", location="forest")
        templ = EntityTemplate.from_entity(entity)
        assert templ.payload.label == "scene-a"

    def test_from_entity_payload_is_copy(self) -> None:
        entity = Scene(label="scene-a")
        templ = EntityTemplate.from_entity(entity)
        assert templ.payload is not entity

    def test_from_data_with_default_kind(self) -> None:
        templ = EntityTemplate.from_data({"label": "scene-a"}, default_kind=Scene)
        assert isinstance(templ.payload, Scene)

    def test_from_data_without_kind_defaults_to_entity(self) -> None:
        templ = EntityTemplate.from_data({"label": "plain"})
        assert isinstance(templ.payload, Entity)

    def test_from_data_does_not_mutate_input(self) -> None:
        payload = {"label": "scene-a"}
        EntityTemplate.from_data(payload, default_kind=Scene)
        assert payload == {"label": "scene-a"}

    def test_payload_field_excluded_from_model_dump(self) -> None:
        templ = EntityTemplate.from_data({"label": "scene-a"}, default_kind=Scene)
        assert "payload" not in templ.model_dump()

    def test_get_label_from_template(self) -> None:
        templ = EntityTemplate(label="templ", payload=Scene(label="scene-a"))
        assert templ.get_label() == "templ"

    def test_get_label_fallback_to_payload(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.get_label() == "from-scene-a"


class TestEntityTemplateMatching:
    def test_has_kind_matches_template_type(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.has_kind(EntityTemplate)

    def test_has_kind_matches_payload_type(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.has_kind(Scene)

    def test_has_kind_rejects_wrong_type(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert not templ.has_kind(Block)

    def test_has_template_kind(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.has_template_kind(EntityTemplate)

    def test_has_payload_kind(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.has_payload_kind(Scene)

    def test_has_tags_union(self) -> None:
        templ = EntityTemplate(tags={"templ"}, payload=Scene(label="scene-a", tags={"scene"}))
        assert templ.has_tags("templ", "scene")

    def test_has_tags_single_set_arg(self) -> None:
        templ = EntityTemplate(tags={"templ"}, payload=Scene(label="scene-a", tags={"scene"}))
        assert templ.has_tags({"templ", "scene"})

    def test_get_identifiers_union(self) -> None:
        templ = EntityTemplate(label="templ", payload=Scene(label="scene-a"))
        ids = templ.get_identifiers()
        assert "templ" in ids and "scene-a" in ids

    def test_selector_finds_by_payload_kind(self) -> None:
        reg = TemplateRegistry()
        scene = EntityTemplate(payload=Scene(label="scene-a"))
        block = EntityTemplate(payload=Block(label="block-a"))
        reg.add(scene)
        reg.add(block)
        assert list(reg.find_all(Selector(has_payload_kind=Scene))) == [scene]


class TestEntityTemplateMaterialize:
    def test_materialize_creates_entity(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        ent = templ.materialize()
        assert isinstance(ent, Scene)

    def test_materialize_fresh_uid(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.materialize().uid != templ.payload.uid

    def test_materialize_preserves_uid(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.materialize(preserve_uid=True).uid == templ.payload.uid

    def test_materialize_with_updates(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        ent = templ.materialize(label="scene-b")
        assert ent.label == "scene-b"

    def test_materialize_kind_narrowing(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        ent = templ.materialize(kind=SpecialScene, difficulty=5)
        assert isinstance(ent, SpecialScene)
        assert ent.difficulty == 5

    def test_materialize_kind_widening_raises(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        with pytest.raises(TypeError, match="must be a subclass"):
            templ.materialize(kind=Block)

    def test_materialize_does_not_mutate_payload(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        _ = templ.materialize(label="scene-b")
        assert templ.payload.label == "scene-a"


class TestEntityTemplateCompileDecompileSerialization:
    def test_compile_from_dict(self) -> None:
        templ = EntityTemplate.compile({"label": "scene-a", "kind": Scene})
        assert isinstance(templ.payload, Scene)

    def test_decompile_strips_uid_and_seq(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        data = templ.decompile()
        assert "uid" not in data and "seq" not in data

    def test_decompile_strips_redundant_entity_kind(self) -> None:
        templ = EntityTemplate(payload=Entity(label="plain"))
        assert "kind" not in templ.decompile()

    def test_decompile_preserves_specific_kind(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.decompile()["kind"] is Scene

    def test_unstructure_structure_roundtrip(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a", location="cave"))
        restored = EntityTemplate.structure(templ.unstructure())
        assert restored == templ

    def test_content_hash_from_payload(self) -> None:
        templ = EntityTemplate(payload=Scene(label="scene-a"))
        assert templ.get_hashable_content() == templ.payload.unstructure()


class TestSnapshot:
    def test_materialize_preserves_uid(self) -> None:
        entity = Scene(label="scene-a")
        snap = Snapshot.from_entity(entity)
        copy = snap.materialize()
        assert copy.uid == entity.uid

    def test_materialize_rejects_updates(self) -> None:
        snap = Snapshot.from_entity(Scene(label="scene-a"))
        with pytest.raises(TypeError):
            snap.materialize(label="scene-b")

    def test_materialize_rejects_preserve_uid_false(self) -> None:
        snap = Snapshot.from_entity(Scene(label="scene-a"))
        with pytest.raises(TypeError):
            snap.materialize(preserve_uid=False)


class TestTemplateGroupAndRegistry:
    def test_template_group_compile_yields_depth_first(self) -> None:
        script = {
            "label": "chapter",
            "members": [
                {"label": "scene-1", "members": [{"label": "block-1"}]},
                {"label": "scene-2"},
            ],
        }
        items = list(TemplateGroup.compile(script))
        labels = [item.payload.label for item in items]
        assert labels == ["block-1", "scene-1", "scene-2", "chapter"]

    def test_template_group_decompile_roundtrip(self) -> None:
        script = [
            {
                "label": "chapter-1",
                "members": [
                    {"label": "scene-1.1", "members": [{"label": "block-1.1.1"}]},
                    {"label": "scene-1.2"},
                ],
            }
        ]
        reg = TemplateRegistry.compile(script)
        assert reg.decompile_all() == script

    def test_template_registry_materialize_one(self) -> None:
        reg = TemplateRegistry()
        reg.add(EntityTemplate.from_data({"label": "scene-a", "kind": Scene}))
        assert isinstance(reg.materialize_one(Selector(has_payload_kind=Scene)), Scene)

    def test_template_registry_materialize_one_not_found(self) -> None:
        reg = TemplateRegistry()
        assert reg.materialize_one(Selector(label="missing")) is None

    def test_template_registry_materialize_all(self) -> None:
        reg = TemplateRegistry()
        reg.add(EntityTemplate.from_data({"label": "a", "kind": Scene}))
        reg.add(EntityTemplate.from_data({"label": "b", "kind": Block}))
        mats = list(reg.materialize_all())
        assert len(mats) == 2

    def test_template_registry_compile_mixed_groups_and_leaves(self) -> None:
        script = [
            {"label": "group", "members": [{"label": "leaf"}]},
            {"label": "plain-leaf"},
        ]
        reg = TemplateRegistry.compile(script)
        assert isinstance(reg, TemplateRegistry)
        assert len(reg) == 3

    def test_template_registry_decompile_all_returns_top_level_groups(self) -> None:
        script = [{"label": "group", "members": [{"label": "leaf"}]}]
        reg = TemplateRegistry.compile(script)
        assert reg.decompile_all() == script

    def test_template_group_member_defaults_field(self) -> None:
        grp = TemplateGroup(payload=Scene(label="group"), member_defaults={"kind": Scene})
        assert grp.member_defaults == {"kind": Scene}
