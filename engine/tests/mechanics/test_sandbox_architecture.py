"""Architectural guardrails for sandbox mechanics.

These tests keep sandbox honest as a domain vocabulary over StoryTangl
primitives rather than a shadow runtime.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tangl.core import Selector, Token
from tangl.mechanics.sandbox import (
    SandboxCompiledAssetType,
    SandboxLocation,
    SandboxMob,
    SandboxScope,
    SandboxSliceCompiler,
)
from tangl.story import Action, MenuBlock, StoryGraph
from tangl.story.concepts import Actor
from tangl.story.fragments import ChoiceFragment, ContentFragment
from tangl.story.system_handlers import render_block, render_block_choices
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


ENGINE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ENGINE_ROOT / "src" / "tangl"
SANDBOX_ROOT = SOURCE_ROOT / "mechanics" / "sandbox"

ARCHITECTURE_SLICE = {
    "id": "sandbox_architecture_slice",
    "scope": {"id": "arch_scope"},
    "locations": {
        "road": {
            "name": "Road",
            "traits": ["light"],
            "descriptions": {"look": "You are on the road."},
            "exits": {"east": "cave"},
        },
        "cave": {
            "name": "Cave",
            "traits": ["light"],
            "descriptions": {"look": "You are in the cave."},
            "exits": {"west": "road"},
        },
    },
    "assets": {
        "lamp": {
            "name": "lamp",
            "traits": ["portable"],
            "initial": {"location": "road"},
        }
    },
    "mobs": {
        "guide": {
            "name": "Guide",
            "initial": {"location": "cave"},
            "descriptions": {"present": "The guide is here."},
            "contributes": {
                "affordances": {
                    "greet": {
                        "text": "Greet the guide",
                        "journal": "The guide nods.",
                    }
                }
            },
        }
    },
}


@pytest.fixture(autouse=True)
def _clear_compiled_asset_types() -> None:
    SandboxCompiledAssetType.clear_instances()
    yield
    SandboxCompiledAssetType.clear_instances()


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _sandbox_actions(location: SandboxLocation) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox"}.issubset(getattr(edge, "tags", set()) or set())
    ]


def test_lower_runtime_layers_do_not_import_sandbox() -> None:
    """Sandbox must remain deletable from Core/VM/Story/Service."""
    offenders: list[str] = []
    for package in ("core", "vm", "story", "service"):
        for path in _python_files(SOURCE_ROOT / package):
            text = path.read_text()
            if "tangl.mechanics.sandbox" in text or "mechanics.sandbox" in text:
                offenders.append(str(path.relative_to(ENGINE_ROOT)))

    assert offenders == []


def test_sandbox_defines_no_shadow_runtime_primitives() -> None:
    """Sandbox should not grow its own ledger, frame, dispatch, or fragment model."""
    forbidden = {
        "SandboxCtx",
        "SandboxDispatch",
        "SandboxFragment",
        "SandboxFrame",
        "SandboxGraph",
        "SandboxLedger",
        "SandboxResolver",
    }
    defined: set[str] = set()
    for path in _python_files(SANDBOX_ROOT):
        tree = ast.parse(path.read_text(), filename=str(path))
        defined.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        )

    assert defined.isdisjoint(forbidden)


def test_sandbox_compiles_to_canonical_story_primitives() -> None:
    """The compact slice lowers to normal graph, node, token, action, and journal types."""
    compiled = SandboxSliceCompiler().compile(ARCHITECTURE_SLICE)
    road = compiled.locations["road"]
    cave = compiled.locations["cave"]

    assert isinstance(compiled.graph, StoryGraph)
    assert isinstance(compiled.scope, SandboxScope)
    assert isinstance(road, MenuBlock)
    assert isinstance(compiled.assets["lamp"], Token)
    assert isinstance(compiled.mobs["guide"], SandboxMob)
    assert isinstance(compiled.mobs["guide"], Actor)

    road_ctx = PhaseCtx(graph=compiled.graph, cursor_id=road.uid)
    do_provision(road, ctx=road_ctx)

    movement = next(
        action
        for action in _sandbox_actions(road)
        if action.ui_hints.get("contribution") == "movement"
    )
    assert isinstance(movement, Action)
    assert movement.successor is cave

    choices = render_block_choices(caller=road, ctx=road_ctx)
    assert any(isinstance(fragment, ChoiceFragment) for fragment in choices or [])

    cave_ctx = PhaseCtx(graph=compiled.graph, cursor_id=cave.uid)
    do_provision(cave, ctx=cave_ctx)
    mob_action = next(
        action
        for action in _sandbox_actions(cave)
        if action.ui_hints.get("mob") == "guide"
    )
    assert isinstance(mob_action, Action)
    assert mob_action.successor is cave

    fragments = render_block(caller=cave, ctx=cave_ctx)
    assert any(
        isinstance(fragment, ContentFragment) and fragment.content == "The guide is here."
        for fragment in fragments or []
    )
