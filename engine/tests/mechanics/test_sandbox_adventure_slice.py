"""Hand-compiled Adventure sandbox slice over generic sandbox mechanics."""

from __future__ import annotations

from typing import Any

import pytest

from tangl.core import Selector
from tangl.mechanics.sandbox import (
    SandboxCompiledAssetType,
    SandboxCompiledSlice,
    SandboxLocation,
    SandboxMaterializationSpec,
    SandboxMob,
    SandboxSliceCompiler,
    SandboxSliceSpec,
)
from tangl.story import Action, StoryGraph
from tangl.story.fragments import ChoiceFragment, ContentFragment
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
    "scope": {
        "id": "cave",
        "state": {"world_turn": 0},
        "visibility": {
            "darkness_text": (
                "It is now pitch dark. If you proceed you will likely fall "
                "into a pit."
            )
        },
        "materialization": {
            "policy": "mixed",
            "stable": {
                "locations": ["cobble_crawl"],
                "assets": ["brass_lamp"],
                "fixtures": ["grate"],
                "mobs": ["wounded_pirate"],
            },
            "notes": "Pirate-style offscreen state needs stable runtime homes.",
        },
    },
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
            "runtime_identity": {"stable": True},
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
        },
    },
    "mobs": {
        "wounded_pirate": {
            "name": "wounded pirate",
            "kind": "mobile_actor",
            "traits": ["mobile", "audible_nearby", "can_carry"],
            "initial": {
                "location": "cobble_crawl",
                "state": {"hp": 3, "injured": True, "hostile": False},
            },
            "descriptions": {
                "present": "A wounded pirate leans against the wall, watching you.",
                "nearby": "You hear someone breathing raggedly nearby.",
            },
            "contributes": {
                "affordances": {
                    "help": {
                        "text": "Make sure the wounded pirate is okay",
                        "journal": (
                            "The pirate eyes you suspiciously, but accepts your help."
                        ),
                        "state": {"helped": True, "hostile": False},
                    }
                }
            },
            "runtime_identity": {"stable": True},
        },
    },
}


@pytest.fixture(autouse=True)
def _clear_adventure_item_types() -> None:
    SandboxCompiledAssetType.clear_instances()
    yield
    SandboxCompiledAssetType.clear_instances()


def _provision_current(ledger: Ledger) -> SandboxLocation:
    location = ledger.cursor
    assert isinstance(location, SandboxLocation)
    do_provision(location, ctx=PhaseCtx(graph=ledger.graph, cursor_id=location.uid))
    return location


def _sandbox_actions(location: SandboxLocation) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox"}.issubset(edge.tags)
    ]


def _choose(ledger: Ledger, **hints: str) -> Action:
    location = _provision_current(ledger)
    for action in _sandbox_actions(location):
        if all(action.ui_hints.get(key) == value for key, value in hints.items()):
            ledger.resolve_choice(action.uid, choice_payload=action.payload)
            return action
    raise AssertionError(
        f"No sandbox action at {location.get_label()} matched {hints!r}"
    )


def _choice_fragments(location: SandboxLocation, graph: StoryGraph) -> list[ChoiceFragment]:
    ctx = PhaseCtx(graph=graph, cursor_id=location.uid)
    do_provision(location, ctx=ctx)
    return [
        fragment
        for fragment in render_block_choices(caller=location, ctx=ctx) or []
        if isinstance(fragment, ChoiceFragment)
    ]


def test_adventure_slice_schema_validates() -> None:
    spec = SandboxSliceCompiler.validate_ir(ADVENTURE_SANDBOX_SLICE)

    assert isinstance(spec, SandboxSliceSpec)
    assert spec.locations["outside_grate"].exits["down"].through == "grate"
    assert spec.locations["building"].exits["in"].kind == "message"
    assert spec.scope.materialization.policy == "mixed"
    assert spec.scope.materialization.stable.locations == ["cobble_crawl"]
    assert spec.scope.materialization.stable.mobs == ["wounded_pirate"]
    assert spec.locations["cobble_crawl"].runtime_identity.stable is True
    assert spec.mobs["wounded_pirate"].initial.location == "cobble_crawl"
    assert spec.mobs["wounded_pirate"].runtime_identity.stable is True


