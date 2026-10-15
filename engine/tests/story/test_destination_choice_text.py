"""Deferred choice text uses its owner's live scope without simulating arrival."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.sandbox import SandboxLocation, SandboxScope
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.prose.naming import NamedActor, NamingOperations, get_authorities
from tangl.story import Action, Block, InitMode, MenuBlock, StoryGraph, World
from tangl.story.system_handlers import find_edges_by_command, render_block_choices
from tangl.vm import Dependency, Ledger, ResolutionPhase
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


def _world(*, menu: bool = False) -> World:
    script = {
        "label": "destination_choice_text",
        "metadata": {"start_at": "town.hub"},
        "globals": {"arrivals": 0},
        "actors": {
            "rin": {"kind": NamedActor, "name": "Rin", "anonymous_name": "the blonde girl"},
            "beth": {"kind": NamedActor, "name": "Beth", "anonymous_name": "the dark-haired girl"},
        },
        "scenes": {"town": {
            "kind": SandboxScope,
            "locals": {"world_turn": 0},
            "blocks": {
                "hub": {
                    "kind": SandboxLocation,
                    "roles": {"host": {"actor_ref": "beth"}},
                    "locals": {"text_template": "jinja", "naming_defaults": {"Actor": "proper"}},
                    "scheduled_events": [
                        {"label": "Watch the performance", "target": "performance"},
                        {"label": "Explicit", "target": "performance",
                         "text": "{{ reference(host) }} invites you"},
                        {"label": "Public fallback", "target": "plain"},
                        {"target": "plain"},
                    ],
                },
                "performance": {
                    "roles": {"host": {"actor_ref": "rin"}},
                    "locals": {
                        "text_template": "jinja", "naming_defaults": {"Actor": "concealed"},
                        "action_text": "{{ reference(host) }} is performing ({{ world_turn }})",
                    },
                    "pre_effects": ["arrivals += 1"],
                    "action_name": "Lower priority",
                },
                "plain": {},
            },
        }},
    }
    if menu:
        hub = script["scenes"]["town"]["blocks"]["hub"]
        hub["kind"] = MenuBlock
        del hub["scheduled_events"]
        hub["menu_items"] = {"has_tags": ["activity"]}
        script["scenes"]["town"]["blocks"]["performance"]["tags"] = ["activity"]
    world = World.from_script_data(script_data=script)
    world.extra_authorities.extend(get_authorities())
    return world


def _ctx(graph: StoryGraph, *, narrator: str = "reader") -> PhaseCtx:
    return PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id,
                    current_phase=ResolutionPhase.JOURNAL, meta={"narrator_key": narrator})


def _texts(ctx: PhaseCtx) -> dict[UUID, str]:
    return {choice.edge_id: choice.text
            for choice in render_block_choices(caller=ctx.cursor, ctx=ctx)}


def _events(ctx: PhaseCtx) -> dict[str, Action]:
    return {edge.fallback_text: edge for edge in ctx.cursor.edges_out(
        Selector(has_kind=Action, has_tags={"event"}),
    )}


def test_retained_event_reads_destination_scope_live_without_reprojection_or_arrival() -> None:
    graph = _world().create_story("run").graph
    ctx = _ctx(graph)
    events = _events(ctx)
    edge = events["Watch the performance"]
    authored = edge.successor.locals["action_text"]
    # Gather the conflicting source first, proving cached helpers cannot leak.
    assert ctx.get_ns(ctx.cursor)["host"].name == "Beth"
    before = graph.value_hash()
    texts = _texts(ctx)
    assert texts[edge.uid] == "the blonde girl is performing (0)"
    assert texts[events["Explicit"].uid] == "Beth invites you"
    assert texts[events["Public fallback"].uid] == "Public fallback"
    assert texts[events["plain"].uid] == "plain"
    assert find_edges_by_command(caller=ctx.cursor, ctx=ctx, query={
        "kind": "command", "command": texts[edge.uid],
    }) == [edge]
    assert graph.value_hash() == before
    rin = graph.find_one(Selector(has_kind=NamedActor, label="rin"))
    assert rin.narrator_knowledge == {}
    assert graph.locals["arrivals"] == 0
    NamingOperations(ctx).introduce(rin)
    scope = graph.find_one(Selector(has_kind=SandboxScope))
    scope.locals["world_turn"] = 1
    identified = graph.value_hash()
    assert _texts(ctx)[edge.uid] == "Rin is performing (1)"
    assert _texts(_ctx(graph, narrator="other"))[edge.uid] == "the blonde girl is performing (1)"
    assert graph.value_hash() == identified
    assert _events(ctx)["Watch the performance"] is edge
    assert edge.text == "" and edge.successor.locals["action_text"] == authored


@pytest.mark.parametrize("explicit", [False, True])
def test_standard_introduction_in_display_fails_before_knowledge_mutation(explicit: bool) -> None:
    graph = _world().create_story("run").graph
    ctx = _ctx(graph)
    edge = _events(ctx)["Watch the performance"]
    if explicit:
        edge.text = "{{ introduce(host) }}"
    else:
        edge.successor.locals["action_text"] = "{{ introduce(host) }}"
    before = graph.value_hash()
    with pytest.raises(RuntimeError, match="Introductions require"):
        _texts(ctx)
    assert graph.value_hash() == before
    assert all(actor.narrator_knowledge == {} for actor in graph.find_all(
        Selector(has_kind=NamedActor),
    ))


@pytest.mark.parametrize("json_wire", [False, True])
def test_constructor_restore_preserves_explicit_deferred_and_fallback_distinction(
    json_wire: bool,
) -> None:
    graph = _world().create_story("run").graph
    ledger = Ledger.from_graph(graph)
    events = _events(_ctx(graph))
    original = {label: (edge.uid, edge.text, edge.fallback_text) for label, edge in events.items()}
    data = ledger.unstructure()
    if json_wire:
        data = JsonSerializationHandler.deserialize(JsonSerializationHandler.serialize(data))
    restored = Ledger.structure(data)
    ctx = _ctx(restored.graph)
    assert {label: (edge.uid, edge.text, edge.fallback_text)
            for label, edge in _events(ctx).items()} == original
    edge = _events(ctx)["Watch the performance"]
    assert _texts(ctx)[edge.uid] == "the blonde girl is performing (0)"
    rin = restored.graph.find_one(Selector(has_kind=NamedActor, label="rin"))
    NamingOperations(ctx).introduce(rin)
    assert _texts(ctx)[edge.uid] == "Rin is performing (0)"
    assert set(restored.graph.members) == set(graph.members)
    destination_ctx = ctx.derive(cursor_id=edge.successor_id)
    assert destination_ctx.get_ns(edge.successor)["host_role"].provider is rin


def test_destination_language_overrides_source_language() -> None:
    graph = _world().create_story("run").graph
    ctx = _ctx(graph)
    edge = _events(ctx)["Watch the performance"]
    target = edge.successor
    target.locals.update(text_template="fstring", action_text="{host.name} performs")
    assert _texts(ctx)[edge.uid] == "Rin performs"
    assert _texts(ctx)[_events(ctx)["Explicit"].uid] == "Beth invites you"


def test_lazy_unrealized_event_uses_static_fallback_without_provisioning() -> None:
    graph = _world().create_story("run", init_mode=InitMode.LAZY).graph
    ctx = _ctx(graph)
    events = _events(ctx)
    edge = events["Watch the performance"]
    assert edge.successor is None
    assert graph.find_one(Selector(label="performance", has_kind=Block)) is None
    assert list(graph.find_all(Selector(has_kind=Dependency, label="destination")))
    # The explicit template needs its source role bound, not the absent destination.
    do_provision(ctx.cursor, ctx=ctx)
    before = graph.value_hash()
    assert _texts(ctx)[edge.uid] == "Watch the performance"
    assert graph.value_hash() == before
    assert edge.successor is None


def test_realized_destination_missing_required_binding_is_diagnostic() -> None:
    graph = _world().create_story("run").graph
    ctx = _ctx(graph)
    edge = _events(ctx)["Watch the performance"]
    role = ctx.derive(cursor_id=edge.successor_id).get_ns(edge.successor)["host_role"]
    role.set_provider(None)
    before = graph.value_hash()
    with pytest.raises((TypeError, ValueError), match="bound concept|Missing anonymous"):
        _texts(ctx)
    assert graph.value_hash() == before


@pytest.mark.parametrize("eager", [False, True])
def test_both_menu_projection_paths_defer_selection_and_realization(eager: bool) -> None:
    graph = _world(menu=True).create_story("menu", freeze_shape=eager).graph
    menu = graph.get(graph.initial_cursor_id)
    target = graph.find_one(Selector(has_kind=Block, label="performance"))
    ctx = PhaseCtx(graph=graph, cursor_id=menu.uid)
    if not eager:
        do_provision(menu, ctx=ctx)
    (edge,) = menu.edges_out(Selector(has_kind=Action))
    assert edge.text == "" and edge.fallback_text == "performance"
    assert _texts(ctx)[edge.uid] == "the blonde girl is performing (0)"
    target.locals["action_text"] = ""
    assert _texts(ctx)[edge.uid] == "Lower priority"
    target.action_name = ""
    target.locals["menu_text"] = "Last suggestion"
    assert _texts(ctx)[edge.uid] == "Last suggestion"
    target.locals["menu_text"] = ""
    assert _texts(ctx)[edge.uid] == "performance"


def test_compiled_world_actual_return_keeps_offer_identity_and_authored_source() -> None:
    bundle = WorldBundle.load(Path(__file__).resolve().parents[3] / "worlds/destination_choice_demo")
    world = WorldCompiler().compile(bundle)
    graph = world.create_story("witness").graph
    ledger = Ledger.from_graph(graph)
    ctx = _ctx(graph, narrator="_")
    event = _events(ctx)["Watch the show"]
    source = event.successor.locals["action_text"]
    before = graph.value_hash()
    assert _texts(ctx)[event.uid] == "the blonde girl is performing in the square"
    assert graph.value_hash() == before
    hub_id = ledger.cursor_id
    ledger.resolve_choice(event.uid)
    assert ledger.cursor_id == hub_id
    assert graph.get(event.uid) is event
    assert _texts(_ctx(graph, narrator="_"))[event.uid] == "Rin is performing in the square"
    assert event.text == "" and event.successor.locals["action_text"] == source
    assert graph.find_one(Selector(has_kind=SandboxScope)).locals["world_turn"] == 0
