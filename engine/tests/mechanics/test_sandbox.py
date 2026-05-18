"""Sandbox mechanic contracts for dynamic scene-location hubs."""

from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Graph, Selector, Token
from tangl.core.runtime_op import Effect, Predicate
from tangl.mechanics.games import (
    HasGame,
    IncrementalGame,
    IncrementalGameHandler,
    IncrementalMove,
    TaskSpec,
)
from tangl.mechanics.sandbox import (
    ChargeConsumption,
    ChargeFacet,
    ContainerFacet,
    LightSourceFacet,
    LockableFacet,
    OpenableFacet,
    SandboxClockPolicy,
    SandboxExit,
    SandboxFixture,
    SandboxInteraction,
    SandboxLocation,
    SandboxMob,
    SandboxMobAffordance,
    SandboxScope,
    SandboxVisibilityRule,
    Schedule,
    ScheduleEntry,
    ScheduledEvent,
    ScheduledPresence,
    SwitchableFacet,
    WorldTime,
    advance_world_turn,
    current_world_time,
    normalize_sandbox_direction,
)
from tangl.mechanics.sandbox import incremental as sandbox_incremental
from tangl.story import Action, Block, StoryGraph
from tangl.story.concepts import Actor, Role
from tangl.story.concepts.asset import AssetTransactionManager, AssetType
from tangl.story.fragments import ChoiceFragment, ContentFragment
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Ledger, Requirement
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


class SandboxItemType(AssetType):
    name: str = ""
    traits: set[str] = Field(default_factory=set)
    portable: bool = True
    readable: bool = False
    read_text: str | None = None
    switchable: SwitchableFacet | None = None
    light_source: LightSourceFacet | None = None
    container: ContainerFacet | None = Field(
        default=None,
        json_schema_extra={"instance_var": True},
    )
    lit: bool = Field(default=False, json_schema_extra={"instance_var": True})
    charge: ChargeFacet | None = Field(
        default=None,
        json_schema_extra={"instance_var": True},
    )
    turn_on_text: str | None = None
    turn_off_text: str | None = None
    take_text: str | None = None
    drop_text: str | None = None
    interactions: list[SandboxInteraction] = Field(default_factory=list)
    scheduled_events: list[ScheduledEvent] = Field(default_factory=list)


class SandboxColonyGame(IncrementalGame):
    """Tiny resource-allocation shell for sandbox tick integration tests."""

    starting_resources: dict[str, int] = {"food": 1}
    starting_workers: int = 1
    task_specs: dict[str, TaskSpec] = {
        "forage": TaskSpec(produces={"food": 2}),
    }
    upkeep: dict[str, int] = {"food": 1}
    unlocked_tasks: list[str] = ["forage"]


class SandboxColonyBlock(HasGame, Block):
    """Sandbox-hosted incremental game block."""

    _game_class = SandboxColonyGame
    _game_handler_class = IncrementalGameHandler


@pytest.fixture(autouse=True)
def _clear_sandbox_item_types() -> None:
    SandboxItemType.clear_instances()
    yield
    SandboxItemType.clear_instances()


def _sandbox_graph() -> tuple[Graph, SandboxLocation, SandboxLocation, SandboxLocation]:
    graph = Graph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="Road",
        sandbox_scope="tiny_cave",
        links={"east": "building", "west": "cave_entrance"},
    )
    building = SandboxLocation(
        label="building",
        location_name="Building",
        sandbox_scope="tiny_cave",
        links={"west": "road"},
    )
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        sandbox_scope="tiny_cave",
        links={"east": "road"},
    )
    graph.add(road)
    graph.add(building)
    graph.add(cave_entrance)
    return graph, road, building, cave_entrance


def _dynamic_sandbox_actions(location: SandboxLocation) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox", "movement"}.issubset(edge.tags)
    ]


def _dynamic_sandbox_actions_with_tag(location: SandboxLocation, tag: str) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox", tag}.issubset(edge.tags)
    ]


def test_world_time_is_derived_from_world_turn() -> None:
    assert WorldTime.from_turn(0).model_dump() == {
        "turn": 0,
        "period": 1,
        "day": 1,
        "day_of_month": 1,
        "month": 1,
        "season": 1,
        "year": 1,
    }

    later = WorldTime.from_turn(4 * 28 * 3)

    assert later.period == 1
    assert later.day_of_month == 1
    assert later.month == 4
    assert later.season == 2
    assert later.year == 1


def test_world_turn_helpers_use_mutable_locals() -> None:
    location = SandboxLocation(label="road", locals={"world_turn": 1})

    assert current_world_time(location).turn == 1
    assert advance_world_turn(location, 2) == 3
    assert location.locals["world_turn"] == 3


def test_charge_consumption_supports_when_used_trigger() -> None:
    charge = ChargeFacet(
        current=2,
        maximum=2,
        consumption_trigger=ChargeConsumption.WHEN_USED,
    )

    assert charge.can_consume(is_on=True) is False
    assert charge.can_consume(is_on=False, was_used=True) is True


def test_charge_consumption_rate_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ChargeFacet(current=2, maximum=2, consume_per_tick=0)


def test_clock_policy_default_duration_has_constant_fallback() -> None:
    policy = SandboxClockPolicy(default_durations={"movement": 2})

    assert policy.default_duration("custom_action") == 1


def test_depleted_charged_asset_does_not_project_turn_on_choice() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    cave = SandboxLocation(label="cave", location_name="Cave")
    SandboxItemType(
        label="lamp",
        name="lamp",
        switchable=SwitchableFacet(),
        light_source=LightSourceFacet(),
        charge=ChargeFacet(current=0, maximum=3),
    )
    lamp = Token[SandboxItemType](token_from="lamp", label="lamp")
    scope.player_assets.add_asset(lamp)
    graph.add(scope)
    graph.add(cave)
    graph.add(lamp)
    scope.add_child(cave)

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))

    asset_actions = _dynamic_sandbox_actions_with_tag(cave, "asset")
    assert "Turn on lamp" not in {action.text for action in asset_actions}


def test_schedule_matches_time_location_and_presence() -> None:
    schedule = Schedule(
        entries=[
            ScheduleEntry(label="traveler", location="road", actor="traveler", period=3),
            ScheduleEntry(label="merchant", location="building", period=3),
        ]
    )
    world_time = WorldTime.from_turn(2)

    matches = schedule.matching(
        world_time,
        location="road",
        actors_present=["traveler"],
    )

    assert [entry.label for entry in matches] == ["traveler"]


