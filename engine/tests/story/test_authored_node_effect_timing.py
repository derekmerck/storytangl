"""Authored scene and block effects lower into VM's phase-tagged effect list."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tangl.ir.story_ir import StoryScript
from tangl.story import InitMode
from tangl.story.fabula.compiler import StoryCompiler
from tangl.story.fabula.world import World
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.traversable import TraversableEffect


def _script(**start: object) -> dict[str, object]:
    return {
        "label": "node_effect_timing",
        "metadata": {
            "title": "Node effect timing",
            "author": "Tests",
            "start_at": "s.start",
        },
        "globals": {"sword": "sheathed"},
        "scenes": {
            "s": {
                "blocks": {
                    "start": {
                        "content": "The sword is {sword}.",
                        **start,
                    },
                },
            },
        },
    }


def _enter(script: dict[str, object]) -> Ledger:
    world = World.from_script_data(script_data=script)
    graph = world.create_story("node_effect_timing", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    ledger.cursor_id = frame.cursor.uid
    ledger.output_stream = frame.output_stream
    return ledger


def test_authored_node_effects_lower_to_explicit_runtime_phases() -> None:
    script = _script(
        pre_effects=["graph.locals['sword'] = 'drawn'"],
        post_effects=["graph.locals['sword'] = 'discarded'"],
    )
    validated = StoryCompiler.validate_ir(script)
    start_ir = validated.scenes["s"].blocks["start"]
    assert start_ir.pre_effects == ["graph.locals['sword'] = 'drawn'"]
    assert start_ir.post_effects == ["graph.locals['sword'] = 'discarded'"]

    world = World.from_script_data(
        script_data=validated.model_dump(by_alias=True, exclude_none=True),
    )
    graph = world.create_story("node_effect_timing", init_mode=InitMode.EAGER).graph
    start = graph.get(graph.initial_cursor_id)

    assert start.effects == [
        TraversableEffect(
            expr="graph.locals['sword'] = 'drawn'",
            trigger_phase=ResolutionPhase.UPDATE,
        ),
        TraversableEffect(
            expr="graph.locals['sword'] = 'discarded'",
            trigger_phase=ResolutionPhase.FINALIZE,
        ),
    ]


def test_authored_pre_and_post_effects_bracket_journal() -> None:
    ledger = _enter(
        _script(
            pre_effects=["graph.locals['sword'] = 'drawn'"],
            post_effects=["graph.locals['sword'] = 'discarded'"],
        ),
    )

    text = [getattr(record, "content", "") for record in ledger.output_stream]
    assert "The sword is drawn." in text
    assert ledger.graph.locals["sword"] == "discarded"


def test_block_effect_timing_round_trips_through_decompile() -> None:
    source = _script(
        pre_effects=[
            "graph.locals['sword'] = 'drawn'",
            "graph.locals['sword'] = 'ready'",
        ],
        post_effects=[
            "graph.locals['sword'] = 'discarded'",
            "graph.locals['sword'] = 'stored'",
        ],
    )
    compiler = StoryCompiler()
    canonical = compiler.decompile(compiler.compile(source))
    restored = compiler.compile(canonical)

    block = canonical["scenes"]["s"]["blocks"]["start"]
    assert block["effects"] == [
        {"expr": "graph.locals['sword'] = 'drawn'"},
        {"expr": "graph.locals['sword'] = 'ready'"},
    ]
    assert block["post_effects"] == [
        {"expr": "graph.locals['sword'] = 'discarded'"},
        {"expr": "graph.locals['sword'] = 'stored'"},
    ]
    assert restored.issues == []

    ledger = _enter(canonical)
    text = [getattr(record, "content", "") for record in ledger.output_stream]
    assert "The sword is ready." in text
    assert ledger.graph.locals["sword"] == "stored"


def test_effects_remains_the_pre_effects_alias() -> None:
    world = World.from_script_data(
        script_data=_script(effects=["graph.locals['sword'] = 'drawn'"]),
    )
    graph = world.create_story("node_effect_timing", init_mode=InitMode.EAGER).graph
    start = graph.get(graph.initial_cursor_id)

    assert start.effects == [
        TraversableEffect(
            expr="graph.locals['sword'] = 'drawn'",
            trigger_phase=ResolutionPhase.UPDATE,
        ),
    ]


def test_effects_and_pre_effects_conflict_fails_loudly() -> None:
    script = _script(effects=["x = 1"], pre_effects=["x = 2"])

    with pytest.raises(ValidationError, match="either 'effects' or 'pre_effects'"):
        StoryScript.model_validate(script)
    with pytest.raises(ValueError, match="either 'effects' or 'pre_effects'"):
        World.from_script_data(script_data=script)


def test_authored_trigger_phase_fails_loudly_instead_of_being_dropped() -> None:
    script = _script(
        effects=[
            {
                "expr": "graph.locals['sword'] = 'discarded'",
                "trigger_phase": "finalize",
            },
        ],
    )

    with pytest.raises(ValueError, match="pre_effects.*post_effects"):
        World.from_script_data(script_data=script)
