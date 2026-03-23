"""Story initialization integration tests.

Covers compiler output, LAZY/EAGER initialization behavior, dependency
prelinking expectations, and runtime/loader guardrails.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from tangl.loaders import WorldBundle, WorldCompiler
from tangl.media.media_resource import MediaDep
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.persistence import PersistenceManagerFactory
from tangl.service import build_service_manager
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.story.concepts import Actor, Location, Role, Setting
from tangl.story.fabula import (
    GraphInitializationError,
    ResolutionError,
    ResolutionFailureReason,
    StoryCompiler,
)
from tangl.story.episode import Action, Block, Scene
from tangl.core import BehaviorRegistry, DispatchLayer, EntityTemplate, Selector, TemplateRegistry
from tangl.story.dispatch import story_dispatch
from tangl.vm import Ledger


def _base_script() -> dict:
    return {
        "label": "story_demo",
        "metadata": {
            "title": "Story Demo",
            "author": "Tests",
            "start_at": "intro.start",
        },
        "globals": {"gold": 5},
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
                        "roles": [{"label": "host", "actor_ref": "guard"}],
                        "settings": [{"label": "place", "location_ref": "castle"}],
                        "actions": [{"text": "Continue", "successor": "end"}],
                    },
                    "end": {
                        "content": "End",
                    },
                },
            }
        },
    }


def test_compiler_emits_template_registry_and_entry_ids() -> None:
    bundle = StoryCompiler().compile(_base_script())

    assert bundle.entry_template_ids == ["intro.start"]
    assert bundle.template_registry.find_one(Selector(label="intro")) is not None
    assert bundle.template_registry.find_one(Selector(label="intro.start")) is not None


def test_lazy_mode_materializes_entry_and_ancestor_only() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("run_lazy", init_mode=InitMode.LAZY)

    graph = result.graph
    scene_nodes = list(Selector(has_kind=Scene).filter(graph.values()))
    block_nodes = list(Selector(has_kind=Block).filter(graph.values()))
    actor_nodes = list(Selector(has_kind=Actor).filter(graph.values()))
    location_nodes = list(Selector(has_kind=Location).filter(graph.values()))

    assert len(scene_nodes) == 1
    assert {node.label for node in block_nodes} == {"start"}
    assert actor_nodes == []
    assert location_nodes == []
    assert graph.initial_cursor_id == block_nodes[0].uid
    assert any("action destination unresolved" in warning for warning in result.report.warnings)


def test_ledger_from_story_graph_defaults_to_story_initial_cursor() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("run_lazy", init_mode=InitMode.LAZY)

    ledger = Ledger.from_graph(result.graph)

    assert result.graph.factory is world
    assert result.graph.world is world
    assert ledger.cursor_id == result.graph.initial_cursor_id
    assert ledger.cursor is result.graph.get(result.graph.initial_cursor_id)


def test_story_graph_roundtrip_preserves_world_factory_identity() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("story_roundtrip", init_mode=InitMode.EAGER)

    payload = result.graph.unstructure()
    restored = type(result.graph).structure(payload)

    assert "world" not in payload
    assert restored.factory is world
    assert restored.world is world
    assert restored.world.find_template("intro.start") is world.find_template("intro.start")


def test_create_story_preserves_seed_entry_ids_when_explicit_entries_are_cleared() -> None:
    world = World.from_script_data(script_data=_base_script())
    world.force_set("entry_template_ids", [])

    result = world.create_story("seed_entry_story", init_mode=InitMode.LAZY)

    assert result.graph.initial_cursor_id is not None
    assert result.graph.initial_cursor_ids == [result.graph.initial_cursor_id]
    assert result.entry_ids == [result.graph.initial_cursor_id]


@pytest.mark.parametrize("init_mode", [InitMode.LAZY, InitMode.EAGER])
def test_create_story_uses_direct_world_fields_when_bundle_is_cleared(init_mode: InitMode) -> None:
    world = World.from_script_data(script_data=_base_script())
    world.force_set("bundle", None)

    result = world.create_story(f"bundleless_{init_mode.value}", init_mode=init_mode)

    assert result.graph.factory is world
    assert result.graph.initial_cursor_id is not None
    assert result.source_map == world.source_map
    assert result.codec_state == world.codec_state
    assert result.codec_id == world.codec_id


def test_freeze_shape_requires_eager_mode() -> None:
    world = World.from_script_data(script_data=_base_script())

    with pytest.raises(ValueError, match="freeze_shape requires InitMode.EAGER"):
        world.create_story("run_lazy_frozen", init_mode=InitMode.LAZY, freeze_shape=True)


def test_lazy_mode_missing_canonical_destination_raises_resolution_error() -> None:
    script = {
        "label": "lazy_missing_destination",
        "metadata": {
            "title": "Missing Destination",
            "author": "Tests",
            "start_at": "intro.start",
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "missing"}],
                    },
                }
            },
        },
    }

    world = World.from_script_data(script_data=script)
    with pytest.raises(ResolutionError) as exc_info:
        world.create_story("lazy_missing_story", init_mode=InitMode.LAZY)

    error = exc_info.value
    assert error.reason is ResolutionFailureReason.NO_TEMPLATE
    assert error.authored_ref == "missing"
    assert error.canonical_ref == "intro.missing"
    assert error.source_node_label == "start"
    assert error.selector["has_identifier"] == "intro.missing"
    assert error.world_id == world.label
    assert error.bundle_id == world.bundle.template_registry.label


def test_lazy_mode_ambiguous_destination_raises_resolution_error() -> None:
    @dataclass(slots=True)
    class _AmbiguousTemplates:
        extra: TemplateRegistry

        def get_template_scope_groups(self, *, caller=None, graph=None):
            return [list(self.extra.values())]

    script = {
        "label": "lazy_ambiguous_destination",
        "metadata": {
            "title": "Ambiguous Destination",
            "author": "Tests",
            "start_at": "scene1.start",
        },
        "scenes": {
            "scene1": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "scene2"}],
                    },
                }
            },
            "scene2": {
                "blocks": {
                    "entry": {"content": "Entry"},
                }
            },
        },
    }
    extra_templates = TemplateRegistry(label="extra_scope")
    EntityTemplate(
        label="scene2",
        payload=Block(label="scene2_shadow", content="Shadow"),
        registry=extra_templates,
    )

    world = World.from_script_data(
        script_data=script,
        templates=_AmbiguousTemplates(extra=extra_templates),
    )
    with pytest.raises(ResolutionError) as exc_info:
        world.create_story("lazy_ambiguous_story", init_mode=InitMode.LAZY)

    error = exc_info.value
    assert error.reason is ResolutionFailureReason.AMBIGUOUS_TEMPLATE
    assert error.authored_ref == "scene2"
    assert error.canonical_ref == "scene2"
    assert error.source_node_label == "start"
    assert error.selector["has_identifier"] == "scene2"


def test_eager_mode_materializes_all_and_wires_dependencies() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("run_eager", init_mode=InitMode.EAGER)

    graph = result.graph
    assert len(result.report.unresolved_hard) == 0

    block_nodes = list(Selector(has_kind=Block).filter(graph.values()))
    assert {node.label for node in block_nodes} == {"start", "end"}

    roles = list(Selector(has_kind=Role).filter(graph.values()))
    settings = list(Selector(has_kind=Setting).filter(graph.values()))
    assert len(roles) == 1
    assert len(settings) == 1
    assert roles[0].satisfied
    assert settings[0].satisfied


def test_eager_mode_missing_hard_dependency_raises() -> None:
    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
        {"label": "host", "actor_ref": "missing", "hard": True}
    ]

    world = World.from_script_data(script_data=script)
    with pytest.raises(GraphInitializationError):
        world.create_story("run_fail", init_mode=InitMode.EAGER)


def test_eager_mode_missing_soft_dependency_is_reported() -> None:
    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
        {"label": "optional_host", "actor_ref": "missing", "hard": False}
    ]

    world = World.from_script_data(script_data=script)
    result = world.create_story("run_soft", init_mode=InitMode.EAGER)

    assert len(result.report.unresolved_hard) == 0
    assert len(result.report.unresolved_soft) == 1
    assert result.report.unresolved_soft[0].label == "optional_host"


def test_eager_mode_prelink_selection_is_deterministic() -> None:
    script = _base_script()
    script["actors"] = {
        "alice": {"name": "Alice"},
        "bob": {"name": "Bob"},
    }
    script["scenes"]["intro"]["blocks"]["start"]["roles"] = [{"label": "companion"}]

    world_a = World.from_script_data(script_data=script)
    result_a = world_a.create_story("run_det_a", init_mode=InitMode.EAGER)

    script_b = dict(script)
    script_b["label"] = "story_demo_second"
    world_b = World.from_script_data(script_data=script_b)
    result_b = world_b.create_story("run_det_b", init_mode=InitMode.EAGER)

    role_a = next(Selector(has_kind=Role).filter(result_a.graph.values()))
    role_b = next(Selector(has_kind=Role).filter(result_b.graph.values()))
    assert role_a.provider is not None
    assert role_b.provider is not None
    assert role_a.provider.label == role_b.provider.label


def test_static_cyoa_traversal_needs_no_runtime_provisioning() -> None:
    script = {
        "label": "linear",
        "metadata": {"title": "Linear", "author": "Tests", "start_at": "intro.start"},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {"content": "A", "actions": [{"text": "Go", "successor": "middle"}]},
                    "middle": {"content": "B", "actions": [{"text": "Go", "successor": "end"}]},
                    "end": {"content": "C"},
                }
            }
        },
    }

    world = World.from_script_data(script_data=script)
    result = world.create_story("linear_eager", init_mode=InitMode.EAGER)

    assert result.report.unresolved_hard == []
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    start = ledger.cursor
    action = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    ledger.resolve_choice(action.uid)

    assert ledger.cursor.label == "middle"


def test_action_payload_is_materialized_from_script() -> None:
    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["actions"][0]["payload"] = {
        "move": "rock",
        "weight": 1,
    }
    script["scenes"]["intro"]["blocks"]["start"]["actions"][0]["accepts"] = {
        "type": "object",
        "properties": {
            "move": {"type": "string", "enum": ["rock", "paper", "scissors"]},
        },
        "required": ["move"],
    }
    script["scenes"]["intro"]["blocks"]["start"]["actions"][0]["ui_hints"] = {
        "widget": "radio",
        "framework": "wx",
    }

    world = World.from_script_data(script_data=script)
    result = world.create_story("payload_story", init_mode=InitMode.EAGER)
    start = result.graph.get(result.graph.initial_cursor_id)
    assert isinstance(start, Block)
    action = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    assert action.payload == {"move": "rock", "weight": 1}
    assert action.accepts is not None
    assert action.accepts["type"] == "object"
    assert action.accepts["properties"]["move"]["enum"] == ["rock", "paper", "scissors"]
    assert action.ui_hints == {"widget": "radio", "framework": "wx"}


def test_action_hint_aliases_payload_schema_and_presentation_hints() -> None:
    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["actions"][0]["payload_schema"] = {
        "type": "string",
        "enum": ["red", "blue"],
    }
    script["scenes"]["intro"]["blocks"]["start"]["actions"][0]["presentation_hints"] = {
        "style_tags": ["choice", "inline"],
        "widget": "chips",
    }

    world = World.from_script_data(script_data=script)
    result = world.create_story("payload_alias_story", init_mode=InitMode.EAGER)
    start = result.graph.get(result.graph.initial_cursor_id)
    assert isinstance(start, Block)
    action = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    assert action.accepts == {"type": "string", "enum": ["red", "blue"]}
    assert action.ui_hints == {"style_tags": ["choice", "inline"], "widget": "chips"}


def test_loader_compiler_runtime_path(tmp_path: Path) -> None:
    world_root = tmp_path / "loader_world"
    world_root.mkdir()
    media_dir = world_root / "media"
    media_dir.mkdir()
    (media_dir / "cover.svg").write_text(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\"></svg>",
        encoding="utf-8",
    )
    (world_root / "domain").mkdir()
    package_dir = world_root / "loader_world"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "domain.py").write_text(
        """
