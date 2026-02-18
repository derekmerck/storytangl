"""Story38 initialization integration tests.

Covers compiler output, MINIMAL/FULLY_SPECIFIED initialization behavior,
dependency prelinking expectations, and runtime/loader guardrails.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tangl.loaders import WorldBundle, WorldCompiler
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.user.user import User
from tangl.story38 import InitMode, World38
from tangl.story38.concepts import Actor, Location, Role, Setting
from tangl.story38.fabula import GraphInitializationError, StoryCompiler38
from tangl.story38.episode import Action, Block, Scene
from tangl.core38 import BehaviorRegistry, DispatchLayer, Selector
from tangl.story38.dispatch import story_dispatch
from tangl.vm38 import Ledger


def _base_script() -> dict:
    return {
        "label": "story38_demo",
        "metadata": {
            "title": "Story38 Demo",
            "author": "Tests",
            "start_at": "intro.start",
        },
        "globals": {"gold": 5},
        "actors": {
            "guard": {
                "name": "Joe",
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
            }
        },
        "locations": {
            "castle": {
                "name": "Castle",
                "obj_cls": "tangl.story.concepts.location.location.Location",
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
    bundle = StoryCompiler38().compile(_base_script())

    assert bundle.entry_template_ids == ["intro.start"]
    assert bundle.template_registry.find_one(Selector(label="intro")) is not None
    assert bundle.template_registry.find_one(Selector(label="intro.start")) is not None


def test_minimal_mode_materializes_entry_and_ancestor_only() -> None:
    world = World38.from_script_data(script_data=_base_script())
    result = world.create_story("run_min", init_mode=InitMode.MINIMAL)

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


def test_full_mode_materializes_all_and_wires_dependencies() -> None:
    world = World38.from_script_data(script_data=_base_script())
    result = world.create_story("run_full", init_mode=InitMode.FULLY_SPECIFIED)

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


def test_full_mode_missing_hard_dependency_raises() -> None:
    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
        {"label": "host", "actor_ref": "missing", "hard": True}
    ]

    world = World38.from_script_data(script_data=script)
    with pytest.raises(GraphInitializationError):
        world.create_story("run_fail", init_mode=InitMode.FULLY_SPECIFIED)


def test_full_mode_missing_soft_dependency_is_reported() -> None:
    script = _base_script()
    script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
        {"label": "optional_host", "actor_ref": "missing", "hard": False}
    ]

    world = World38.from_script_data(script_data=script)
    result = world.create_story("run_soft", init_mode=InitMode.FULLY_SPECIFIED)

    assert len(result.report.unresolved_hard) == 0
    assert len(result.report.unresolved_soft) == 1
    assert result.report.unresolved_soft[0].label == "optional_host"


def test_full_mode_prelink_selection_is_deterministic() -> None:
    script = _base_script()
    script["actors"] = {
        "alice": {"name": "Alice"},
        "bob": {"name": "Bob"},
    }
    script["scenes"]["intro"]["blocks"]["start"]["roles"] = [{"label": "companion"}]

    world_a = World38.from_script_data(script_data=script)
    result_a = world_a.create_story("run_det_a", init_mode=InitMode.FULLY_SPECIFIED)

    world_b = World38.from_script_data(script_data=script)
    result_b = world_b.create_story("run_det_b", init_mode=InitMode.FULLY_SPECIFIED)

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

    world = World38.from_script_data(script_data=script)
    result = world.create_story("linear_full", init_mode=InitMode.FULLY_SPECIFIED)

    assert result.report.unresolved_hard == []
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    start = ledger.cursor
    action = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    ledger.resolve_choice(action.uid)

    assert ledger.cursor.label == "middle"


def test_loader_compiler_runtime_38_path(tmp_path: Path) -> None:
    world_root = tmp_path / "loader_world"
    world_root.mkdir()

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
    compiled = WorldCompiler().compile(bundle, runtime_version="38")

    assert isinstance(compiled, World38)
    result = compiled.create_story("loader_story", init_mode=InitMode.MINIMAL)
    assert result.graph.initial_cursor_id is not None
    assert result.codec_id in {"near_native", "near_native_yaml"}
    assert "__source_files__" in result.source_map
    assert len(result.source_map["__source_files__"]) == 1


def test_runtime_controller_create_story38_with_world_param() -> None:
    world = World38.from_script_data(script_data=_base_script())
    controller = RuntimeController()
    user = User(label="test-user")

    result = controller.create_story38(
        user=user,
        world_id=world.label,
        world=world,
        init_mode=InitMode.FULLY_SPECIFIED.value,
        story_label="svc_story",
    )

    assert result.status == "ok"
    assert result.cursor_id is not None
    assert result.details is not None
    assert result.details.get("world_id") == world.label


def test_story_graph_authorities_include_story_and_world_authorities() -> None:
    world = World38.from_script_data(script_data=_base_script())
    result = world.create_story("auth_story", init_mode=InitMode.MINIMAL)

    world_authority = BehaviorRegistry(
        label="world.auth",
        default_dispatch_layer=DispatchLayer.APPLICATION,
    )
    result.graph.world = SimpleNamespace(get_authorities=lambda: [world_authority])

    authorities = result.graph.get_authorities()
    assert story_dispatch in authorities
    assert world_authority in authorities


def test_story38_source_has_no_legacy_core_vm_imports() -> None:
    src_root = Path(__file__).resolve().parents[2] / "src" / "tangl" / "story38"
    assert src_root.exists(), str(src_root)
    bad_markers = ("from tangl.core ", "from tangl.vm ", "import tangl.core", "import tangl.vm")

    for file_path in src_root.rglob("*.py"):
        text = file_path.read_text(encoding="utf-8")
        assert not any(marker in text for marker in bad_markers), str(file_path)
