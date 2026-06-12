"""Architectural guardrails for sandbox mechanics.

These tests keep sandbox honest as a domain vocabulary over StoryTangl
primitives rather than a shadow runtime.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from tangl.core import Selector, Token
from tangl.mechanics.sandbox import (
    SandboxCompiledAssetType,
    SandboxInteraction,
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
    "scope": {
        "id": "arch_scope",
        "scheduled_events": {
            "dawn": {
                "target": "road",
                "text": "Notice the dawn",
                "period": 1,
            }
        },
    },
    "locations": {
        "road": {
            "name": "Road",
            "traits": ["light"],
            "descriptions": {"look": "You are on the road."},
            "exits": {"east": "cave"},
            "contributes": {
                "interactions": {
                    "listen": {
                        "text": "Listen to the road",
                        "target": "current",
                        "journal": "The road hums underfoot.",
                        "availability": "True",
                        "effects": "listened = True",
                    }
                },
                "scheduled_events": {
                    "wagon": {
                        "target": "cave",
                        "text": "Hear the wagon pass",
                        "period": 1,
                    }
                }
            },
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
            "traits": ["portable", "readable"],
            "initial": {"location": "road"},
            "descriptions": {"examine": "The lamp is readable, somehow."},
            "contributes": {
                "interactions": {
                    "rub": {
                        "text": "Rub the lamp",
                        "target": "current",
                    }
                },
                "scheduled_events": {
                    "flicker": {
                        "target": "current",
                        "text": "Watch the lamp flicker",
                        "period": 1,
                    }
                }
            },
        }
    },
    "fixtures": {
        "altar": {
            "name": "Altar",
            "initial": {"locations": ["road"]},
            "contributes": {
                "interactions": {
                    "pray": {
                        "text": "Pray at the altar",
                        "target": "current",
                    }
                },
                "scheduled_events": {
                    "chime": {
                        "target": "current",
                        "text": "Hear the altar chime",
                        "period": 1,
                    }
                }
            },
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
                },
                "interactions": {
                    "ask": {
                        "text": "Ask the guide about the cave",
                        "target": "road",
                        "return_to_location": True,
                    }
                },
                "scheduled_events": {
                    "warning": {
                        "target": "road",
                        "text": "Hear the guide's warning",
                        "period": 1,
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
        if {"dynamic", "sandbox"}.issubset(edge.tags)
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
    assert compiled.assets["lamp"].readable is True
    assert isinstance(compiled.mobs["guide"], SandboxMob)
    assert isinstance(road.interactions[0], SandboxInteraction)
    assert [predicate.expr for predicate in road.interactions[0].availability] == [
        "True"
    ]
    assert [effect.expr for effect in road.interactions[0].effects] == ["listened = True"]
    assert compiled.scope.scheduled_events[0].label == "dawn"
    assert road.scheduled_events[0].label == "wagon"
    assert len(compiled.assets["lamp"].interactions) == 1
    assert compiled.assets["lamp"].scheduled_events[0].label == "flicker"
    assert compiled.fixtures["altar"].interactions[0].label == "pray"
    assert compiled.fixtures["altar"].scheduled_events[0].label == "chime"
    assert isinstance(compiled.mobs["guide"].interactions[0], SandboxInteraction)
    assert compiled.mobs["guide"].scheduled_events[0].label == "warning"
    assert isinstance(compiled.mobs["guide"], Actor)

    road_ctx = PhaseCtx(graph=compiled.graph, cursor_id=road.uid)
    do_provision(road, ctx=road_ctx)

    movement = next(
        action
        for action in _sandbox_actions(road)
        if action.ui_hints.contribution == "movement"
    )
    interaction = next(
        action
        for action in _sandbox_actions(road)
        if action.ui_hints.contribution == "interaction"
    )
    assert isinstance(movement, Action)
    assert movement.successor is cave
    assert isinstance(interaction, Action)
    assert interaction.successor is road

    choices = render_block_choices(caller=road, ctx=road_ctx)
    assert any(isinstance(fragment, ChoiceFragment) for fragment in choices or [])

    cave_ctx = PhaseCtx(graph=compiled.graph, cursor_id=cave.uid)
    do_provision(cave, ctx=cave_ctx)
    mob_action = next(
        action
        for action in _sandbox_actions(cave)
        if action.ui_hints.model_dump().get("mob") == "guide"
    )
    assert isinstance(mob_action, Action)
    assert mob_action.successor is cave
    assert "affordance:greet" in mob_action.tags

    fragments = render_block(caller=cave, ctx=cave_ctx)
    assert any(
        isinstance(fragment, ContentFragment) and fragment.content == "The guide is here."
        for fragment in fragments or []
    )


# Cleanup-discriminator contract. Each projector family removes its own stale
# dynamic actions by matching one of these tag sets against its source node's
# edges_out. The families intentionally share tags (every set contains
# "dynamic"; menu and game also share "fanout"), so the safety property is NOT
# set disjointness — it is mutual non-subsumption: no family's discriminator
# is a subset of another's, so no family's cleanup sweep automatically claims
# another family's actions. Until now this held by convention only. See
# AFFORDANCE_MODEL.md, "The audit table (filled)".
#
# Engine-owned families only, deliberately: the adventure world's
# {dynamic, sandbox, adventure} discriminator is excluded because its hazard
# actions also wear "movement" and legitimately match two families today
# (see the hazard row of the audit table). Adding it here would fail the
# exactly-one-family test until that overlap is resolved by contract.
FAMILY_DISCRIMINATORS: dict[str, frozenset[str]] = {
    "menu": frozenset({"dynamic", "fanout", "menu"}),
    "game": frozenset({"dynamic", "fanout", "game"}),
    **{
        f"sandbox:{kind}": frozenset({"dynamic", "sandbox", kind})
        for kind in (
            "movement", "asset", "unlock", "lock", "fixture",
            "mob", "location", "wait", "event", "incremental",
        )
    },
}


def _matching_families(tags: set[str]) -> set[str]:
    return {name for name, disc in FAMILY_DISCRIMINATORS.items() if disc <= tags}


def test_dynamic_action_family_discriminators_are_mutually_non_subsuming() -> None:
    """No family's cleanup discriminator may subsume another's.

    Not set disjointness — families share "dynamic" (and menu/game share
    "fanout") by design. The contract is a subset antichain: if one
    discriminator were a subset of another, its cleanup sweep would claim
    every action of the other family.
    """
    from itertools import combinations

    for (a, disc_a), (b, disc_b) in combinations(FAMILY_DISCRIMINATORS.items(), 2):
        assert not disc_a <= disc_b and not disc_b <= disc_a, (a, b)


def test_generated_actions_match_exactly_one_family_discriminator() -> None:
    """A projected dynamic action is owned by exactly one cleanup family.

    Every family in FAMILY_DISCRIMINATORS must be observed, so adding a new
    family to the dict forces this fixture to generate one of its actions.
    """
    from tangl.mechanics.games import (
        HasGame,
        IncrementalGame,
        IncrementalGameHandler,
        TaskSpec,
    )
    from tangl.mechanics.sandbox import LockableFacet, SandboxFixture
    from tangl.mechanics.sandbox import incremental as _incremental  # registers projector
    from tangl.story import Block

    assert _incremental.project_sandbox_incremental_game_moves is not None

    compiled = SandboxSliceCompiler().compile(ARCHITECTURE_SLICE)

    # Unlock/lock families: one locked fixture (projects unlock) and one
    # unlocked lockable fixture (projects lock).
    compiled.locations["cave"].fixtures = [
        SandboxFixture(label="grate", name="grate", lockable=LockableFacet(key="keys")),
        SandboxFixture(
            label="gate", name="gate", lockable=LockableFacet(key="keys", is_locked=False)
        ),
    ]

    # Incremental family: host a minimal incremental game under the scope.
    class _ColonyGame(IncrementalGame):
        starting_resources: dict[str, int] = {"food": 1}
        starting_workers: int = 1
        task_specs: dict[str, TaskSpec] = {"forage": TaskSpec(produces={"food": 2})}
        upkeep: dict[str, int] = {"food": 1}
        unlocked_tasks: list[str] = ["forage"]

    class _ColonyBlock(HasGame, Block):
        _game_class = _ColonyGame
        _game_handler_class = IncrementalGameHandler

    colony = _ColonyBlock(label="family_colony")
    compiled.graph.add(colony)
    compiled.scope.add_child(colony)

    seen: set[str] = set()
    for label in ("road", "cave"):
        location = compiled.locations[label]
        do_provision(location, ctx=PhaseCtx(graph=compiled.graph, cursor_id=location.uid))
        for action in location.edges_out(Selector(has_kind=Action)):
            tags = set(action.tags or set())
            if "dynamic" not in tags:
                continue
            families = _matching_families(tags)
            assert len(families) == 1, (action.get_label(), sorted(tags))
            seen |= families

    # Menu family: project from a hand-wired dynamic fanout affordance.
    from tangl.story import Block
    from tangl.story.system_handlers import project_menu_affordances
    from tangl.vm import Affordance

    menu = compiled.graph.add_node(kind=MenuBlock, label="family_menu")
    item = compiled.graph.add_node(kind=Block, label="family_item")
    Affordance(
        registry=compiled.graph,
        predecessor_id=menu.uid,
        successor_id=item.uid,
        requirement={"has_identifier": "family_item"},
        tags={"dynamic", "fanout"},
    )
    project_menu_affordances(caller=menu, ctx=PhaseCtx(graph=compiled.graph, cursor_id=menu.uid))

    # Game family: provision self-loop moves for a minimal hosted game.
    from tangl.mechanics.games import HasGame
    from tangl.mechanics.games.handlers import provision_game_moves
    from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler

    class _GameBlock(HasGame, Block):
        _game_class = RpsGame
        _game_handler_class = RpsGameHandler

    game_block = compiled.graph.add_node(kind=_GameBlock, label="family_game")
    game_block.game_handler.setup(game_block.game)
    provision_game_moves(game_block, ctx=PhaseCtx(graph=compiled.graph, cursor_id=game_block.uid))

    for node in (menu, game_block):
        for action in node.edges_out(Selector(has_kind=Action)):
            tags = set(action.tags or set())
            if "dynamic" not in tags:
                continue
            families = _matching_families(tags)
            assert len(families) == 1, (action.get_label(), sorted(tags))
            seen |= families

    missing = set(FAMILY_DISCRIMINATORS) - seen
    assert not missing, sorted(missing)


@pytest.mark.parametrize(
    ("section", "expected"),
    [
        ("assets", "Asset 'lamp' starts in unknown sandbox location 'missing_room'"),
        ("fixtures", "Fixture 'gate' is placed in unknown sandbox location 'missing_room'"),
        ("mobs", "Mob 'guide' starts in unknown sandbox location 'missing_room'"),
    ],
)
def test_sandbox_compiler_reports_unknown_placement_locations(
    section: str,
    expected: str,
) -> None:
    """Bad compact IR should fail with a compiler-shaped message, not KeyError."""
    data = deepcopy(ARCHITECTURE_SLICE)
    if section == "assets":
        data["assets"]["lamp"]["initial"]["location"] = "missing_room"
    elif section == "fixtures":
        data["fixtures"] = {
            "gate": {
                "name": "gate",
                "initial": {"locations": ["missing_room"]},
            }
        }
    else:
        data["mobs"]["guide"]["initial"]["location"] = "missing_room"

    with pytest.raises(ValueError, match=expected):
        SandboxSliceCompiler().compile(data)