def test_scheduled_mob_presence_follows_world_time() -> None:
    graph = Graph(label="tiny_cave")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="road",
        present_text="A pirate watches you.",
        schedule=Schedule(
            entries=[
                ScheduleEntry(label="road_watch", location="road", period=1),
                ScheduleEntry(label="building_watch", location="building", period=2),
            ]
        ),
        affordances=[
            SandboxMobAffordance(
                label="greet",
                text="Greet the pirate",
                journal_text="The pirate nods.",
            )
        ],
    )
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 0},
        mobs=[pirate],
    )
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))

    assert [
        action.text for action in _dynamic_sandbox_actions_with_tag(road, "mob")
    ] == ["Greet the pirate"]
    assert _dynamic_sandbox_actions_with_tag(building, "mob") == []

    scope.locals["world_turn"] = 1
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))

    assert _dynamic_sandbox_actions_with_tag(road, "mob") == []
    assert [
        action.text for action in _dynamic_sandbox_actions_with_tag(building, "mob")
    ] == ["Greet the pirate"]


def test_scheduled_mob_presence_can_gate_scheduled_events() -> None:
    graph = Graph(label="tiny_cave")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="road",
        schedule=Schedule(
            entries=[
                ScheduleEntry(label="road_watch", location="road", period=1),
                ScheduleEntry(label="building_watch", location="building", period=2),
            ]
        ),
    )
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 0},
        mobs=[pirate],
        scheduled_events=[
            ScheduledEvent(
                label="pirate_chat",
                actor="pirate",
                location="road",
                period=1,
                target="pirate_arrives",
                text="Talk to pirate",
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road")
    pirate_arrives = Block(label="pirate_arrives", content="The pirate waves.")
    graph.add(scope)
    graph.add(road)
    graph.add(pirate)
    graph.add(pirate_arrives)
    scope.add_child(road)
    scope.add_child(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert [
        event.text for event in _dynamic_sandbox_actions_with_tag(road, "event")
    ] == ["Talk to pirate"]

    pirate.schedule = Schedule(
        entries=[
            ScheduleEntry(label="building_watch", location="building", period=1),
        ]
    )
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert _dynamic_sandbox_actions_with_tag(road, "event") == []


def test_present_mob_projects_traversable_interaction_with_return() -> None:
    graph = StoryGraph(label="tiny_cave")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="road",
        interactions=[
            SandboxInteraction(
                label="talk",
                text="Talk to the pirate",
                target="pirate_chat",
                return_to_location=True,
            )
        ],
    )
    scope = SandboxScope(label="tiny_cave_scope", mobs=[pirate])
    road = SandboxLocation(label="road", location_name="Road")
    pirate_chat = Block(
        label="pirate_chat",
        content="The pirate tells you about the cave.",
    )
    graph.add(scope)
    graph.add(road)
    graph.add(pirate_chat)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    interactions = _dynamic_sandbox_actions_with_tag(road, "interaction")

    assert [action.text for action in interactions] == ["Talk to the pirate"]
    assert interactions[0].successor is pirate_chat
    assert interactions[0].return_phase is not None
    assert interactions[0].ui_hints["source"] == "sandbox_mob"
    assert interactions[0].ui_hints["source_label"] == "pirate"


def test_scheduled_absent_mob_does_not_project_interaction() -> None:
    graph = StoryGraph(label="tiny_cave")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="building",
        schedule=Schedule(entries=[ScheduleEntry(label="away", location="building", period=1)]),
        interactions=[
            SandboxInteraction(
                label="talk",
                text="Talk to the pirate",
                target="pirate_chat",
            )
        ],
    )
    scope = SandboxScope(label="tiny_cave_scope", locals={"world_turn": 0}, mobs=[pirate])
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    pirate_chat = Block(
        label="pirate_chat",
        content="The pirate tells you about the cave.",
    )
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(pirate_chat)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert _dynamic_sandbox_actions_with_tag(road, "interaction") == []


def test_once_mob_interaction_is_suppressed_after_target_visit() -> None:
    graph = StoryGraph(label="tiny_cave")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="road",
        interactions=[
            SandboxInteraction(
                label="talk",
                text="Talk to the pirate",
                target="pirate_chat",
                once=True,
            )
        ],
    )
    scope = SandboxScope(label="tiny_cave_scope", mobs=[pirate])
    road = SandboxLocation(label="road", location_name="Road")
    pirate_chat = Block(
        label="pirate_chat",
        content="The pirate tells you about the cave.",
        locals={"_visited": True},
    )
    graph.add(scope)
    graph.add(road)
    graph.add(pirate_chat)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert _dynamic_sandbox_actions_with_tag(road, "interaction") == []


def test_location_interaction_can_be_trivial_self_loop_action() -> None:
    graph = StoryGraph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="Road",
        content="Cover is {cover}.",
        locals={"cover": "thin"},
        interactions=[
            SandboxInteraction(
                label="hide",
                text="Hide in the roadside ruins",
                target="current",
                journal_text="You crouch behind the broken wall.",
                effects=[Effect(expr="cover = 'good'")],
            )
        ],
    )
    graph.add(road)
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    hide = _dynamic_sandbox_actions_with_tag(road, "interaction")[0]
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    ledger.resolve_choice(hide.uid)

    assert road.locals["cover"] == "good"
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content[:2] == [
        "You crouch behind the broken wall.",
        "Cover is good.",
    ]


def test_assets_project_sponsored_interactions_when_present_or_carried() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    road = SandboxLocation(label="road", location_name="Road")
    flute_scene = Block(label="flute_scene", content="The notes carry.")
    book_scene = Block(label="book_scene", content="The margins answer.")
    SandboxItemType(
        label="flute",
        name="flute",
        interactions=[
            SandboxInteraction(
                label="play",
                text="Play the flute",
                target="flute_scene",
                return_to_location=True,
            )
        ],
    )
    SandboxItemType(
        label="book",
        name="book",
        interactions=[
            SandboxInteraction(
                label="study",
                text="Study the book",
                target="book_scene",
            )
        ],
    )
    flute = Token[SandboxItemType](token_from="flute", label="flute")
    book = Token[SandboxItemType](token_from="book", label="book")
    scope.player_assets.add_asset(flute)
    road.add_asset(book)
    graph.add(scope)
    graph.add(road)
    graph.add(flute_scene)
    graph.add(book_scene)
    graph.add(flute)
    graph.add(book)
    scope.add_child(road)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    interactions = [
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "interaction")
        if action.ui_hints.get("source") == "sandbox_asset"
    ]
    assert {action.text for action in interactions} == {
        "Play the flute",
        "Study the book",
    }
    assert {
        action.ui_hints["asset"]: action.ui_hints["possession"]
        for action in interactions
    } == {"flute": "carried", "book": "location"}
    play = next(action for action in interactions if action.text == "Play the flute")
    assert play.successor is flute_scene
    assert play.return_phase is not None