from tangl.core import Entity


class DomainCharacter(Entity):
    ...
""".strip(),
        encoding="utf-8",
    )

    (world_root / "world.yaml").write_text(
        """
label: loader_world
scripts: script.yaml
""".strip(),
        encoding="utf-8",
    )
    (world_root / "script.yaml").write_text(
        """
label: loader_world
metadata:
  title: Loader World
  author: Tests
  start_at: intro.start
scenes:
  intro:
    blocks:
      start:
        content: Hello
""".strip(),
        encoding="utf-8",
    )

    bundle = WorldBundle.load(world_root)
    compiled = WorldCompiler().compile(bundle)

    assert isinstance(compiled, World)
    assert compiled.assets is not None
    assert compiled.resources is not None
    assert compiled.templates is compiled.bundle.template_registry
    assert "DomainCharacter" in compiled.class_registry
    assert compiled.dispatch in compiled.get_authorities()
    result = compiled.create_story("loader_story", init_mode=InitMode.LAZY)
    assert result.graph.initial_cursor_id is not None
    assert result.codec_id in {"near_native", "near_native_yaml"}
    assert "__source_files__" in result.source_map
    assert len(result.source_map["__source_files__"]) == 1


def test_story_materializer_wires_inventory_media_without_wrapping_direct_media(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    asset = media_root / "cover.svg"
    asset.write_text(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\"></svg>",
        encoding="utf-8",
    )
    resources = ResourceManager(media_root, scope="world")
    resources.index_directory(".")

    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["media"] = [
        {"name": "cover.svg", "text": "Cover"},
        {"url": "https://example.com/poster.svg"},
        {"data": "<svg xmlns='http://www.w3.org/2000/svg'></svg>"},
    ]

    world = World.from_script_data(script_data=script, resources=resources)
    result = world.create_story("media_story", init_mode=InitMode.EAGER)

    start = next(node for node in Selector(has_kind=Block, label="start").filter(result.graph.values()))
    media_deps = [edge for edge in start.edges_out() if isinstance(edge, MediaDep)]

    assert len(media_deps) == 1
    assert media_deps[0].provider is not None
    assert start.media[0].get("dependency_id") == media_deps[0].uid
    assert "dependency_id" not in start.media[1]
    assert "dependency_id" not in start.media[2]


def test_service_manager_create_story_with_world_param() -> None:
    world = World.from_script_data(script_data=_base_script())
    manager = build_service_manager(PersistenceManagerFactory.native_in_mem())
    user = User(label="test-user")
    manager.persistence.save(user)

    result = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_story",
    )

    assert result.cursor_id is not None
    assert result.metadata.get("world_id") == world.label


def test_story_graph_authorities_include_story_and_world_authorities() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("auth_story", init_mode=InitMode.LAZY)

    world_authority = BehaviorRegistry(
        label="world.auth",
        default_dispatch_layer=DispatchLayer.APPLICATION,
    )
    result.graph.world = SimpleNamespace(get_authorities=lambda: [world_authority])

    authorities = result.graph.get_authorities()
    assert story_dispatch in authorities
    assert world_authority in authorities


def test_story_init_does_not_create_story_media_until_needed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story_media_root = tmp_path / "story_media"

    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        lambda story_id=None: story_media_root if story_id is None else story_media_root / str(story_id),
    )

    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("no_media_story", init_mode=InitMode.LAZY)

    assert result.graph.story_resources is None
    assert not story_media_root.exists()


def test_story_graph_template_lineage_is_nearest_first() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("scope_lineage_story", init_mode=InitMode.EAGER)

    graph = result.graph
    cursor = graph.get(graph.initial_cursor_id)
    assert cursor is not None

    lineage = graph.template_lineage_by_entity_id.get(cursor.uid, [])
    assert lineage
    assert lineage[0] == graph.template_by_entity_id[cursor.uid]


def test_scene_finalize_container_contract_is_idempotent() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("scene_finalize_idempotent", init_mode=InitMode.EAGER)
    graph = result.graph

    scene = next(Selector(has_kind=Scene, label="intro").filter(graph.values()), None)
    assert scene is not None
    original_source = scene.source_id
    original_sink = scene.sink_id
    assert original_source is not None
    assert original_sink is not None

    scene.finalize_container_contract()
    scene.finalize_container_contract()

    assert scene.source_id == original_source
    assert scene.sink_id == original_sink


def test_story_graph_template_scope_groups_follow_lineage_order() -> None:
    world = World.from_script_data(script_data=_base_script())
    result = world.create_story("scope_groups_story", init_mode=InitMode.EAGER)

    graph = result.graph
    cursor = graph.get(graph.initial_cursor_id)
    assert cursor is not None

    groups = graph.get_template_scope_groups(cursor)
    assert groups

    lineage = [
        templ_id
        for templ_id in graph.template_lineage_by_entity_id.get(cursor.uid, [])
        if graph.template_registry is not None and graph.template_registry.get(templ_id) is not None
    ]
    group_heads = [getattr(group[0], "uid", None) for group in groups if group]
    assert group_heads[: len(lineage)] == lineage


def test_world_template_lookup_facade_finds_templates() -> None:
    world = World.from_script_data(script_data=_base_script())

    start_template = world.find_template("intro.start")
    assert start_template is not None
    assert start_template.get_label() == "intro.start"

    block_templates = world.find_templates(Selector(has_payload_kind=Block))
    assert block_templates
    assert any(template.get_label() == "intro.start" for template in block_templates)


def test_world_template_scope_groups_are_included_in_runtime_scope() -> None:
    base_world = World.from_script_data(script_data=_base_script())
    extra_registry = TemplateRegistry(label="world_extra_templates")
    extra_template = EntityTemplate(
        label="world.extra.guest",
        payload=Actor(label="guest", name="Guest Actor"),
        registry=extra_registry,
    )
    _ = extra_template

    world = World(
        label=f"{base_world.label}.scope",
        bundle=base_world.bundle,
        templates=base_world.bundle.template_registry,
        extra_template_registries=[extra_registry],
    )
    result = world.create_story("scope_world_story", init_mode=InitMode.EAGER)
    cursor = result.graph.get(result.graph.initial_cursor_id)
    assert cursor is not None

    groups = result.graph.get_template_scope_groups(cursor)
    labels = {
        item.get_label()
        for group in groups
        for item in group
        if hasattr(item, "get_label")
    }
    assert "world.extra.guest" in labels


def test_story_source_has_no_legacy_core_vm_imports() -> None:
    src_root = Path(__file__).resolve().parents[2] / "src" / "tangl" / "story"
    assert src_root.exists(), str(src_root)
    bad_markers = (
        "from tangl.core_legacy ",
        "from tangl.vm_legacy ",
        "import tangl.core_legacy",
        "import tangl.vm_legacy",
    )

    for file_path in src_root.rglob("*.py"):
        text = file_path.read_text(encoding="utf-8")
        assert not any(marker in text for marker in bad_markers), str(file_path)
