"""Static sandbox binding at story construction, distinct from live arrival."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from tangl.core import DispatchLayer, Selector
from tangl.core.behavior import Priority
from tangl.journal.fragments import ChoiceFragment
from tangl.mechanics.sandbox import SandboxLocation, SandboxScope, ScheduledEvent
from tangl.story import Action, InitMode, StoryGraph, World
from tangl.story.dispatch import do_story_materialized
from tangl.vm import Dependency, Ledger
from tangl.vm.dispatch import do_journal, do_provision
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


@pytest.mark.parametrize("layer", [DispatchLayer.APPLICATION, DispatchLayer.AUTHOR])
def test_static_binding_runs_after_world_ready_setup(layer: DispatchLayer) -> None:
    world = World.from_script_data(script_data=_script(f"ready_setup_{layer.name}"))

    @world.dispatch.register(
        task="story_ready",
        wants_caller_kind=StoryGraph,
        dispatch_layer=layer,
        priority=Priority.LAST,
    )
    def setup(*, caller: StoryGraph, **kwargs) -> None:
        start = caller.find_one(Selector(has_kind=SandboxLocation, label="start"))
        scope = caller.find_one(Selector(has_kind=SandboxScope))
        start.scheduled_events[0] = ScheduledEvent(
            label="now", target="hub.target", text="Rewritten",
        )
        scope.scheduled_events.append(
            ScheduledEvent(label="added", target="hub.target", text="Added"),
        )

    result = world.create_story("run", freeze_shape=True)
    graph = result.graph
    start = graph.get(graph.initial_cursor_id)
    alternate = graph.find_one(Selector(has_kind=SandboxLocation, label="alternate"))
    assert set(_offers(start)) == {"Rewritten", "Added", "Later"}
    assert set(_offers(alternate)) == {"Added", "Later"}
    assert result.report.materialized_counts["Action"] == 5
    assert graph.locals["arrivals"] == 0
    do_provision(start, ctx=PhaseCtx(graph=graph, cursor_id=start.uid))
    assert _offers(start)["Rewritten"].available(ctx=PhaseCtx(graph=graph, cursor_id=start.uid))


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
    start = graph.get(graph.initial_cursor_id)
    assert isinstance(start, SandboxLocation)
    assert set(_offers(start)) == {"Now", "Later"}
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    ids = {text: action.uid for text, action in _offers(start).items()}
    dependencies = list(graph.find_all(Selector(has_kind=Dependency, label="destination")))
    assert len(dependencies) == 2
    assert all(action.successor is None for action in _offers(start).values())
    fragments = do_journal(start, ctx=ctx)
    choices = {
        fragment.text: fragment
        for fragment in fragments
        if isinstance(fragment, ChoiceFragment)
    }
    assert choices["Now"].available
    assert not choices["Later"].available
    do_provision(start, ctx=ctx)
    assert {text: action.uid for text, action in _offers(start).items()} == ids
    assert list(graph.find_all(Selector(has_kind=Dependency, label="destination"))) == dependencies
    assert graph.find_one(Selector(label="target")) is None


def test_materialized_receiver_respects_automatic_provisioning_opt_out() -> None:
    script = _script("lazy_receiver")
    script["scenes"]["hub"]["blocks"]["start"]["actions"] = [
        {"text": "Move", "successor": "hub.alternate"},
    ]
    script["scenes"]["hub"]["blocks"]["alternate"]["auto_provision"] = False
    # The topology hook must honor the opt-out, not rely on a later PLANNING pass.
    world = World.from_script_data(script_data=script)
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    ledger = Ledger.from_graph(graph)
    (move,) = ledger.cursor.edges_out(Selector(has_kind=Action, text="Move"))
    ledger.resolve_choice(move.uid)
    assert ledger.cursor.get_label() == "alternate"
    assert not _offers(ledger.cursor)


def test_lazy_nested_scope_and_receiver_bind_before_their_first_planning_pass() -> None:
    script = _script("lazy_nested_scope")
    script["scenes"]["hub"]["blocks"]["start"]["actions"] = [
        {"text": "Move", "successor": "annex.entry"},
    ]
    script["scenes"]["annex"] = {
        "kind": SandboxScope,
        "scheduled_events": [{"label": "scope", "target": "annex.target", "text": "Scope"}],
        "blocks": {
            "entry": {
                "kind": SandboxLocation,
                "scheduled_events": [{"label": "local", "target": "current", "text": "Local"}],
            },
            "target": {"content": "Annex target"},
        },
    }
    world = World.from_script_data(script_data=script)
    seen = []

    @world.dispatch.register(task="story_materialized", wants_caller_kind=SandboxLocation)
    def observe(*, caller: SandboxLocation, **kwargs) -> None:
        seen.append((caller.get_label(), set(_offers(caller))))

    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    assert graph.find_one(Selector(label="annex")) is None
    ledger = Ledger.from_graph(graph)
    ledger.save_snapshot()
    (move,) = ledger.cursor.edges_out(Selector(has_kind=Action, text="Move"))
    ledger.resolve_choice(move.uid)
    assert ("entry", {"Scope", "Local"}) in seen
    assert set(_offers(ledger.cursor)) == {"Scope", "Local"}
    assert graph.find_one(Selector(has_path="annex.target")) is None
    ids = {text: action.uid for text, action in _offers(ledger.cursor).items()}
    receiver_step = ledger.cursor_steps
    restored = Ledger.structure(ledger.unstructure())
    assert {text: action.uid for text, action in _offers(restored.cursor).items()} == ids
    restored.resolve_choice(ids["Scope"])
    assert restored.cursor.path == "annex.target"
    restored.rollback_to_step(receiver_step, reason="replay lazy receiver")
    assert {text: action.uid for text, action in _offers(restored.cursor).items()} == ids
    assert restored.graph.find_one(Selector(has_path="annex.target")) is None


def test_lazy_offer_target_selection_and_once_gate_survive_restore_and_replay() -> None:
    script = _script("lazy_once_replay")
    script["scenes"]["hub"]["blocks"]["start"]["scheduled_events"][0]["once"] = True
    world = World.from_script_data(script_data=script)
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    ledger = Ledger.from_graph(graph)
    ledger.save_snapshot()
    action = _offers(ledger.cursor)["Now"]
    assert action.once and action.successor is None
    restored = Ledger.structure(ledger.unstructure())
    restored.resolve_choice(action.uid)
    assert restored.cursor.get_label() == "target"
    restored_action = restored.graph.get(action.uid)
    assert restored_action.successor is restored.cursor
    assert not restored_action.available(ctx=restored._make_phase_ctx())
    restored.rollback_to_step(0, reason="repeat lazy offer")
    assert restored.graph.get(action.uid).successor is None
    restored.resolve_choice(action.uid)
    assert restored.cursor.get_label() == "target"


def test_removing_a_pending_static_offer_also_removes_its_destination_dependency() -> None:
    graph = World.from_script_data(script_data=_script("lazy_prune")).create_story(
        "run", init_mode=InitMode.LAZY,
    ).graph
    start = graph.get(graph.initial_cursor_id)
    action = _offers(start)["Now"]
    (dependency,) = graph.find_edges(
        Selector(has_kind=Dependency, predecessor_id=action.uid, label="destination"),
    )
    start.scheduled_events.clear()
    do_provision(start, ctx=PhaseCtx(graph=graph, cursor_id=start.uid))
    assert graph.get(action.uid) is None
    assert graph.get(dependency.uid) is None
    assert "Later" in _offers(start)


def test_pending_once_offer_reuses_a_target_realized_by_another_offer() -> None:
    script = _script("lazy_shared_target")
    script["scenes"]["hub"]["scheduled_events"][0].pop("period")
    script["scenes"]["hub"]["scheduled_events"][0]["once"] = True
    script["scenes"]["hub"]["blocks"]["start"]["scheduled_events"][0]["return_to_location"] = True
    ledger = Ledger.from_graph(World.from_script_data(script_data=script).create_story(
        "run", init_mode=InitMode.LAZY,
    ).graph)
    offers = _offers(ledger.cursor)
    later_id = offers["Later"].uid
    (dependency,) = ledger.graph.find_edges(
        Selector(has_kind=Dependency, predecessor_id=later_id, label="destination"),
    )
    ledger.resolve_choice(offers["Now"].uid)
    assert ledger.cursor.get_label() == "start"
    later = _offers(ledger.cursor)["Later"]
    assert later.uid == later_id
    assert later.successor is _offers(ledger.cursor)["Now"].successor
    assert dependency.successor is later.successor
    assert not later.available(ctx=ledger._make_phase_ctx())


@pytest.mark.parametrize(
    "reference, destination", [("target", "hub.target"), ("other", "other.target")],
)
def test_lazy_short_target_uses_normal_scoped_destination_resolution(
    reference: str, destination: str,
) -> None:
    script = _script(f"lazy_scoped_{reference}")
    script["scenes"]["hub"]["blocks"]["start"]["scheduled_events"][0]["target"] = reference
    script["scenes"]["other"] = {"blocks": {"target": {"content": "Wrong target"}}}
    graph = World.from_script_data(script_data=script).create_story(
        "run", init_mode=InitMode.LAZY,
    ).graph
    ledger = Ledger.from_graph(graph)
    ledger.resolve_choice(_offers(ledger.cursor)["Now"].uid)
    assert ledger.cursor.path == destination
    absent = "other.target" if reference == "target" else "hub.target"
    assert graph.find_one(Selector(has_path=absent)) is None


def test_materialized_handlers_cannot_return_narrative_output() -> None:
    script = _script("materialized_output")
    world = World.from_script_data(script_data=script)
    world.dispatch.register(task="story_materialized", func=lambda **kwargs: "Not a journal")
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    with pytest.raises(TypeError, match="story_materialized handlers must return None"):
        do_story_materialized(ledger.cursor, ctx=ledger._make_phase_ctx())


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