def test_fixture_projects_sponsored_interaction() -> None:
    graph = StoryGraph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="Road",
        locals={"blessed": False},
        fixtures=[
            SandboxFixture(
                label="altar",
                name="altar",
                interactions=[
                    SandboxInteraction(
                        label="pray",
                        text="Pray at the altar",
                        target="current",
                        journal_text="The stone warms under your hands.",
                        effects=[Effect(expr="blessed = True")],
                    )
                ],
            )
        ],
    )
    graph.add(road)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    interaction = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "interaction")
        if action.ui_hints.get("source") == "sandbox_fixture"
    )
    assert interaction.text == "Pray at the altar"
    assert interaction.successor is road
    assert interaction.ui_hints["fixture"] == "altar"
    assert interaction.journal_text == "The stone warms under your hands."

    Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(interaction.uid)

    assert road.locals["blessed"] is True


def test_present_mob_projects_asset_transfer_actions() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    road = SandboxLocation(label="road", location_name="Road")
    pirate = SandboxMob(label="pirate", name="pirate", location="road")
    SandboxItemType(label="keys", name="keys")
    SandboxItemType(label="coin", name="coin")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    coin = Token[SandboxItemType](token_from="coin", label="coin")
    scope.player_assets.add_asset(keys)
    pirate.add_asset(coin)
    graph.add(scope)
    graph.add(road)
    graph.add(pirate)
    graph.add(keys)
    graph.add(coin)
    scope.add_child(road)
    scope.add_child(pirate)
    scope.mobs.append(pirate)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    transfer_texts = {
        choice.text
        for choice in choices
        if choice.ui_hints.get("source") == "sandbox_mob"
        and choice.ui_hints.get("asset") in {"keys", "coin"}
    }

    assert transfer_texts == {"Give keys to pirate", "Take coin from pirate"}
    mob_transfer_actions = [
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "mob")
        if action.ui_hints.get("asset") in {"keys", "coin"}
    ]
    assert all("asset" not in action.tags for action in mob_transfer_actions)

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    take_coin = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "take")
        if action.ui_hints.get("mob") == "pirate"
    )
    ledger.resolve_choice(take_coin.uid)

    assert scope.player_assets.has_asset("coin")
    assert not pirate.has_asset("coin")

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    give_keys = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "give")
        if action.ui_hints.get("asset") == "keys"
    )
    ledger.resolve_choice(give_keys.uid)

    assert pirate.has_asset("keys")
    assert not scope.player_assets.has_asset("keys")


def test_absent_mob_does_not_project_asset_transfer_actions() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    pirate = SandboxMob(label="pirate", name="pirate", location="building")
    SandboxItemType(label="coin", name="coin")
    coin = Token[SandboxItemType](token_from="coin", label="coin")
    pirate.add_asset(coin)
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(pirate)
    graph.add(coin)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)
    scope.mobs.append(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert [
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "mob")
        if action.ui_hints.get("asset") == "coin"
    ] == []


def test_stale_mob_transfer_actions_are_unavailable_after_mob_moves() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope", locals={"world_turn": 0})
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="road",
        schedule=Schedule(
            entries=[
                ScheduleEntry(label="road_watch", location="road", period=1),
                ScheduleEntry(label="building_watch", location="building", period=2),
            ]
        ),
    )
    SandboxItemType(label="coin", name="coin")
    coin = Token[SandboxItemType](token_from="coin", label="coin")
    pirate.add_asset(coin)
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(pirate)
    graph.add(coin)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)
    scope.mobs.append(pirate)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    take_coin = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "take")
        if action.ui_hints.get("mob") == "pirate"
    )

    assert take_coin.available(ctx=ctx)

    scope.locals["world_turn"] = 1

    assert not take_coin.available(ctx=ctx)


def test_sandbox_location_links_project_normal_actions() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Go east to Building",
        "Go west to Cave Entrance",
    }
    assert all(action.successor is not None for action in actions)
    assert all(action.ui_hints["source"] == "sandbox_link" for action in actions)
    assert all(action.ui_hints["contribution"] == "movement" for action in actions)
    assert all(action.ui_hints["source_kind"] == "location" for action in actions)
    assert all(action.ui_hints["source_label"] == "road" for action in actions)
    assert all(action.ui_hints["scope"] == "tiny_cave" for action in actions)


def test_sandbox_location_links_normalize_direction_aliases() -> None:
    assert normalize_sandbox_direction("n") == "north"
    assert normalize_sandbox_direction("U") == "up"
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.links = {"n": "building", "u": "cave_entrance"}
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Go north to Building",
        "Go up to Cave Entrance",
    }
    hints = {action.ui_hints["raw_direction"]: action.ui_hints["direction"] for action in actions}
    assert hints == {"n": "north", "u": "up"}


def test_sandbox_structured_exit_can_override_choice_text() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.links = {
        "in": SandboxExit(target="building", text="Enter the building"),
        "out": {"target": "cave_entrance", "text": "Leave for the cave"},
        "down": {"to": "cave_entrance", "text": "Climb down"},
    }
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Enter the building",
        "Leave for the cave",
        "Climb down",
    }


def test_manual_location_action_suppresses_generated_link_choice() -> None:
    graph, road, building, _cave_entrance = _sandbox_graph()
    Action(
        registry=graph,
        label="manual_enter_building",
        predecessor_id=road.uid,
        successor_id=building.uid,
        text="Step inside",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {"Go west to Cave Entrance"}


def test_dynamic_nonmovement_action_does_not_suppress_generated_link_choice() -> None:
    graph, road, building, _cave_entrance = _sandbox_graph()
    Action(
        registry=graph,
        label="sandbox_event_enter_building",
        predecessor_id=road.uid,
        successor_id=building.uid,
        text="Attend scheduled building event",
        tags={"dynamic", "sandbox", "event"},
    )
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Go east to Building",
        "Go west to Cave Entrance",
    }


