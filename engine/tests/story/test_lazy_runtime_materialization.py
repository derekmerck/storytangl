"""Lazy runtime materialization parity and preview regression tests."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

import tangl.story.story_graph as story_graph_module
from tangl.core import Selector
from tangl.media.media_resource import MediaDep
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.story import InitMode, World
from tangl.story.concepts import Role, Setting
from tangl.story.episode import Action, Block, Scene
from tangl.story.fragments import ChoiceFragment, ContentFragment
from tangl.story.system_handlers import render_block
from tangl.vm import Ledger
from tangl.vm.provision import MaterializeRole
from tangl.vm.runtime.frame import PhaseCtx

import tangl.story  # noqa: F401 - ensure story handlers are registered


def _resource_manager(tmp_path: Path) -> ResourceManager:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "cover.svg").write_text(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\"></svg>",
        encoding="utf-8",
    )
    resources = ResourceManager(media_root, scope="world")
    resources.index_directory(".")
    return resources


def _runtime_parity_script() -> dict:
    return {
        "label": "lazy_runtime_parity",
        "metadata": {
            "title": "Lazy Runtime Parity",
            "author": "Tests",
            "start_at": "intro.start",
        },
        "actors": {
            "guard": {
                "name": "Joe",
                "kind": "tangl.story.concepts.actor.actor.Actor",
            }
        },
        "locations": {
            "castle": {
                "name": "Castle",
                "kind": "tangl.story.concepts.location.location.Location",
            }
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Enter", "successor": "middle"}],
                    },
                    "middle": {
                        "content": "Hello {host.name} at {place.name}",
                        "roles": [{"label": "host", "actor_ref": "guard", "hard": True}],
                        "settings": [{"label": "place", "location_ref": "castle", "hard": True}],
                        "media": [{"name": "cover.svg", "text": "Cover", "hard": True}],
                        "actions": [
                            {"text": "Finish", "successor": "end"},
                            {"text": "Back", "successor": "start"},
                        ],
                    },
                    "end": {"content": "End"},
                }
            }
        },
    }


def _entry_only_container_script() -> dict:
    return {
        "label": "lazy_entry_only_container",
        "metadata": {
            "title": "Lazy Entry Only Container",
            "author": "Tests",
            "start_at": "scene1.start",
        },
        "scenes": {
            "scene1": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "scene2"}],
                    }
                }
            },
            "scene2": {
                "blocks": {
                    "entry": {"content": "Entry"},
                    "later": {"content": "Later"},
                }
            },
        },
    }


def _ancestor_scope_script(*, actor_ref: str) -> dict:
    return {
        "label": "lazy_ancestor_scope",
        "metadata": {
            "title": "Lazy Ancestor Scope",
            "author": "Tests",
            "start_at": "scene1.start",
        },
        "actors": {
            "companion": {
                "name": "Mina",
                "kind": "tangl.story.concepts.actor.actor.Actor",
            }
        },
        "scenes": {
            "scene1": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "scene2.entry"}],
                    }
                }
            },
            "scene2": {
                "roles": [{"label": "companion", "actor_ref": actor_ref, "hard": True}],
                "blocks": {
                    "entry": {"content": "Hello {companion.name}"},
                },
            },
        },
    }


def _block(graph, label: str, *, parent: Scene | None = None) -> Block:
    for value in graph.values():
        if not isinstance(value, Block):
            continue
        if value.label != label:
            continue
        if parent is not None and getattr(value.parent, "uid", None) != parent.uid:
            continue
        return value
    raise AssertionError(f"Block not found: {label!r}")


def _scene(graph, label: str) -> Scene:
    for value in graph.values():
        if isinstance(value, Scene) and value.label == label:
            return value
    raise AssertionError(f"Scene not found: {label!r}")


def _choice_action(ledger: Ledger, text: str) -> Action:
    for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)):
        if action.text == text:
            return action
    raise AssertionError(f"Choice action not found: {text!r}")


def _edge_inventory(block: Block) -> dict[str, int]:
    return {
        "actions": len(list(block.edges_out(Selector(has_kind=Action, trigger_phase=None)))),
        "roles": len(list(block.edges_out(Selector(has_kind=Role)))),
        "settings": len(list(block.edges_out(Selector(has_kind=Setting)))),
        "media": len(list(block.edges_out(Selector(has_kind=MediaDep)))),
    }


def test_lazy_leaf_matches_eager_edge_inventory_and_lineage(tmp_path: Path) -> None:
    world = World.from_script_data(
        script_data=_runtime_parity_script(),
        resources=_resource_manager(tmp_path),
    )
    eager = world.create_story("runtime_parity_eager", init_mode=InitMode.EAGER)
    lazy = world.create_story("runtime_parity_lazy", init_mode=InitMode.LAZY)
    ledger = Ledger.from_graph(lazy.graph, entry_id=lazy.graph.initial_cursor_id)

    ledger.resolve_choice(_choice_action(ledger, "Enter").uid)

    eager_middle = _block(eager.graph, "middle")
    lazy_middle = ledger.cursor
    assert isinstance(lazy_middle, Block)
    assert lazy_middle.label == "middle"

    assert _edge_inventory(lazy_middle) == _edge_inventory(eager_middle)
    assert lazy.graph.template_by_entity_id[lazy_middle.uid] == eager.graph.template_by_entity_id[
        eager_middle.uid
    ]
    assert lazy.graph.template_lineage_by_entity_id[lazy_middle.uid] == eager.graph.template_lineage_by_entity_id[
        eager_middle.uid
    ]


def test_lazy_leaf_revisit_does_not_duplicate_wiring(tmp_path: Path) -> None:
    world = World.from_script_data(
        script_data=_runtime_parity_script(),
        resources=_resource_manager(tmp_path),
    )
    result = world.create_story("runtime_parity_revisit", init_mode=InitMode.LAZY)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

    ledger.resolve_choice(_choice_action(ledger, "Enter").uid)
    middle = ledger.cursor
    assert isinstance(middle, Block)
    counts_before = _edge_inventory(middle)

    ledger.resolve_choice(_choice_action(ledger, "Back").uid)
    ledger.resolve_choice(_choice_action(ledger, "Enter").uid)

    assert ledger.cursor.uid == middle.uid
    assert _edge_inventory(ledger.cursor) == counts_before


def test_lazy_bare_container_destination_materializes_entry_only() -> None:
    world = World.from_script_data(script_data=_entry_only_container_script())
    result = world.create_story("entry_only_container", init_mode=InitMode.LAZY)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

    ledger.resolve_choice(_choice_action(ledger, "Go").uid)

    scene2 = _scene(ledger.graph, "scene2")
    children = list(scene2.children())

    assert ledger.cursor.label == "entry"
    assert len(children) == 1
    assert children[0].label == "entry"
    assert scene2.source_id == children[0].uid
    assert scene2.sink_id == children[0].uid
    assert all(child.label != "later" for child in children)
    assert not any(
        isinstance(value, Block)
        and value.label == "later"
        and getattr(value.parent, "uid", None) == scene2.uid
        for value in ledger.graph.values()
    )


def test_lazy_cross_container_arrival_resolves_ancestor_scope_before_journal() -> None:
    world = World.from_script_data(script_data=_ancestor_scope_script(actor_ref="companion"))
    result = world.create_story("ancestor_scope_lazy", init_mode=InitMode.LAZY)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

    ledger.resolve_choice(_choice_action(ledger, "Go").uid)

    scene2 = _scene(ledger.graph, "scene2")
    role = next(scene2.edges_out(Selector(has_kind=Role)), None)
    assert role is not None
    assert role.satisfied is True

    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor.uid)
    rendered = render_block(caller=ledger.cursor, ctx=ctx)
    content = next(fragment for fragment in rendered if isinstance(fragment, ContentFragment))
    assert content.content == "Hello Mina"

    contents = [
        fragment.content
        for fragment in ledger.get_journal()
        if getattr(fragment, "fragment_type", None) == "content"
    ]
    assert contents[-1] == "Hello Mina"


def test_preview_blocks_missing_container_hard_dep_without_side_effects() -> None:
    world = World.from_script_data(script_data=_ancestor_scope_script(actor_ref="missing"))
    result = world.create_story("ancestor_scope_preview", init_mode=InitMode.LAZY)
    graph = result.graph
    start = _block(graph, "start")
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)

    before_item_ids = {item.uid for item in graph.values()}
    before_edge_ids = {edge.uid for edge in graph.edges}
    before_templates = dict(graph.template_by_entity_id)
    before_lineage = {
        entity_id: list(lineage)
        for entity_id, lineage in graph.template_lineage_by_entity_id.items()
    }
    before_wired = set(graph.wired_node_ids)

    fragments = render_block(caller=start, ctx=ctx)
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))

    assert choice.available is False
    assert choice.blockers is not None
    assert choice.blockers[0]["type"] == "provision"
    assert choice.blockers[0]["reason"] == "immediate_dependency_unresolvable"
    assert choice.blockers[0]["context"]["target_ctx"] == "scene2"

    assert {item.uid for item in graph.values()} == before_item_ids
    assert {edge.uid for edge in graph.edges} == before_edge_ids
    assert graph.template_by_entity_id == before_templates
    assert graph.template_lineage_by_entity_id == before_lineage
    assert graph.wired_node_ids == before_wired


def test_rebuild_runtime_materialization_state_prevents_duplicate_post_materialize(tmp_path: Path) -> None:
    world = World.from_script_data(
        script_data=_runtime_parity_script(),
        resources=_resource_manager(tmp_path),
    )
    result = world.create_story("runtime_parity_rehydrate", init_mode=InitMode.LAZY)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

    ledger.resolve_choice(_choice_action(ledger, "Enter").uid)
    middle = ledger.cursor
    assert isinstance(middle, Block)
    counts_before = _edge_inventory(middle)

    graph = ledger.graph
    graph.wired_node_ids.clear()
    graph.rebuild_runtime_materialization_state()

    template = graph.script_manager.find_template("intro.middle")
    ctx = PhaseCtx(graph=graph, cursor_id=middle.uid)
    graph.story_post_materialize(
        template=template,
        entity=middle,
        role=MaterializeRole.PROVISION_LEAF,
        _ctx=ctx,
    )

    assert middle.uid in graph.wired_node_ids
    assert _edge_inventory(middle) == counts_before


def test_runtime_wiring_import_errors_propagate(monkeypatch) -> None:
    world = World.from_script_data(script_data=_entry_only_container_script())
    result = world.create_story("entry_only_container_import_failure", init_mode=InitMode.LAZY)
    graph = result.graph
    start = _block(graph, "start")
    graph.wired_node_ids.clear()

    def _boom():
        raise ImportError("runtime wiring imports failed")

    monkeypatch.setattr(story_graph_module, "_runtime_wiring_symbols", _boom)

    with pytest.raises(ImportError, match="runtime wiring imports failed"):
        graph.is_runtime_wired_node(start)

    with pytest.raises(ImportError, match="runtime wiring imports failed"):
        graph.rebuild_runtime_materialization_state()


def test_rebuild_runtime_materialization_state_warns_and_skips_malformed_node(
    monkeypatch,
    caplog,
) -> None:
    world = World.from_script_data(script_data=_entry_only_container_script())
    result = world.create_story("entry_only_container_rebuild_warning", init_mode=InitMode.LAZY)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

    ledger.resolve_choice(_choice_action(ledger, "Go").uid)

    graph = ledger.graph
    scene2 = _scene(graph, "scene2")
    graph.wired_node_ids.clear()
    original_has_member = type(scene2).has_member

    def _broken_has_member(self, item):
        if self.uid == scene2.uid:
            raise AttributeError("broken membership cache")
        return original_has_member(self, item)

    monkeypatch.setattr(type(scene2), "has_member", _broken_has_member)
    caplog.set_level(logging.WARNING, logger=story_graph_module.__name__)

    graph.rebuild_runtime_materialization_state()

    assert scene2.uid not in graph.wired_node_ids
    assert any(
        "Skipping runtime wiring rebuild" in record.message
        and str(scene2.uid) in record.message
        for record in caplog.records
    )