def test_adventure_slice_compiler_rejects_unknown_exit_target() -> None:
    data: dict[str, Any] = {
        "id": "bad_exits",
        "scope": {"id": "cave"},
        "locations": {
            "road": {
                "name": "Road",
                "exits": {"north": "missing_room"},
            },
        },
    }

    with pytest.raises(
        ValueError,
        match="Location 'road' exit 'north' targets unknown sandbox location 'missing_room'",
    ):
        SandboxSliceCompiler().compile(data)


def test_adventure_slice_compiler_rejects_conflicting_asset_type_reuse() -> None:
    first: dict[str, Any] = {
        "id": "first_keys",
        "scope": {"id": "cave"},
        "locations": {"building": {"name": "Building"}},
        "assets": {
            "keys": {
                "name": "set of keys",
                "traits": ["portable"],
                "initial": {"location": "building"},
            },
        },
    }
    second: dict[str, Any] = {
        "id": "second_keys",
        "scope": {"id": "cave"},
        "locations": {"building": {"name": "Building"}},
        "assets": {
            "keys": {
                "name": "brass key",
                "traits": ["portable"],
                "initial": {"location": "building"},
            },
        },
    }

    compiler = SandboxSliceCompiler()
    compiler.compile(first)

    with pytest.raises(
        ValueError,
        match="Sandbox asset type 'keys' is already registered with a different definition",
    ):
        compiler.compile(second)


def test_adventure_slice_compiler_preserves_provenance_inputs() -> None:
    compiled = SandboxSliceCompiler().compile(
        ADVENTURE_SANDBOX_SLICE,
        source_map={"source_refs": ADVENTURE_SANDBOX_SLICE["source"]},
        codec_state={"codec_id": "compact_sandbox_slice"},
    )

    assert isinstance(compiled, SandboxCompiledSlice)
    assert isinstance(compiled.materialization, SandboxMaterializationSpec)
    assert isinstance(compiled.mobs["wounded_pirate"], SandboxMob)
    assert compiled.materialization.stable.assets == ["brass_lamp"]
    assert compiled.source_map["source_refs"]["kind"] == "punyinform"
    assert compiled.codec_state["codec_id"] == "compact_sandbox_slice"


def test_adventure_slice_stable_mob_projects_only_when_present() -> None:
    compiled = SandboxSliceCompiler().compile(ADVENTURE_SANDBOX_SLICE)
    road = compiled.locations["road"]
    cobble = compiled.locations["cobble_crawl"]
    pirate = compiled.mobs["wounded_pirate"]

    assert pirate.location == "cobble_crawl"
    assert pirate.state["injured"] is True
    assert pirate.uid is not None

    do_provision(road, ctx=PhaseCtx(graph=compiled.graph, cursor_id=road.uid))
    assert [
        action
        for action in _sandbox_actions(road)
        if action.ui_hints.get("mob") == "wounded_pirate"
    ] == []

    cobble.light = True
    do_provision(cobble, ctx=PhaseCtx(graph=compiled.graph, cursor_id=cobble.uid))
    mob_actions = [
        action
        for action in _sandbox_actions(cobble)
        if action.ui_hints.get("mob") == "wounded_pirate"
    ]

    assert [action.text for action in mob_actions] == [
        "Make sure the wounded pirate is okay"
    ]


def test_adventure_slice_compiler_runs_core_walkthrough() -> None:
    compiled = SandboxSliceCompiler().compile(ADVENTURE_SANDBOX_SLICE)
    graph = compiled.graph
    locations = compiled.locations
    assets = compiled.assets
    fixtures = compiled.fixtures
    mobs = compiled.mobs
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
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert "A wounded pirate leans against the wall, watching you." in content

    _choose(ledger, contribution="mob", mob="wounded_pirate", action="help")

    assert assets["brass_lamp"].lit is True
    assert fixtures["grate"].locked is False
    assert fixtures["grate"].open is True
    assert mobs["wounded_pirate"].state["helped"] is True