def test_sandbox_movement_refresh_removes_stale_actions() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)
    first_ids = {action.uid for action in _dynamic_sandbox_actions(road)}

    road.links = {"east": "building"}
    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {"Go east to Building"}
    assert first_ids.isdisjoint({action.uid for action in actions})


def test_target_location_availability_gates_generated_movement_choice() -> None:
    graph, road, _building, cave_entrance = _sandbox_graph()
    cave_entrance.availability = [Predicate(expr="grate_open and lamp_lit")]
    cave_entrance.locals.update({"grate_open": True, "lamp_lit": False})
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)

    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    west = next(choice for choice in choices if choice.text == "Go west to Cave Entrance")

    assert west.available is False
    assert west.unavailable_reason == "guard_failed_or_unavailable"

    cave_entrance.locals["lamp_lit"] = True
    ctx._ns_cache.clear()
    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    west = next(choice for choice in choices if choice.text == "Go west to Cave Entrance")

    assert west.available is True


def test_sandbox_location_projects_wait_choice() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.locals["world_turn"] = 0
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    waits = _dynamic_sandbox_actions_with_tag(road, "wait")
    assert len(waits) == 1
    assert waits[0].text == "Wait"
    assert waits[0].successor is road
    assert waits[0].payload["sandbox_action"] == "wait"
    assert waits[0].payload["turn_delta"] == 1
    assert waits[0].payload["sandbox_time_cost"].duration == 1
    assert waits[0].payload["sandbox_time_cost"].kind == "wait"


def test_wait_choice_advances_world_turn_through_ledger() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.locals["world_turn"] = 0
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)
    wait = _dynamic_sandbox_actions_with_tag(road, "wait")[0]
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    ledger.resolve_choice(wait.uid, choice_payload=wait.payload)

    assert ledger.cursor is road
    assert road.locals["world_turn"] == 1


def test_sandbox_can_host_incremental_allocation_and_tick_cycles() -> None:
    graph = Graph(label="colony_sandbox")
    scope = SandboxScope(label="colony_scope", locals={"world_turn": 0})
    hub = SandboxLocation(label="colony_hub", location_name="Colony")
    colony = SandboxColonyBlock(label="colony_shell", content="The colony waits.")
    graph.add(scope)
    graph.add(hub)
    graph.add(colony)
    scope.add_child(hub)
    scope.add_child(colony)
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    assert sandbox_incremental.reconcile_incremental_games_on_sandbox_tick is not None
    do_provision(hub, ctx=ctx)
    actions = _dynamic_sandbox_actions_with_tag(hub, "incremental")

    assert {action.text for action in actions} == {
        "Assign 1 worker to forage",
        "End cycle",
    }

    assign = next(action for action in actions if action.text == "Assign 1 worker to forage")
    assert assign.payload["sandbox_time_cost"].duration == 0

    ledger = Ledger.from_graph(graph, entry_id=hub.uid)
    ledger.resolve_choice(assign.uid, choice_payload=assign.payload)

    assert scope.locals["world_turn"] == 0
    assert colony.game.worker_pool == 0
    assert colony.game.task_assignments["forage"] == 1
    assert any(
        isinstance(fragment, ContentFragment)
        and fragment.content == "You assign a worker to forage."
        for fragment in ledger.get_journal()
    )
    assert "_sandbox_incremental_fragments" not in hub.locals

    do_provision(hub, ctx=PhaseCtx(graph=graph, cursor_id=hub.uid))
    cycle = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(hub, "incremental")
        if action.text == "End cycle"
    )
    assert cycle.payload["sandbox_time_cost"].duration == 1

    ledger.resolve_choice(cycle.uid, choice_payload=cycle.payload)

    assert scope.locals["world_turn"] == 1
    assert colony.game.cycle == 1
    assert colony.game.resources["food"] == 2
    journal_text = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert "Cycle 1 resolves." in journal_text
    assert "Resources: food=2." in journal_text
    assert "_sandbox_tick_result" not in hub.locals


def test_sandbox_incremental_update_rejects_unsupported_move_kind() -> None:
    graph = Graph(label="colony_sandbox")
    scope = SandboxScope(label="colony_scope", locals={"world_turn": 0})
    hub = SandboxLocation(label="colony_hub", location_name="Colony")
    colony = SandboxColonyBlock(label="colony_shell", content="The colony waits.")
    graph.add(scope)
    graph.add(hub)
    graph.add(colony)
    scope.add_child(hub)
    scope.add_child(colony)
    ctx = PhaseCtx(
        graph=graph,
        cursor_id=hub.uid,
        incoming_payload={
            "sandbox_incremental_game": colony.uid,
            "move": IncrementalMove(kind="resolve_cycle"),
        },
    )

    with pytest.raises(ValueError, match="Unsupported sandbox incremental move kind"):
        sandbox_incremental.process_sandbox_incremental_game_move(caller=hub, ctx=ctx)


