"""Template scope resolution and lineage-ordering contract tests for story38.

Covers ``StoryGraph38.get_template_scope_groups`` and ``ScriptManager38.get_template_scope_groups``,
validating the fundamental scope guarantee:

    nearest template (block's own template) → parent template (scene)
    → world templates (all others)  — with no cross-scene leakage

These tests are the story38 replacement for the legacy
``test_template_provisioner_scope.py`` and ``test_world_template_registry.py``
modules listed in the parity matrix.

The intent here is *lineage ordering*, not provisioner mechanics.  The VM
provisioner integration lives in ``engine/tests/vm38/test_resolver.py``.

See Also
--------
- ``tangl.story38.story_graph.StoryGraph38.get_template_scope_groups``
- ``tangl.story38.fabula.script_manager38.ScriptManager38.get_template_scope_groups``
- ``tangl.story38.fabula.materializer.StoryMaterializer38``
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tangl.core38 import EntityTemplate, Selector, TemplateRegistry
from tangl.core38.template import TemplateGroup
from tangl.story38 import InitMode, World38
from tangl.story38.concepts import Actor
from tangl.story38.episode import Block, Scene
from tangl.story38.fabula import StoryCompiler38, StoryMaterializer38
from tangl.story38.fabula.script_manager38 import ScriptManager38
from tangl.story38.story_graph import StoryGraph38


# ---------------------------------------------------------------------------
# Shared script builders
# ---------------------------------------------------------------------------

def _multi_scene_script() -> dict:
    """Two scenes (intro, chapter) each with two blocks and an actor each."""
    return {
        "label": "scope_world",
        "metadata": {
            "title": "Scope World",
            "author": "Tests",
            "start_at": "intro.start",
        },
        "actors": {
            "hero": {"name": "Hero"},
            "villain": {"name": "Villain"},
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Intro start.",
                        "actions": [{"text": "Next", "successor": "mid"}],
                    },
                    "mid": {"content": "Intro mid."},
                }
            },
            "chapter": {
                "blocks": {
                    "open": {"content": "Chapter open."},
                    "close": {"content": "Chapter close."},
                }
            },
        },
    }


def _world_and_graph(script: dict | None = None, *, story_label: str = "scope_story"):
    """Return (world, StoryInitResult) for EAGER initialization."""
    w = World38.from_script_data(script_data=script or _multi_scene_script())
    result = w.create_story(story_label, init_mode=InitMode.EAGER)
    return w, result


# ---------------------------------------------------------------------------
# ScriptManager38 scope-group ordering
# ---------------------------------------------------------------------------

class TestScriptManager38ScopeGroups:
    """ScriptManager38.get_template_scope_groups returns lineage-ordered groups."""

    def test_own_template_appears_in_first_group(self) -> None:
        _, result = _world_and_graph()
        graph = result.graph
        cursor = graph.get(graph.initial_cursor_id)
        assert cursor is not None

        groups = graph.get_template_scope_groups(cursor)

        assert groups
        first_group_labels = {
            getattr(item, "label", getattr(item, "get_label", lambda: None)())
            for item in groups[0]
        }
        # The cursor's own template (intro.start) should lead
        own_tmpl_uid = graph.template_by_entity_id.get(cursor.uid)
        own_tmpl = graph.factory.get(own_tmpl_uid) if own_tmpl_uid else None
        if own_tmpl is not None:
            assert own_tmpl.get_label() in first_group_labels or own_tmpl in groups[0]

    def test_all_registry_templates_appear_in_some_group(self) -> None:
        _, result = _world_and_graph()
        graph = result.graph
        cursor = graph.get(graph.initial_cursor_id)

        groups = graph.get_template_scope_groups(cursor)
        flat = {
            getattr(item, "uid", None)
            for group in groups
            for item in group
        }
        for tmpl in graph.factory.values():
            assert tmpl.uid in flat, f"Template {tmpl.get_label()} missing from scope groups"

    def test_cursor_lineage_heads_precede_global_pool(self) -> None:
        _, result = _world_and_graph()
        graph = result.graph
        cursor = graph.get(graph.initial_cursor_id)
        lineage = graph.template_lineage_by_entity_id.get(cursor.uid, [])

        groups = graph.get_template_scope_groups(cursor)
        group_heads = [
            getattr(group[0], "uid", None) for group in groups if group
        ]
        # The lineage ids should appear as group heads, in order, before any
        # group head that is *not* in the lineage.
        lineage_set = set(lineage)
        lineage_head_positions = [i for i, uid in enumerate(group_heads) if uid in lineage_set]
        non_lineage_positions = [i for i, uid in enumerate(group_heads) if uid not in lineage_set]
        if lineage_head_positions and non_lineage_positions:
            assert max(lineage_head_positions) < min(non_lineage_positions)

    def test_no_cross_scene_template_appears_before_own_scene_templates(self) -> None:
        """Templates from 'chapter' scene should not precede 'intro' templates for intro.start cursor."""
        _, result = _world_and_graph()
        graph = result.graph
        cursor = graph.get(graph.initial_cursor_id)
        assert cursor.label == "start"

        groups = graph.get_template_scope_groups(cursor)
        flat_labels = [
            getattr(item, "label", getattr(item, "get_label", lambda: "")())
            for group in groups
            for item in group
        ]
        # 'intro.start' or 'intro' must appear before 'chapter.open' or 'chapter'
        intro_pos = next(
            (i for i, lbl in enumerate(flat_labels) if "intro" in str(lbl)), None
        )
        chapter_pos = next(
            (i for i, lbl in enumerate(flat_labels) if "chapter" in str(lbl)), None
        )
        if intro_pos is not None and chapter_pos is not None:
            assert intro_pos <= chapter_pos

    def test_scope_groups_contain_no_duplicates(self) -> None:
        _, result = _world_and_graph()
        graph = result.graph
        cursor = graph.get(graph.initial_cursor_id)

        groups = graph.get_template_scope_groups(cursor)
        seen: set = set()
        for group in groups:
            for item in group:
                uid = getattr(item, "uid", id(item))
                assert uid not in seen, f"Duplicate item in scope groups: {item}"
                seen.add(uid)

    def test_different_cursors_get_different_lineage_heads(self) -> None:
        """Cursor at 'start' vs cursor at 'open' have different template lineages."""
        _, result = _world_and_graph()
        graph = result.graph

        start = next(
            n for n in graph.values()
            if isinstance(n, Block) and n.label == "start"
        )
        open_block = next(
            n for n in graph.values()
            if isinstance(n, Block) and n.label == "open"
        )

        start_groups = graph.get_template_scope_groups(start)
        open_groups = graph.get_template_scope_groups(open_block)

        start_first = {getattr(i, "uid", None) for i in (start_groups[0] if start_groups else [])}
        open_first = {getattr(i, "uid", None) for i in (open_groups[0] if open_groups else [])}

        # The leading groups should differ (different lineages)
        assert start_first != open_first


# ---------------------------------------------------------------------------
# World scope provider integration
# ---------------------------------------------------------------------------

class TestWorldScopeProviderIntegration:
    """World-contributed template groups appear in resolved scope groups."""

    def test_world_extra_templates_appear_in_scope(self) -> None:
        @dataclass(slots=True)
        class _FakeFacet:
            extra: TemplateRegistry

            def get_template_scope_groups(self, *, caller=None, graph=None):
                return [list(self.extra.values())]

        base_world = World38.from_script_data(script_data=_multi_scene_script())
        extra_reg = TemplateRegistry(label="extra")
        extra_tmpl = EntityTemplate(
            label="world.extra.npc",
            payload=Actor(label="npc", name="NPC"),
            registry=extra_reg,
        )
        _ = extra_tmpl

        world = World38(
            label=base_world.label,
            bundle=base_world.bundle,
            templates=_FakeFacet(extra=extra_reg),
        )
        result = world.create_story("world_scope_story", init_mode=InitMode.EAGER)
        cursor = result.graph.get(result.graph.initial_cursor_id)
        groups = result.graph.get_template_scope_groups(cursor)

        all_labels = {
            getattr(item, "label", None)
            for group in groups
            for item in group
        }
        assert "world.extra.npc" in all_labels


# ---------------------------------------------------------------------------
# ScriptManager38 standalone unit tests
# ---------------------------------------------------------------------------

class TestScriptManager38Standalone:
    """ScriptManager38 scope-group logic in isolation (no world fixture)."""

    def _minimal_registry(self) -> tuple[TemplateRegistry, EntityTemplate, EntityTemplate]:
        reg = TemplateRegistry(label="test_reg")
        scene_tmpl = TemplateGroup(
            label="scene_a",
            payload=Scene(label="scene_a"),
            registry=reg,
        )
        block_tmpl = TemplateGroup(
            label="scene_a.block_1",
            payload=Block(label="block_1"),
            registry=reg,
        )
        scene_tmpl.add_child(block_tmpl)
        return reg, scene_tmpl, block_tmpl

    def test_lineage_ids_produce_first_groups(self) -> None:
        reg, scene_tmpl, block_tmpl = self._minimal_registry()
        sm = ScriptManager38(template_registry=reg)

        caller = Block(label="block_1")
        groups = sm.get_template_scope_groups(
            caller=caller,
            lineage_ids=[block_tmpl.uid, scene_tmpl.uid],
        )

        assert groups
        first_uid = getattr(groups[0][0], "uid", None)
        assert first_uid == block_tmpl.uid

    def test_empty_lineage_returns_flat_pool(self) -> None:
        reg, _scene, _block = self._minimal_registry()
        sm = ScriptManager38(template_registry=reg)

        groups = sm.get_template_scope_groups(caller=None, lineage_ids=[])

        assert groups
        all_uids = {getattr(i, "uid", None) for group in groups for i in group}
        for tmpl in reg.values():
            assert tmpl.uid in all_uids

    def test_find_template_by_label(self) -> None:
        reg, scene_tmpl, block_tmpl = self._minimal_registry()
        sm = ScriptManager38(template_registry=reg)

        found = sm.find_template("scene_a.block_1")
        assert found is not None
        assert found.uid == block_tmpl.uid

    def test_find_template_returns_none_for_unknown(self) -> None:
        reg, _, _ = self._minimal_registry()
        sm = ScriptManager38(template_registry=reg)

        assert sm.find_template("nonexistent.block") is None

    def test_find_templates_with_selector(self) -> None:
        reg, scene_tmpl, block_tmpl = self._minimal_registry()
        sm = ScriptManager38(template_registry=reg)

        results = sm.find_templates(Selector(has_payload_kind=Block))
        labels = {r.get_label() for r in results}
        assert "scene_a.block_1" in labels
        assert "scene_a" not in labels
