"""Hand-compiled Adventure sandbox slice over generic sandbox mechanics."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import Field

from tangl.core import Selector, Token
from tangl.mechanics.sandbox import (
    SandboxExit,
    SandboxLocation,
    SandboxLockable,
    SandboxScope,
    SandboxVisibilityRule,
)
from tangl.story import Action, StoryGraph
from tangl.story.concepts.asset import AssetType
from tangl.story.fragments import ChoiceFragment
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


ADVENTURE_SANDBOX_SLICE: dict[str, Any] = {
    "id": "adventure_sandbox_slice",
    "title": "Colossal Cave Adventure - Sandbox Slice",
    "source": {
        "kind": "punyinform",
        "path": "advent_punyinform.inf",
        "stance": "feel_preserving_compression",
    },
    "scope": {"id": "cave", "state": {"world_turn": 0}},
    "locations": {
        "road": {
            "name": "End of Road",
            "traits": ["light", "aboveground", "notfarin"],
            "descriptions": {
                "look": (
                    "You are standing at the end of a road before a small brick "
                    "building. Around you is a forest."
                ),
                "repeat": "You're at the end of the road again.",
            },
            "exits": {
                "east": "building",
                "south": "valley",
                "down": "valley",
                "in": "building",
            },
        },
        "building": {
            "name": "Inside Building",
            "traits": ["light", "aboveground", "notfarin"],
            "descriptions": {
                "look": "You are inside a building, a well house for a large spring.",
                "repeat": "You're inside the building.",
            },
            "exits": {
                "west": "road",
                "out": "road",
                "in": {
                    "kind": "message",
                    "journal": "The pipes are too small.",
                },
            },
        },
        "valley": {
            "name": "In A Valley",
            "traits": ["light", "aboveground", "notfarin"],
            "descriptions": {
                "look": "You are in a valley beside a stream tumbling along a rocky bed.",
                "repeat": "You're in the valley.",
            },
            "exits": {
                "north": "road",
                "up": "road",
                "south": "slit_streambed",
                "down": "slit_streambed",
            },
        },
        "slit_streambed": {
            "name": "At Slit in Streambed",
            "traits": ["light", "aboveground", "notfarin"],
            "descriptions": {
                "look": (
                    "At your feet all the water of the stream splashes into a "
                    "2-inch slit in the rock."
                ),
                "repeat": "You're at the slit in the streambed.",
            },
            "exits": {
                "north": "valley",
                "up": "valley",
                "south": "outside_grate",
                "down": {
                    "kind": "message",
                    "journal": "You don't fit through a two-inch slit!",
                },
            },
        },
        "outside_grate": {
            "name": "Outside Grate",
            "traits": ["light", "aboveground", "notfarin"],
            "descriptions": {
                "look": (
                    "You are in a 20-foot depression floored with bare dirt. "
                    "Set into the dirt is a strong steel grate mounted in concrete."
                ),
                "repeat": "You're outside the grate.",
            },
            "exits": {
                "north": "slit_streambed",
                "down": {"through": "grate", "to": "below_grate"},
            },
        },
        "below_grate": {
            "name": "Below the Grate",
            "traits": ["dark", "notfarin"],
            "descriptions": {
                "lit": (
                    "You are in a small chamber beneath a 3x3 steel grate to "
                    "the surface."
                ),
                "dark": (
                    "It is now pitch dark. If you proceed you will likely fall "
                    "into a pit."
                ),
                "repeat": "You're below the grate.",
            },
            "exits": {
                "up": {"through": "grate", "to": "outside_grate"},
                "west": "cobble_crawl",
            },
        },
        "cobble_crawl": {
            "name": "In Cobble Crawl",
            "traits": ["dark", "dwarfroom"],
            "descriptions": {
                "lit": (
                    "You are crawling over cobbles in a low passage. There is a "
                    "dim light at the east end of the passage."
                ),
                "dark": (
                    "It is now pitch dark. If you proceed you will likely fall "
                    "into a pit."
                ),
                "repeat": "You're in the cobble crawl.",
            },
            "exits": {"east": "below_grate"},
        },
    },
    "assets": {
        "keys": {
            "name": "set of keys",
            "kind": "keyring",
            "traits": ["portable", "tiny"],
            "initial": {"location": "building"},
            "descriptions": {"examine": "It's just a normal-looking set of keys."},
        },
        "brass_lamp": {
            "name": "brass lantern",
            "kind": "lamp",
            "traits": ["portable", "switchable", "provides_light", "requires_charge"],
            "initial": {
                "location": "building",
                "state": {"lit": False, "charge": 330},
            },
            "descriptions": {"examine": "It is a shiny brass lamp."},
        },
    },
    "fixtures": {
        "grate": {
            "name": "steel grate",
            "kind": "door",
            "traits": ["fixture", "door", "openable", "lockable"],
            "initial": {
                "locations": ["outside_grate", "below_grate"],
                "state": {"locked": True, "open": False},
            },
            "key": "keys",
            "connects": {
                "outside_grate": "below_grate",
                "below_grate": "outside_grate",
            },
        },
    },
}


class AdventureItemType(AssetType):
    """Test asset type used by the hand-compiled Adventure slice."""

    name: str = ""
    kind: str = ""
    portable: bool = True
    light_source: bool = False
    lit: bool = Field(default=False, json_schema_extra={"instance_var": True})
    charge: int | None = Field(default=None, json_schema_extra={"instance_var": True})
    turn_on_text: str | None = None
    turn_off_text: str | None = None


@pytest.fixture(autouse=True)
def _clear_adventure_item_types() -> None:
    AdventureItemType.clear_instances()
    yield
    AdventureItemType.clear_instances()


def _compile_adventure_slice(
    spec: dict[str, Any],
) -> tuple[
    StoryGraph,
    SandboxScope,
    dict[str, SandboxLocation],
    dict[str, Token],
    dict[str, SandboxLockable],
]:
    graph = StoryGraph(label=spec["id"])
    scope = SandboxScope(
        label=spec["scope"]["id"],
        locals=dict(spec["scope"].get("state", {})),
        visibility_rules=[
            SandboxVisibilityRule(
                journal_text="It is now pitch dark. If you proceed you will likely fall into a pit."
            )
        ],
    )
    graph.add(scope)

    locations: dict[str, SandboxLocation] = {}
    for label, payload in spec["locations"].items():
        descriptions = payload.get("descriptions", {})
        traits = set(payload.get("traits", ()))
        location = SandboxLocation(
            label=label,
            location_name=payload["name"],
            sandbox_scope=scope.get_label(),
            light="light" in traits,
            content=descriptions.get("lit") or descriptions.get("look", ""),
            dark_text=descriptions.get("dark"),
        )
        location.links = {
            direction: _compile_exit(exit_spec)
            for direction, exit_spec in payload.get("exits", {}).items()
        }
        graph.add(location)
        scope.add_child(location)
        locations[label] = location

    assets: dict[str, Token] = {}
    for label, payload in spec["assets"].items():
        traits = set(payload.get("traits", ()))
        initial = payload.get("initial", {})
        state = initial.get("state", {})
        AdventureItemType(
            label=label,
            name=payload["name"],
            kind=payload.get("kind", ""),
            portable="portable" in traits,
            light_source="provides_light" in traits,
            lit=bool(state.get("lit", False)),
            charge=state.get("charge"),
            turn_on_text=f"Your {payload['name']} is now on.",
            turn_off_text=f"Your {payload['name']} is now off.",
        )
        asset = Token[AdventureItemType](token_from=label, label=label)
        graph.add(asset)
        locations[initial["location"]].add_asset(asset)
        assets[label] = asset

    fixtures: dict[str, SandboxLockable] = {}
    for label, payload in spec["fixtures"].items():
        traits = set(payload.get("traits", ()))
        state = payload.get("initial", {}).get("state", {})
        fixture = SandboxLockable(
            label=label,
            name=payload["name"],
            key=payload.get("key", "key"),
            locked=bool(state.get("locked", False)),
            open=bool(state.get("open", False)),
            openable="openable" in traits,
            unlock_text="The key turns with a click. The grate unlocks.",
            open_text="The grate opens.",
            close_text="The grate closes.",
        )
        for location_label in payload.get("initial", {}).get("locations", ()):
            locations[location_label].lockables.append(fixture)
        fixtures[label] = fixture

    return graph, scope, locations, assets, fixtures


def _compile_exit(payload: str | dict[str, Any]) -> str | SandboxExit:
    if isinstance(payload, str):
        return payload
    if payload.get("kind") == "message":
        return SandboxExit(kind="message", journal_text=payload["journal"])
    return SandboxExit(
        target=payload["to"],
        through=payload.get("through"),
        text=payload.get("text"),
    )


def _provision_current(ledger: Ledger) -> SandboxLocation:
    location = ledger.cursor
    assert isinstance(location, SandboxLocation)
    do_provision(location, ctx=PhaseCtx(graph=ledger.graph, cursor_id=location.uid))
    return location


def _sandbox_actions(location: SandboxLocation) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox"}.issubset(getattr(edge, "tags", set()) or set())
    ]


def _choose(ledger: Ledger, **hints: str) -> Action:
    location = _provision_current(ledger)
    for action in _sandbox_actions(location):
        if all(action.ui_hints.get(key) == value for key, value in hints.items()):
            ledger.resolve_choice(action.uid, choice_payload=action.payload)
            return action
    raise AssertionError(f"No sandbox action at {location.get_label()} matched {hints!r}")


def _choice_fragments(location: SandboxLocation, graph: StoryGraph) -> list[ChoiceFragment]:
    ctx = PhaseCtx(graph=graph, cursor_id=location.uid)
    do_provision(location, ctx=ctx)
    return [
        fragment
        for fragment in render_block_choices(caller=location, ctx=ctx) or []
        if isinstance(fragment, ChoiceFragment)
    ]


def test_adventure_slice_hand_compiles_core_walkthrough() -> None:
    graph, _scope, locations, assets, fixtures = _compile_adventure_slice(
        ADVENTURE_SANDBOX_SLICE
    )
    ledger = Ledger.from_graph(graph, entry_id=locations["road"].uid)

    _choose(ledger, contribution="movement", direction="east")
    _choose(ledger, contribution="take", asset="keys")
    _choose(ledger, contribution="take", asset="brass_lamp")
    _choose(ledger, contribution="light", asset="brass_lamp", verb="turn_on")
    _choose(ledger, contribution="movement", direction="west")
    _choose(ledger, contribution="movement", direction="south")
    _choose(ledger, contribution="movement", direction="south")
    _choose(ledger, contribution="movement", direction="south")

    down_choices = _choice_fragments(locations["outside_grate"], graph)
    down = next(
        choice
        for choice in down_choices
        if choice.ui_hints.get("direction") == "down"
    )
    assert down.available is False
    assert down.ui_hints["through"] == "grate"

    _choose(ledger, contribution="unlock", target="grate")
    _choose(ledger, contribution="open", target="grate")
    _choose(ledger, contribution="movement", direction="down")
    _choose(ledger, contribution="movement", direction="west")

    assert ledger.cursor is locations["cobble_crawl"]
    assert assets["brass_lamp"].lit is True
    assert fixtures["grate"].locked is False
    assert fixtures["grate"].open is True