def test_scheduled_event_projects_only_at_matching_location_and_time() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(traveler)
    road.locals["world_turn"] = 1
    road.scheduled_events = [
        ScheduledEvent(
            label="traveler",
            location="road",
            period=3,
            target="traveler_arrives",
            text="Talk to traveler",
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []

    road.locals["world_turn"] = 2
    ctx._ns_cache.clear()
    do_provision(road, ctx=ctx)
    events = _dynamic_sandbox_actions_with_tag(road, "event")

    assert len(events) == 1
    assert events[0].text == "Talk to traveler"
    assert events[0].successor is traveler


def test_scheduled_event_renders_as_normal_choice_fragment() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(traveler)
    road.locals["world_turn"] = 2
    road.scheduled_events = [
        ScheduledEvent(
            label="traveler",
            location="road",
            period=3,
            target="traveler_arrives",
            text="Talk to traveler",
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)

    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]

    assert any(choice.text == "Talk to traveler" and choice.available for choice in choices)


def test_scheduled_event_uses_interaction_journal_effects_and_availability() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.locals.update({"world_turn": 2, "can_ring": False, "bell_rung": False})
    road.scheduled_events = [
        ScheduledEvent(
            label="bell",
            location="road",
            period=3,
            target="current",
            text="Ring the bell",
            journal_text="The bell rings once.",
            availability=[Predicate(expr="can_ring")],
            effects=[Effect(expr="bell_rung = True")],
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    assert event.text == "Ring the bell"
    assert event.ui_hints["contribution"] == "event"
    assert event.journal_text == "The bell rings once."
    assert not event.available(ctx=ctx)

    road.locals["can_ring"] = True
    ctx._ns_cache.clear()
    assert event.available(ctx=ctx)

    Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)

    assert road.locals["bell_rung"] is True


def test_present_mob_scheduled_event_projects_when_time_matches() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope", locals={"world_turn": 0})
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    parley = Block(label="parley", content="The pirate lowers his blade.")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="road",
        schedule=Schedule(
            entries=[
                ScheduleEntry(label="road_watch", location="road", period=1),
                ScheduleEntry(label="building_watch", location="building", period=2),
            ]
        ),
        scheduled_events=[
            ScheduledEvent(
                label="parley",
                period=1,
                target="parley",
                text="Parley with the pirate",
            )
        ],
    )
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(parley)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)
    scope.mobs.append(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))

    road_events = _dynamic_sandbox_actions_with_tag(road, "event")
    assert [event.text for event in road_events] == ["Parley with the pirate"]
    assert road_events[0].ui_hints["source_kind"] == "mob"
    assert road_events[0].ui_hints["mob"] == "pirate"
    assert _dynamic_sandbox_actions_with_tag(building, "event") == []


def test_hidden_mob_does_not_project_scheduled_events() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 0},
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(label="dark_cave", location_name="Dark Cave")
    parley = Block(label="parley", content="The pirate lowers his blade.")
    pirate = SandboxMob(
        label="pirate",
        name="pirate",
        location="dark_cave",
        scheduled_events=[
            ScheduledEvent(
                label="parley",
                period=1,
                target="parley",
                text="Parley with the pirate",
            )
        ],
    )
    graph.add(scope)
    graph.add(cave)
    graph.add(parley)
    graph.add(pirate)
    scope.add_child(cave)
    scope.add_child(pirate)
    scope.mobs.append(pirate)

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))

    assert _dynamic_sandbox_actions_with_tag(cave, "event") == []


def test_suppressed_carried_asset_affordances_do_not_project_scheduled_events() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 0},
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(label="dark_cave", location_name="Dark Cave")
    whisper = Block(label="whisper", content="The amulet hums.")
    SandboxItemType(
        label="amulet",
        name="amulet",
        scheduled_events=[
            ScheduledEvent(
                label="whisper",
                period=1,
                target="whisper",
                text="Listen to the amulet",
            )
        ],
    )
    amulet = Token[SandboxItemType](token_from="amulet", label="amulet")
    scope.player_assets.add_asset(amulet)
    graph.add(scope)
    graph.add(cave)
    graph.add(whisper)
    graph.add(amulet)
    scope.add_child(cave)

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))

    assert _dynamic_sandbox_actions_with_tag(cave, "event") == []


def test_locked_local_object_projects_unavailable_unlock_without_key() -> None:
    graph, _road, _building, cave_entrance = _sandbox_graph()
    cave_entrance.fixtures = [
        SandboxFixture(
            label="grate",
            name="grate",
            lockable=LockableFacet(
                key="keys",
                unlock_text="The key turns with a click. The grate unlocks.",
            ),
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)

    do_provision(cave_entrance, ctx=ctx)

    unlocks = _dynamic_sandbox_actions_with_tag(cave_entrance, "unlock")
    assert [action.text for action in unlocks] == ["Unlock grate"]
    assert unlocks[0].successor is cave_entrance
    assert unlocks[0].journal_text == "The key turns with a click. The grate unlocks."

    fragments = render_block_choices(caller=cave_entrance, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    unlock = next(choice for choice in choices if choice.text == "Unlock grate")
    assert unlock.available is False
    assert unlock.unavailable_reason == "guard_failed_or_unavailable"


def test_locked_local_object_unlocks_with_carried_key_and_stops_projecting() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        content="The grate is {grate_state}.",
        locals={"grate_state": "locked"},
        fixtures=[
            SandboxFixture(
                label="grate",
                name="grate",
                lockable=LockableFacet(
                    key="keys",
                    unlock_text="The key turns with a click. The grate unlocks.",
                ),
            )
        ],
    )
    SandboxItemType(label="keys", name="keys")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    scope.player_assets.add_asset(keys)
    graph.add(scope)
    graph.add(cave_entrance)
    graph.add(keys)
    scope.add_child(cave_entrance)
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)
    do_provision(cave_entrance, ctx=ctx)
    unlock = _dynamic_sandbox_actions_with_tag(cave_entrance, "unlock")[0]
    unlock.effects.append(Effect(expr="grate_state = 'unlocked'"))
    ledger = Ledger.from_graph(graph, entry_id=cave_entrance.uid)

    ledger.resolve_choice(unlock.uid)

    assert cave_entrance.fixtures[0].locked is False
    assert cave_entrance.locals["grate_state"] == "unlocked"
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content[:2] == [
        "The key turns with a click. The grate unlocks.",
        "The grate is unlocked.",
    ]

    do_provision(cave_entrance, ctx=PhaseCtx(graph=graph, cursor_id=cave_entrance.uid))
    assert _dynamic_sandbox_actions_with_tag(cave_entrance, "unlock") == []
    lock = _dynamic_sandbox_actions_with_tag(cave_entrance, "lock")[0]

    ledger.resolve_choice(lock.uid)

    assert cave_entrance.fixtures[0].locked is True


