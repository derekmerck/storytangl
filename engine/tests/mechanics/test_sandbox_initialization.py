"""Static sandbox binding at story construction, distinct from live arrival."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from tangl.core import Selector
from tangl.mechanics.sandbox import SandboxLocation, SandboxScope, ScheduledEvent
from tangl.story import Action, InitMode, StoryGraph, World
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


def _script(label: str) -> dict:
    return {
        "label": label,
        "metadata": {"start_at": "hub.start"},
        "locals": {"arrivals": 0},
        "scenes": {
            "hub": {
                "kind": SandboxScope,
                "locals": {"world_turn": 0},
                "scheduled_events": [
                    {"label": "later", "period": 3, "target": "hub.target", "text": "Later"},
                ],
                "blocks": {
                    "start": {
                        "kind": SandboxLocation,
                        "effects": [{"expr": "arrivals += 1"}],
                        "scheduled_events": [
                            {"label": "now", "target": "hub.target", "text": "Now"},
                        ],
                    },
                    "alternate": {"kind": SandboxLocation},
                    "target": {"content": "The event begins."},
                },
            },
        },
    }


def _offers(location: SandboxLocation) -> dict[str, Action]:
    return {
        action.text: action
        for action in location.edges_out(Selector(has_kind=Action, has_tags={"event"}))
    }


@pytest.mark.parametrize("frozen", [False, True])
def test_eager_setup_establishes_all_static_offers_without_arrival(frozen: bool) -> None:
    world = World.from_script_data(script_data=_script(f"setup_frozen_{frozen}"))
    result = world.create_story("run", freeze_shape=frozen)
    graph = result.graph
    start = graph.find_one(Selector(has_kind=SandboxLocation, label="start"))
    alternate = graph.find_one(Selector(has_kind=SandboxLocation, label="alternate"))
    scope = graph.find_one(Selector(has_kind=SandboxScope))
    assert isinstance(start, SandboxLocation)
    assert isinstance(alternate, SandboxLocation)
    assert isinstance(scope, SandboxScope)
    assert graph.frozen_shape is frozen
    assert graph.locals["arrivals"] == 0
    assert scope.locals["world_turn"] == 0
    assert set(_offers(start)) == {"Now", "Later"}
    assert set(_offers(alternate)) == {"Later"}
    assert result.report.materialized_counts["Action"] == 3

    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    original_ids = {text: action.uid for text, action in _offers(start).items()}
    assert _offers(start)["Now"].available(ctx=ctx)
    assert not _offers(start)["Later"].available(ctx=ctx)
    scope.locals["world_turn"] = 2
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    do_provision(start, ctx=ctx)
    assert _offers(start)["Later"].available(ctx=ctx)
    assert {text: action.uid for text, action in _offers(start).items()} == original_ids


class EntryPreferenceWorld(World):
    """World-local setup chooses a start and contributes that start's known offer."""

    def _resolve_entry_override(
        self, graph: StoryGraph, namespace: dict[str, Any],
    ) -> UUID:
        label = "alternate" if namespace["ng_plus"] else "start"
        location = graph.find_one(Selector(has_kind=SandboxLocation, label=label))
        assert isinstance(location, SandboxLocation)
        location.scheduled_events.append(
            ScheduledEvent(label="arrival", target="hub.target", text=namespace["look"])
        )
        return location.uid


def test_ready_hook_observes_each_selected_start_without_reusing_another_run() -> None:
    world = EntryPreferenceWorld.from_script_data(script_data=_script("entry_preferences"))
    seen = []

    @world.dispatch.register(task="story_ready")
    def observe(
        *, caller: StoryGraph, ctx: PhaseCtx, namespace: dict[str, Any], init_mode: InitMode,
    ) -> None:
        seen.append((ctx.cursor.get_label(), namespace["look"], init_mode, caller.frozen_shape))

    first = world.create_story(
        "first", freeze_shape=True, namespace={"ng_plus": False, "look": "Day"},
    )
    second = world.create_story(
        "second", freeze_shape=True, namespace={"ng_plus": True, "look": "Night"},
    )
    assert first.graph is not second.graph
    assert seen == [
        ("start", "Day", InitMode.EAGER, True),
        ("alternate", "Night", InitMode.EAGER, True),
    ]
    first_entry = first.graph.get(first.graph.initial_cursor_id)
    second_entry = second.graph.get(second.graph.initial_cursor_id)
    assert isinstance(first_entry, SandboxLocation)
    assert isinstance(second_entry, SandboxLocation)
    assert "Day" in _offers(first_entry) and "Night" not in _offers(first_entry)
    assert "Night" in _offers(second_entry) and "Day" not in _offers(second_entry)


def test_frozen_setup_bindings_survive_restore_and_replay() -> None:
    world = World.from_script_data(script_data=_script("frozen_replay"))
    graph = world.create_story("run", freeze_shape=True).graph
    ledger = Ledger.from_graph(graph)
    ledger.save_snapshot()
    (action,) = ledger.cursor.edges_out(Selector(has_kind=Action, text="Now"))
    restored = Ledger.structure(ledger.unstructure())
    restored.resolve_choice(action.uid)
    assert restored.cursor.get_label() == "target"
    restored.rollback_to_step(0, reason="repeat frozen event")
    assert restored.graph.frozen_shape
    assert restored.graph.get(action.uid) is not None
    restored.resolve_choice(action.uid)
    assert restored.cursor.get_label() == "target"


def test_frozen_setup_rejects_a_static_target_that_cannot_be_bound() -> None:
    script = _script("frozen_missing_target")
    script["scenes"]["hub"]["blocks"]["start"]["scheduled_events"][0]["target"] = "missing"
    world = World.from_script_data(script_data=script)
    with pytest.raises(ValueError, match="Frozen story cannot bind scheduled event"):
        world.create_story("run", freeze_shape=True)


def test_lazy_initialization_does_not_force_static_event_targets_eager() -> None:
    world = World.from_script_data(script_data=_script("lazy_setup"))
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    assert graph.find_one(Selector(label="target")) is None
    assert not list(graph.find_all(Selector(has_kind=Action, has_tags={"event"})))


def test_setup_respects_locations_that_disable_automatic_provisioning() -> None:
    script = _script("disabled_setup")
    script["scenes"]["hub"]["blocks"]["start"]["auto_provision"] = False
    graph = World.from_script_data(script_data=script).create_story("run", freeze_shape=True).graph
    start = graph.get(graph.initial_cursor_id)
    assert isinstance(start, SandboxLocation)
    assert not _offers(start)


def test_ready_handlers_cannot_return_narrative_output() -> None:
    world = World.from_script_data(script_data=_script("ready_output"))
    world.dispatch.register(task="story_ready", func=lambda **kwargs: "Not a journal")
    with pytest.raises(TypeError, match="story_ready handlers must return None"):
        world.create_story("run")