def test_open_fixture_cannot_lock_until_closed() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        fixtures=[
            SandboxFixture(
                label="grate",
                name="grate",
                openable=OpenableFacet(is_open=True),
                lockable=LockableFacet(key="keys", is_locked=False),
            )
        ],
    )
    SandboxItemType(label="keys", name="keys")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    scope.player_assets.add_asset(keys)
    graph.add(scope)
    graph.add(cave_entrance)
    graph.add(keys)
    scope.add_child(cave_entrance)
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)

    do_provision(cave_entrance, ctx=ctx)

    lock = _dynamic_sandbox_actions_with_tag(cave_entrance, "lock")[0]
    fragments = render_block_choices(caller=cave_entrance, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    lock_choice = next(choice for choice in choices if choice.text == "Lock grate")

    assert lock_choice.available is False
    assert cave_entrance.fixtures[0].can_lock(has_key=lambda key: key == "keys") is False
    with pytest.raises(ValueError, match="Fixture 'grate' cannot lock while open"):
        cave_entrance.lock_fixture("grate")

    ledger = Ledger.from_graph(graph, entry_id=cave_entrance.uid)
    close = _dynamic_sandbox_actions_with_tag(cave_entrance, "close")[0]
    ledger.resolve_choice(close.uid)

    do_provision(cave_entrance, ctx=PhaseCtx(graph=graph, cursor_id=cave_entrance.uid))
    closed_lock = _dynamic_sandbox_actions_with_tag(cave_entrance, "lock")[0]
    ledger.resolve_choice(closed_lock.uid)

    assert cave_entrance.fixtures[0].locked is True


def test_locked_local_object_unlocks_with_key_asset_in_player_inventory() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        fixtures=[
            SandboxFixture(
                label="grate",
                name="grate",
                lockable=LockableFacet(
                    key="keys",
                    unlock_text="The key turns with a click. The grate unlocks.",
                ),
            )
        ],
    )
    SandboxItemType(label="keys", name="keys")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    scope.player_assets.add_asset(keys)
    graph.add(scope)
    graph.add(cave_entrance)
    graph.add(keys)
    scope.add_child(cave_entrance)
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)

    do_provision(cave_entrance, ctx=ctx)
    fragments = render_block_choices(caller=cave_entrance, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    unlock = next(choice for choice in choices if choice.text == "Unlock grate")

    assert unlock.available is True


def test_openable_fixture_projects_without_lockable_facet() -> None:
    graph = StoryGraph(label="tiny_cave")
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        fixtures=[
            SandboxFixture(
                label="hatch",
                name="hatch",
                openable=OpenableFacet(open_text="The hatch swings open."),
            )
        ],
    )
    graph.add(cave_entrance)
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)

    do_provision(cave_entrance, ctx=ctx)

    opens = _dynamic_sandbox_actions_with_tag(cave_entrance, "fixture")
    assert [action.text for action in opens] == ["Open hatch"]
    assert opens[0].journal_text == "The hatch swings open."


def test_location_assets_project_take_read_and_drop_actions() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    building = SandboxLocation(label="building", location_name="Building")
    SandboxItemType(label="keys", name="keys")
    SandboxItemType(
        label="leaflet",
        name="leaflet",
        readable=True,
        read_text="Welcome to Adventure!",
    )
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    leaflet = Token[SandboxItemType](token_from="leaflet", label="leaflet")
    building.add_asset(keys)
    building.add_asset(leaflet)
    graph.add(scope)
    graph.add(building)
    graph.add(keys)
    graph.add(leaflet)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=building.uid)

    do_provision(building, ctx=ctx)
    assets = _dynamic_sandbox_actions_with_tag(building, "asset")

    assert {action.text for action in assets} == {
        "Read leaflet",
        "Take keys",
        "Take leaflet",
    }
    read = next(action for action in assets if action.text == "Read leaflet")
    assert read.journal_text == "Welcome to Adventure!"

    take_keys = next(action for action in assets if action.text == "Take keys")
    ledger = Ledger.from_graph(graph, entry_id=building.uid)
    ledger.resolve_choice(take_keys.uid)

    assert not building.has_asset("keys")
    assert scope.player_assets.has_asset("keys")

    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))
    drop_keys = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(building, "asset")
        if action.text == "Drop keys"
    )
    ledger.resolve_choice(drop_keys.uid)

    assert building.has_asset("keys")
    assert not scope.player_assets.has_asset("keys")


def test_carried_readable_asset_projects_read_action() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    building = SandboxLocation(label="building", location_name="Building")
    SandboxItemType(
        label="leaflet",
        name="leaflet",
        readable=True,
        read_text="Welcome to Adventure!",
    )
    leaflet = Token[SandboxItemType](token_from="leaflet", label="leaflet")
    scope.player_assets.add_asset(leaflet)
    graph.add(scope)
    graph.add(building)
    graph.add(leaflet)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=building.uid)

    do_provision(building, ctx=ctx)

    actions = _dynamic_sandbox_actions_with_tag(building, "asset")
    read = next(action for action in actions if action.text == "Read leaflet")
    assert read.journal_text == "Welcome to Adventure!"


def test_fixture_container_accepts_matching_assets_through_preflight() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    building = SandboxLocation(
        label="building",
        location_name="Building",
        fixtures=[
            SandboxFixture(
                label="basket",
                name="basket",
                container=ContainerFacet(max_items=1, accepts_traits={"tiny"}),
            )
        ],
    )
    SandboxItemType(label="keys", name="keys", traits={"tiny"})
    SandboxItemType(label="lamp", name="lamp")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    lamp = Token[SandboxItemType](token_from="lamp", label="lamp")
    scope.player_assets.add_asset(keys)
    scope.player_assets.add_asset(lamp)
    graph.add(scope)
    graph.add(building)
    graph.add(keys)
    graph.add(lamp)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=building.uid)

    do_provision(building, ctx=ctx)
    fragments = render_block_choices(caller=building, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    put_keys = next(choice for choice in choices if choice.text == "Put keys in basket")
    put_lamp = next(choice for choice in choices if choice.text == "Put lamp in basket")

    assert put_keys.available is True
    assert put_lamp.available is False

    ledger = Ledger(graph=graph, cursor_id=building.uid)
    action = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(building, "put")
        if action.text == "Put keys in basket"
    )
    ledger.resolve_choice(action.uid)

    basket = building.fixture_by_label("basket")
    assert basket.has_asset("keys")
    assert not scope.player_assets.has_asset("keys")
    assert scope.player_assets.has_asset("lamp")


def test_closed_fixture_container_hides_contents_and_rejects_receive() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    chest = SandboxFixture(
        label="chest",
        name="chest",
        openable=OpenableFacet(is_open=False),
        container=ContainerFacet(is_open=False, accepts_traits={"tiny"}),
    )
    building = SandboxLocation(
        label="building",
        location_name="Building",
        fixtures=[chest],
    )
    SandboxItemType(label="keys", name="keys", traits={"tiny"})
    SandboxItemType(label="coin", name="coin", traits={"tiny"})
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    coin = Token[SandboxItemType](token_from="coin", label="coin")
    scope.player_assets.add_asset(keys)
    chest.add_asset(coin)
    graph.add(scope)
    graph.add(building)
    graph.add(keys)
    graph.add(coin)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=building.uid)

    do_provision(building, ctx=ctx)
    actions = _dynamic_sandbox_actions_with_tag(building, "container")
    fragments = render_block_choices(caller=building, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    put_keys = next(choice for choice in choices if choice.text == "Put keys in chest")

    assert put_keys.available is False
    assert "Take coin from chest" not in {action.text for action in actions}

    fixture_actions = _dynamic_sandbox_actions_with_tag(building, "fixture")
    open_chest = next(action for action in fixture_actions if action.text == "Open chest")
    ledger = Ledger(graph=graph, cursor_id=building.uid)
    ledger.resolve_choice(open_chest.uid)

    assert chest.open is True
    assert chest.container.is_open is True

    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))
    opened_actions = _dynamic_sandbox_actions_with_tag(building, "container")
    fragments = render_block_choices(
        caller=building,
        ctx=PhaseCtx(graph=graph, cursor_id=building.uid),
    )
    opened_choices = [
        fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)
    ]
    opened_put_keys = next(
        choice for choice in opened_choices if choice.text == "Put keys in chest"
    )

    assert opened_put_keys.available is True
    assert "Take coin from chest" in {action.text for action in opened_actions}


def test_portable_container_rejects_nested_container_without_mutation() -> None:
    SandboxItemType(
        label="cage",
        name="cage",
        traits={"container"},
        container=ContainerFacet(),
    )
    SandboxItemType(
        label="bag",
        name="bag",
        traits={"container"},
        container=ContainerFacet(),
    )
    cage = Token[SandboxItemType](token_from="cage", label="cage")
    bag = Token[SandboxItemType](token_from="bag", label="bag")
    holder = SandboxScope(label="tiny_cave_scope").player_assets
    holder.add_asset(cage)
    holder.add_asset(bag)

    result = AssetTransactionManager().can_give_asset(holder, cage.container, "bag")

    assert result.accepted is False
    assert result.reason == "receiver cannot receive asset"
    assert holder.has_asset("bag")
    assert not cage.container.has_asset("bag")


def test_portable_container_open_state_controls_contained_asset_projection() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    building = SandboxLocation(label="building", location_name="Building")
    SandboxItemType(
        label="cage",
        name="cage",
        traits={"container"},
        container=ContainerFacet(close_text="The cage snaps shut."),
    )
    SandboxItemType(label="keys", name="keys", traits={"tiny"})
    cage = Token[SandboxItemType](token_from="cage", label="cage")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    cage.container.add_asset(keys)
    scope.player_assets.add_asset(cage)
    graph.add(scope)
    graph.add(building)
    graph.add(cage)
    graph.add(keys)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=building.uid)

    do_provision(building, ctx=ctx)
    open_actions = _dynamic_sandbox_actions_with_tag(building, "container")
    assert "Take keys from cage" in {action.text for action in open_actions}

    close_cage = next(action for action in open_actions if action.text == "Close cage")
    ledger = Ledger(graph=graph, cursor_id=building.uid)
    ledger.resolve_choice(close_cage.uid)

    assert cage.container.is_open is False
    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))
    closed_actions = _dynamic_sandbox_actions_with_tag(building, "container")
    assert "Take keys from cage" not in {action.text for action in closed_actions}
    assert "Open cage" in {action.text for action in closed_actions}


def test_light_source_inside_carried_container_can_be_reached_in_darkness() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(label="dark_cave", location_name="Dark Cave")
    SandboxItemType(
        label="bag",
        name="bag",
        traits={"container"},
        container=ContainerFacet(),
    )
    SandboxItemType(
        label="lamp",
        name="lamp",
        switchable=SwitchableFacet(),
        light_source=LightSourceFacet(),
    )
    bag = Token[SandboxItemType](token_from="bag", label="bag")
    lamp = Token[SandboxItemType](token_from="lamp", label="lamp")
    bag.container.add_asset(lamp)
    scope.player_assets.add_asset(bag)
    graph.add(scope)
    graph.add(cave)
    graph.add(bag)
    graph.add(lamp)
    scope.add_child(cave)
    ctx = PhaseCtx(graph=graph, cursor_id=cave.uid)

    do_provision(cave, ctx=ctx)
    actions = _dynamic_sandbox_actions_with_tag(cave, "container")

    assert "Take lamp from bag" in {action.text for action in actions}

    take_lamp = next(action for action in actions if action.text == "Take lamp from bag")
    ledger = Ledger(graph=graph, cursor_id=cave.uid)
    ledger.resolve_choice(take_lamp.uid)

    assert scope.player_assets.has_asset("lamp")
    assert not bag.container.has_asset("lamp")

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))
    lit_actions = _dynamic_sandbox_actions_with_tag(cave, "asset")
    assert "Turn on lamp" in {action.text for action in lit_actions}


def test_darkness_rule_substitutes_journal_and_suppresses_local_asset_actions() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(
        label="dark_cave",
        location_name="Dark Cave",
        content="A glittering nugget rests here.",
    )
    start = Block(label="start", content="Begin.")
    SandboxItemType(label="nugget", name="nugget")
    nugget = Token[SandboxItemType](token_from="nugget", label="nugget")
    cave.add_asset(nugget)
    graph.add(scope)
    graph.add(start)
    graph.add(cave)
    graph.add(nugget)
    scope.add_child(cave)
    enter_cave = Action(
        registry=graph,
        label="enter_cave",
        predecessor_id=start.uid,
        successor_id=cave.uid,
        text="Enter cave",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=cave.uid)

    do_provision(cave, ctx=ctx)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.resolve_choice(enter_cave.uid)

    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content == ["It is now pitch dark."]
    assert _dynamic_sandbox_actions_with_tag(cave, "asset") == []


def test_carried_lamp_restores_dark_location_detail_and_asset_affordances() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(
        label="dark_cave",
        location_name="Dark Cave",
        content="A glittering nugget rests here.",
    )
    SandboxItemType(
        label="lamp",
        name="lamp",
        switchable=SwitchableFacet(),
        light_source=LightSourceFacet(),
        turn_on_text="Your lamp is now on.",
    )
    SandboxItemType(label="nugget", name="nugget")
    lamp = Token[SandboxItemType](token_from="lamp", label="lamp")
    nugget = Token[SandboxItemType](token_from="nugget", label="nugget")
    scope.player_assets.add_asset(lamp)
    cave.add_asset(nugget)
    graph.add(scope)
    graph.add(cave)
    graph.add(lamp)
    graph.add(nugget)
    scope.add_child(cave)
    ctx = PhaseCtx(graph=graph, cursor_id=cave.uid)

    do_provision(cave, ctx=ctx)
    dark_actions = _dynamic_sandbox_actions_with_tag(cave, "asset")
    assert [action.text for action in dark_actions] == ["Turn on lamp"]

    turn_on = dark_actions[0]
    ledger = Ledger(graph=graph, cursor_id=cave.uid)
    ledger.resolve_choice(turn_on.uid)

    assert lamp.lit is True
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content[:2] == ["Your lamp is now on.", "A glittering nugget rests here."]

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))
    lit_actions = _dynamic_sandbox_actions_with_tag(cave, "asset")
    assert {action.text for action in lit_actions} == {
        "Drop lamp",
        "Take nugget",
        "Turn off lamp",
    }


def test_scope_donates_wait_to_child_locations() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        wait_text="Pass time",
        wait_turn_delta=2,
        locals={"world_turn": 0},
    )
    road = SandboxLocation(label="road", location_name="Road")
    peer = SandboxLocation(label="peer", location_name="Peer", wait_enabled=False)
    graph.add(scope)
    graph.add(road)
    graph.add(peer)
    scope.add_child(road)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    wait = _dynamic_sandbox_actions_with_tag(road, "wait")[0]

    assert wait.text == "Pass time"
    assert wait.payload["sandbox_action"] == "wait"
    assert wait.payload["turn_delta"] == 2
    assert wait.payload["sandbox_time_cost"].duration == 2
    assert wait.payload["sandbox_time_cost"].kind == "wait"

    do_provision(peer, ctx=PhaseCtx(graph=graph, cursor_id=peer.uid))
    assert _dynamic_sandbox_actions_with_tag(peer, "wait") == []


def test_scope_wait_advances_shared_scope_time() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope", wait_turn_delta=2, locals={"world_turn": 0})
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    scope.add_child(road)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)
    wait = _dynamic_sandbox_actions_with_tag(road, "wait")[0]
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    ledger.resolve_choice(wait.uid, choice_payload=wait.payload)

    assert scope.locals["world_turn"] == 2
    assert current_world_time(building).turn == 2
    assert "world_turn" not in road.locals


def test_scope_scheduled_event_is_donated_to_matching_child_location() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 2},
        scheduled_events=[
            ScheduledEvent(
                label="traveler",
                location="road",
                period=3,
                target="traveler_arrives",
                text="Talk to traveler",
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(traveler)
    scope.add_child(road)
    scope.add_child(building)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))

    road_events = _dynamic_sandbox_actions_with_tag(road, "event")
    building_events = _dynamic_sandbox_actions_with_tag(building, "event")
    assert [event.text for event in road_events] == ["Talk to traveler"]
    assert building_events == []


def test_scope_once_event_triggers_on_entry_returns_and_suppresses_after_target_visit() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        scheduled_events=[
            ScheduledEvent(
                label="first_entry",
                target="orientation",
                text="Take in your surroundings",
                activation="first",
                once=True,
                return_to_location=True,
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road", links={"east": "building"})
    building = SandboxLocation(label="building", location_name="Building", links={"west": "road"})
    cave_entrance = SandboxLocation(label="cave_entrance", location_name="Cave Entrance")
    inside_cave = SandboxLocation(label="inside_cave", location_name="Inside Cave")
    start = Block(label="start", content="Begin.")
    orientation = Block(label="orientation", content="You get your bearings.")
    graph.add(scope)
    graph.add(start)
    graph.add(road)
    graph.add(building)
    graph.add(cave_entrance)
    graph.add(inside_cave)
    graph.add(orientation)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(cave_entrance)
    scope.add_child(inside_cave)
    enter_road = Action(
        registry=graph,
        label="enter_road",
        predecessor_id=start.uid,
        successor_id=road.uid,
        text="Enter sandbox",
    )

    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.resolve_choice(enter_road.uid)

    assert ledger.cursor is road
    assert orientation.locals["_visited"] is True
    assert road.locals["_visited"] is True

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []

    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))
    assert _dynamic_sandbox_actions_with_tag(building, "event") == []


def test_scope_presence_can_gate_scheduled_events() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 2},
        scheduled_presence=[
            ScheduledPresence(
                label="traveler_presence",
                actor="traveler",
                location="road",
                period=3,
            )
        ],
        scheduled_events=[
            ScheduledEvent(
                label="traveler_chat",
                actor="traveler",
                location="road",
                period=3,
                target="traveler_arrives",
                text="Talk to traveler",
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road")
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(scope)
    graph.add(road)
    graph.add(traveler)
    scope.add_child(road)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    assert [event.text for event in _dynamic_sandbox_actions_with_tag(road, "event")] == [
        "Talk to traveler"
    ]

    scope.scheduled_presence = []
    do_provision(road, ctx=ctx)
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []


def test_role_provider_can_donate_sandbox_events() -> None:
    class HelpfulActor(Actor):
        def get_sandbox_events(self, *, caller, ctx, ns):
            if not ns.get("can_pause", True):
                return []
            return [
                ScheduledEvent(
                    label="repair_armor",
                    target="armor_repair",
                    text=f"Ask {self.name} to fix your armor",
                    return_to_location=True,
                )
            ]

    graph = Graph(label="barn_dance")
    scope = SandboxScope(label="barn_dance_scope")
    road = SandboxLocation(label="dance_floor", location_name="Dance Floor")
    repair = Block(label="armor_repair", content="Aria tightens the straps.")
    aria = HelpfulActor(label="aria", name="Aria")
    role = Role(
        label="friend",
        predecessor_id=scope.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    graph.add(scope)
    graph.add(road)
    graph.add(repair)
    graph.add(aria)
    graph.add(role)
    scope.add_child(road)
    role.set_provider(aria)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    events = _dynamic_sandbox_actions_with_tag(road, "event")

    assert [event.text for event in events] == ["Ask Aria to fix your armor"]
    assert events[0].successor is repair
    assert events[0].return_phase is not None

    road.locals["can_pause"] = False
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []
