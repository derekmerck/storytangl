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
    SandboxMap,
    SandboxMapRegion,
    SandboxMob,
    SandboxMobAffordance,
    SandboxScope,
    SandboxTimeCost,
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
from tangl.mechanics.sandbox import handlers as sandbox_handlers
from tangl.mechanics.sandbox import incremental as sandbox_incremental
from tangl.story import Action, Block, Scene, StoryGraph
from tangl.story.concepts import Actor, Role
from tangl.story.concepts.asset import AssetTransactionManager, AssetType
from tangl.story.fragments import ChoiceFragment, ContentFragment
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Ledger, Requirement, ResolutionPhase
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
        "run_day": 1,
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


@pytest.mark.parametrize(
    ("turn", "run_day", "period"),
    [
        (0, 1, 1),
        (3, 1, 4),
        (4, 2, 1),
        (7, 2, 4),
        (44, 12, 1),
        (45, 12, 2),
        (47, 12, 4),
    ],
)
def test_world_time_run_day_is_one_based_and_unbounded(
    turn: int,
    run_day: int,
    period: int,
) -> None:
    world_time = WorldTime.from_turn(turn)

    assert world_time.run_day == run_day
    assert world_time.period == period


def test_world_time_run_day_preserves_weekday_cycle() -> None:
    world_time = WorldTime.from_turn(4 * 7)

    assert world_time.run_day == 8
    assert world_time.day == 1


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


def test_schedule_matches_exact_and_open_ended_run_days() -> None:
    day_twelve_afternoon = WorldTime.from_turn(45)

    assert ScheduleEntry(run_day=12, period=2).matches_time(day_twelve_afternoon)
    assert ScheduleEntry(run_day_from=5).matches_time(day_twelve_afternoon)
    assert not ScheduleEntry(run_day_through=11).matches_time(day_twelve_afternoon)


def test_run_day_matching_is_inherited_by_presence_and_mob_schedules() -> None:
    presence = ScheduledPresence(
        actor="traveler",
        location="road",
        run_day=12,
    )
    mob = SandboxMob(
        label="traveler",
        location="road",
        schedule=Schedule(
            entries=[ScheduleEntry(location="building", run_day_from=5)]
        ),
    )

    assert presence.matches(WorldTime.from_turn(44), location="road")
    assert mob.scheduled_location(WorldTime.from_turn(15)) == "road"
    assert mob.scheduled_location(WorldTime.from_turn(16)) == "building"


@pytest.mark.parametrize(
    "payload",
    [
        {"run_day": 0},
        {"run_day_from": 0},
        {"run_day_through": 0},
        {"run_day_from": 6, "run_day_through": 5},
        {"run_day": 4, "run_day_from": 5},
        {"run_day": 6, "run_day_through": 5},
    ],
)
def test_schedule_rejects_invalid_run_day_declarations(
    payload: dict[str, int],
) -> None:
    with pytest.raises(ValueError):
        ScheduleEntry(**payload)


def test_world_time_is_available_to_location_and_scoped_event_predicates() -> None:
    graph = Graph(label="calendar_predicates")
    scope = SandboxScope(label="calendar_scope", locals={"world_turn": 45})
    road = SandboxLocation(
        label="road",
        availability=[Predicate(expr="world_time.run_day >= 5")],
    )
    scope.scheduled_events = [
        ScheduledEvent(
            label="day_twelve_afternoon",
            target="current",
            run_day=12,
            period=2,
            availability=[
                Predicate(
                    expr="world_time.run_day == 12 and world_time.period == 2"
                )
            ],
        )
    ]
    graph.add(scope)
    graph.add(road)
    scope.add_child(road)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    assert road.available(ctx=ctx)
    do_provision(road, ctx=ctx)
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    assert event.available(ctx=ctx)


def test_sandbox_scope_publishes_world_time_to_descendant_blocks_after_restore() -> None:
    graph = Graph(label="calendar_scope_namespace")
    scope = SandboxScope(label="calendar_scope", locals={"world_turn": 24})
    meeting = Block(
        label="meeting",
        availability=[Predicate(expr="world_time.run_day == 7 and world_time.day == 7")],
    )
    graph.add(scope)
    graph.add(meeting)
    scope.add_child(meeting)
    ctx = PhaseCtx(graph=graph, cursor_id=meeting.uid)

    assert meeting.available(ctx=ctx)
    scope.locals["world_turn"] = 28
    assert not meeting.available(ctx=PhaseCtx(graph=graph, cursor_id=meeting.uid))
    scope.locals["world_turn"] = 24

    restored = Ledger.structure(
        Ledger.from_graph(graph, entry_id=meeting.uid).unstructure()
    )
    restored_meeting = restored.graph.find_one(
        Selector(has_kind=Block, label="meeting")
    )
    assert isinstance(restored_meeting, Block)
    assert restored_meeting.available(
        ctx=PhaseCtx(graph=restored.graph, cursor_id=restored_meeting.uid)
    )


def test_ledger_round_trip_preserves_run_day_and_scheduled_offer() -> None:
    graph = Graph(label="calendar_restore")
    scope = SandboxScope(
        label="calendar_scope",
        locals={"world_turn": 45},
        scheduled_events=[
            ScheduledEvent(
                label="day_twelve_afternoon",
                target="current",
                run_day=12,
                period=2,
                text="Attend the afternoon meeting",
            )
        ],
    )
    road = SandboxLocation(label="road")
    graph.add(scope)
    graph.add(road)
    scope.add_child(road)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    restored = Ledger.structure(ledger.unstructure())
    restored_road = restored.graph.find_one(
        Selector(has_kind=SandboxLocation, label="road")
    )
    assert isinstance(restored_road, SandboxLocation)
    assert current_world_time(restored_road).run_day == 12

    do_provision(
        restored_road,
        ctx=PhaseCtx(graph=restored.graph, cursor_id=restored_road.uid),
    )
    events = _dynamic_sandbox_actions_with_tag(restored_road, "event")
    assert [event.text for event in events] == ["Attend the afternoon meeting"]


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

    events = _dynamic_sandbox_actions_with_tag(road, "event")
    assert [event.text for event in events] == ["Talk to pirate"]
    assert not events[0].available(ctx=PhaseCtx(graph=graph, cursor_id=road.uid))


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
    assert interactions[0].ui_hints.source == "sandbox_mob"
    assert interactions[0].ui_hints.source_label == "pirate"


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
    )
    graph.add(scope)
    graph.add(road)
    graph.add(pirate_chat)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(pirate)

    # ``once`` reads where the reader has been, which the ledger holds and the
    # frame carries on meta - not a flag annotated onto the target.
    do_provision(
        road,
        ctx=PhaseCtx(
            graph=graph,
            cursor_id=road.uid,
            meta={"cursor_history": [pirate_chat.uid]},
        ),
    )

    assert _dynamic_sandbox_actions_with_tag(road, "interaction") == []


def test_a_once_interaction_still_shows_before_its_target_is_visited() -> None:
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
    pirate_chat = Block(label="pirate_chat", content="The pirate talks.")
    graph.add(scope)
    graph.add(road)
    graph.add(pirate_chat)
    graph.add(pirate)
    scope.add_child(road)
    scope.add_child(pirate)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert [a.text for a in _dynamic_sandbox_actions_with_tag(road, "interaction")] == [
        "Talk to the pirate"
    ]


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


def test_block_targeted_interaction_does_not_acquire_a_location_time_charge() -> None:
    graph = Graph(label="interaction_block_target")
    scope = SandboxScope(label="scope", locals={"world_turn": 0})
    road = SandboxLocation(
        label="road",
        interactions=[
            SandboxInteraction(
                label="enter",
                text="Enter the building",
                target="building",
            )
        ],
    )
    building = Block(label="building", content="Inside.")
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    scope.add_child(road)
    scope.add_child(building)
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    interaction = _dynamic_sandbox_actions_with_tag(road, "interaction")[0]

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ledger.resolve_choice(interaction.uid)

    assert ledger.cursor is building
    assert scope.locals["world_turn"] == 0


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
        if action.ui_hints.source == "sandbox_asset"
    ]
    assert {action.text for action in interactions} == {
        "Play the flute",
        "Study the book",
    }
    assert {
        action.ui_hints.asset: action.ui_hints.possession
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
        if action.ui_hints.source == "sandbox_fixture"
    )
    assert interaction.text == "Pray at the altar"
    assert interaction.successor is road
    assert interaction.ui_hints.fixture == "altar"
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
        if choice.ui_hints.source == "sandbox_mob"
        and choice.ui_hints.asset in {"keys", "coin"}
    }

    assert transfer_texts == {"Give keys to pirate", "Take coin from pirate"}
    mob_transfer_actions = [
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "mob")
        if action.ui_hints.asset in {"keys", "coin"}
    ]
    assert all("asset" not in action.tags for action in mob_transfer_actions)

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    take_coin = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "take")
        if action.ui_hints.mob == "pirate"
    )
    ledger.resolve_choice(take_coin.uid)

    assert scope.player_assets.has_asset("coin")
    assert not pirate.has_asset("coin")

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    give_keys = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "give")
        if action.ui_hints.asset == "keys"
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
        if action.ui_hints.asset == "coin"
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
        if action.ui_hints.mob == "pirate"
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
    assert all(action.ui_hints.source == "sandbox_link" for action in actions)
    assert all(action.ui_hints.contribution == "movement" for action in actions)
    assert all(action.ui_hints.source_kind == "location" for action in actions)
    assert all(action.ui_hints.source_label == "road" for action in actions)
    assert all(action.ui_hints.scope == "tiny_cave" for action in actions)


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
    hints = {action.ui_hints.raw_direction: action.ui_hints.direction for action in actions}
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
        and fragment.source_id == colony.uid
        and fragment.origin_id == colony.uid
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


def test_scheduled_event_candidate_becomes_available_without_reprovisioning() -> None:
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
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    assert event.text == "Talk to traveler"
    assert event.successor is traveler
    assert not event.available(ctx=ctx)

    road.locals["world_turn"] = 2
    ctx._ns_cache.clear()
    assert event.available(ctx=ctx)


def test_scheduled_event_targets_a_qualified_block_path() -> None:
    graph = Graph(label="qualified_event")
    road = SandboxLocation(label="road", location_name="Road", locals={"world_turn": 2})
    scene = Scene(label="scene")
    target = Block(label="block", content="The event begins.")
    graph.add(road)
    graph.add(scene)
    graph.add(target)
    scene.add_child(target)
    road.scheduled_events = [
        ScheduledEvent(
            label="traveler",
            location="road",
            period=3,
            target="scene.block",
            text="Talk to traveler",
        ),
    ]

    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)

    [event] = _dynamic_sandbox_actions_with_tag(road, "event")
    assert event.successor is target
    assert event.available(ctx=ctx)

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ledger.resolve_choice(event.uid)
    assert ledger.cursor is target


def test_scheduled_event_with_missing_target_warns_and_stays_inert(caplog: pytest.LogCaptureFixture) -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.locals["world_turn"] = 2
    road.scheduled_events = [
        ScheduledEvent(
            label="traveler",
            location="road",
            period=3,
            target="scene.missing",
            text="Talk to traveler",
        ),
    ]

    with caplog.at_level("WARNING", logger="tangl.mechanics.sandbox.handlers"):
        do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))

    assert _dynamic_sandbox_actions_with_tag(road, "event") == []
    assert "unresolved target 'scene.missing'" in caplog.text


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


def test_scheduled_event_uses_story_disclosure_policy_when_unavailable() -> None:
    graph = StoryGraph(
        label="scheduled_event_disclosure",
        locals={"unavailable_choice_disclosure": "disclose"},
    )
    road = SandboxLocation(
        label="road",
        locals={"world_turn": 1},
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
    traveler = Block(label="traveler_arrives", content="A traveler waves.")
    graph.add(road)
    graph.add(traveler)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)

    disclosed = render_block_choices(caller=road, ctx=ctx) or []
    choice = next(fragment for fragment in disclosed if fragment.text == "Talk to traveler")
    assert choice.available is False

    graph.locals["unavailable_choice_disclosure"] = "hide"
    hidden = render_block_choices(
        caller=road,
        ctx=PhaseCtx(graph=graph, cursor_id=road.uid),
    ) or []
    assert all(fragment.text != "Talk to traveler" for fragment in hidden)


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
    assert event.ui_hints.contribution == "event"
    assert event.journal_text == "The bell rings once."
    assert not event.available(ctx=ctx)

    road.locals["can_ring"] = True
    ctx._ns_cache.clear()
    assert event.available(ctx=ctx)

    Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)

    assert road.locals["bell_rung"] is True


def _event_time_graph(*, return_to_location: bool = False) -> tuple[
    Graph,
    SandboxScope,
    SandboxLocation,
    Block,
]:
    """Build a scheduled event whose block target inherits the scope clock."""
    graph = Graph(label="event_time")
    scope = SandboxScope(label="event_time_scope", locals={"world_turn": 3})
    road = SandboxLocation(
        label="road",
        location_name="Road",
        scheduled_events=[
            ScheduledEvent(
                label="night_event",
                period=4,
                target="event_beat",
                text="Attend the night event",
                return_to_location=return_to_location,
            ),
            ScheduledEvent(
                label="empty_period",
                period=2,
                target="quiet_beat",
                text="Attend the empty-period event",
            ),
        ],
    )
    square = SandboxLocation(
        label="square",
        location_name="Square",
        scheduled_events=[
            ScheduledEvent(
                label="market_event",
                target="market_beat",
                text="Attend the market event",
            )
        ],
    )
    event_beat = Block(label="event_beat", content="The event begins.")
    market_beat = Block(label="market_beat", content="The market opens.")
    quiet_beat = Block(label="quiet_beat", content="Nothing happens.")
    graph.add(scope)
    graph.add(road)
    graph.add(square)
    graph.add(event_beat)
    graph.add(market_beat)
    graph.add(quiet_beat)
    scope.add_child(road)
    scope.add_child(square)
    scope.add_child(event_beat)
    scope.add_child(market_beat)
    scope.add_child(quiet_beat)
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(square, ctx=PhaseCtx(graph=graph, cursor_id=square.uid))
    return graph, scope, road, event_beat


def test_selected_event_does_not_charge_or_change_its_candidate_set() -> None:
    """Scheduled events bind and validate without advancing the sandbox clock."""
    graph, scope, road, event_beat = _event_time_graph()
    event = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "event")
        if action.text == "Attend the night event"
    )
    square = graph.find_one(Selector(has_kind=SandboxLocation, label="square"))

    assert isinstance(square, SandboxLocation)
    assert [action.text for action in _dynamic_sandbox_actions_with_tag(road, "event")] == [
        "Attend the night event",
        "Attend the empty-period event",
    ]
    assert [action.text for action in _dynamic_sandbox_actions_with_tag(square, "event")] == [
        "Attend the market event"
    ]

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ledger.resolve_choice(event.uid)

    assert ledger.cursor is event_beat
    assert scope.locals["world_turn"] == 3
    world_time = current_world_time(event_beat)
    assert world_time.turn == 3


def test_current_target_event_does_not_charge_time() -> None:
    """A self-target scheduled event remains an ordinary no-charge action."""
    graph = Graph(label="current_event_time")
    scope = SandboxScope(label="current_event_scope", locals={"world_turn": 0})
    road = SandboxLocation(
        label="road",
        scheduled_events=[
            ScheduledEvent(label="bell", target="current", text="Ring the bell"),
        ],
    )
    graph.add(scope)
    graph.add(road)
    scope.add_child(road)
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]

    Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)

    assert scope.locals["world_turn"] == 0


def test_returning_event_restore_and_replay_preserve_no_charge() -> None:
    """A restored open event call remains a no-charge binding projection."""
    graph, scope, road, event_beat = _event_time_graph(return_to_location=True)
    ending = Block(label="event_ending", content="The event concludes.")
    alternate = Block(
        label="event_alternate",
        content="The event takes another turn.",
    )
    graph.add(ending)
    graph.add(alternate)
    scope.add_child(ending)
    scope.add_child(alternate)
    internal_choice = Action(
        registry=graph,
        label="event_internal_choice",
        predecessor_id=event_beat.uid,
        successor_id=ending.uid,
        text="Make the internal choice",
    )
    Action(
        registry=graph,
        label="event_alternate_choice",
        predecessor_id=event_beat.uid,
        successor_id=alternate.uid,
        text="Take the alternate choice",
    )
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ledger.checkpoint_cadence = 3

    ledger.resolve_choice(event.uid)
    assert ledger.cursor is event_beat
    assert scope.locals["world_turn"] == 3

    restored = Ledger.structure(ledger.unstructure())
    restored.push_snapshot()
    restored_scope = restored.graph.find_one(Selector(has_kind=SandboxScope))
    restored_road = restored.graph.find_one(
        Selector(has_kind=SandboxLocation, label="road")
    )
    restored_choice = restored.graph.get(internal_choice.uid)

    assert isinstance(restored_scope, SandboxScope)
    assert isinstance(restored_road, SandboxLocation)
    assert isinstance(restored_choice, Action)
    restored.resolve_choice(restored_choice.uid)

    assert restored.cursor is restored_road
    assert restored_scope.locals["world_turn"] == 3

    restored.rollback_to_step(1, reason="replay event entry")
    replayed_scope = restored.graph.find_one(Selector(has_kind=SandboxScope))

    assert isinstance(replayed_scope, SandboxScope)
    assert restored.cursor.get_label() == "event_beat"
    assert replayed_scope.locals["world_turn"] == 3


def test_returning_event_charges_its_scene_exit_after_its_last_internal_choice() -> None:
    """The event remains in its offered period until its call, not its entry, closes."""
    graph = Graph(label="returning_event_time")
    scope = SandboxScope(label="scope", locals={"world_turn": 3})
    road = SandboxLocation(
        label="road",
        scheduled_events=[
            ScheduledEvent(
                label="night_event",
                period=4,
                target="night_scene",
                text="Attend the night event",
                return_to_location=True,
            ),
        ],
    )
    square = SandboxLocation(
        label="square",
        scheduled_events=[
            ScheduledEvent(label="other_offer", period=4, target="other", text="Other offer"),
        ],
    )
    scene = Scene(label="night_scene", locals={"exit_time_cost": {"kind": "event", "duration": 1}})
    start = Block(label="night_start", content="The night begins.")
    ending = Block(label="night_ending", content="The night ends.")
    other = Block(label="other")
    graph.add(scope)
    graph.add(road)
    graph.add(square)
    graph.add(scene)
    graph.add(start)
    graph.add(ending)
    graph.add(other)
    scope.add_child(road)
    scope.add_child(square)
    scope.add_child(scene)
    scope.add_child(other)
    scene.add_child(start)
    scene.add_child(ending)
    scene.finalize_container_contract()
    internal = Action(
        registry=graph,
        label="night_continue",
        predecessor_id=start.uid,
        successor_id=ending.uid,
        availability=[Predicate(expr="world_time.period == 4")],
    )
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(square, ctx=PhaseCtx(graph=graph, cursor_id=square.uid))
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ledger.resolve_choice(event.uid)

    assert ledger.cursor is start
    assert scope.locals["world_turn"] == 3
    assert internal.available(ctx=PhaseCtx(graph=graph, cursor_id=start.uid))
    ledger.resolve_choice(internal.uid)

    assert ledger.cursor is road
    assert scope.locals["world_turn"] == 4
    assert current_world_time(road).period == 1


def test_rejected_event_selection_does_not_change_time() -> None:
    """Validation rejects a stale event without any sandbox clock side effect."""
    graph, scope, road, _event_beat = _event_time_graph()
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    event.availability = [Predicate(expr="False")]

    with pytest.raises(ValueError, match="Edge validation failed"):
        Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)

    assert scope.locals["world_turn"] == 3


def test_stale_scheduled_event_is_rejected_before_entry() -> None:
    """Schedule matching remains a live selection guard, not projection-only."""
    graph, scope, road, _event_beat = _event_time_graph()
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    scope.locals["world_turn"] = 4

    with pytest.raises(ValueError, match="Edge validation failed"):
        Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)

    assert scope.locals["world_turn"] == 4


def test_stale_duplicate_label_event_is_rejected_before_entry() -> None:
    """Live admission remains bound to the selected duplicate-label contribution."""
    graph, scope, road, event_beat = _event_time_graph()
    road.scheduled_events = [
        ScheduledEvent(
            label="shared",
            period=1,
            target=event_beat.get_label(),
            text="First shared event",
        ),
        ScheduledEvent(
            label="shared",
            period=2,
            target=event_beat.get_label(),
            text="Second shared event",
        ),
    ]
    scope.locals["world_turn"] = 1
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    event = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(road, "event")
        if action.text == "Second shared event"
    )
    scope.locals["world_turn"] = 0

    with pytest.raises(ValueError, match="Edge validation failed"):
        Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)

    assert scope.locals["world_turn"] == 0


def test_stale_unlabeled_event_is_rejected_after_schedule_reordering() -> None:
    """Live admission does not use an unlabeled event's current list position."""
    graph, scope, road, event_beat = _event_time_graph()
    first = ScheduledEvent(
        period=1,
        target=event_beat.get_label(),
        text="First unlabeled event",
    )
    second = ScheduledEvent(
        period=2,
        target=event_beat.get_label(),
        text="Second unlabeled event",
    )
    road.scheduled_events = [first, second]
    scope.locals["world_turn"] = 1
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    restored = Ledger.structure(Ledger.from_graph(graph, entry_id=road.uid).unstructure())
    restored_scope = restored.graph.find_one(Selector(has_kind=SandboxScope))
    restored_road = restored.graph.find_one(
        Selector(has_kind=SandboxLocation, label="road")
    )

    assert isinstance(restored_scope, SandboxScope)
    assert isinstance(restored_road, SandboxLocation)
    event = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(restored_road, "event")
        if action.text == "Second unlabeled event"
    )
    restored_road.scheduled_events.reverse()
    restored_scope.locals["world_turn"] = 0

    with pytest.raises(ValueError, match="Edge validation failed"):
        restored.resolve_choice(event.uid)

    assert restored_scope.locals["world_turn"] == 0


def test_scheduled_event_redirect_does_not_charge_time() -> None:
    """A target redirect does not turn a scheduled event into a clock charge."""
    graph, scope, road, event_beat = _event_time_graph()
    landing = Block(label="redirect_landing", content="The event redirects here.")
    graph.add(landing)
    scope.add_child(landing)
    Action(
        registry=graph,
        label="event_prereq_redirect",
        predecessor_id=event_beat.uid,
        successor_id=landing.uid,
        trigger_phase=ResolutionPhase.PREREQS,
    )
    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]

    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ledger.resolve_choice(event.uid)

    assert ledger.cursor is landing
    assert scope.locals["world_turn"] == 3


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
    assert road_events[0].ui_hints.source_kind == "mob"
    assert road_events[0].ui_hints.mob == "pirate"
    building_events = _dynamic_sandbox_actions_with_tag(building, "event")
    assert [event.text for event in building_events] == ["Parley with the pirate"]
    assert not building_events[0].available(
        ctx=PhaseCtx(graph=graph, cursor_id=building.uid)
    )


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


def test_tick_fragments_do_not_replace_suppressed_location_description() -> None:
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
        charge=ChargeFacet(current=1, maximum=1),
    )
    lamp = Token[SandboxItemType](token_from="lamp", label="lamp", lit=True)
    scope.player_assets.add_asset(lamp)
    graph.add(scope)
    graph.add(cave)
    graph.add(lamp)
    scope.add_child(cave)

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))
    wait = _dynamic_sandbox_actions_with_tag(cave, "wait")[0]
    ledger = Ledger(graph=graph, cursor_id=cave.uid)
    ledger.resolve_choice(wait.uid, choice_payload=wait.payload)

    fragments = [
        fragment
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert [fragment.content for fragment in fragments] == [
        "The lamp flickers and goes out.",
        "It is now pitch dark.",
    ]
    assert fragments[0].source_id == lamp.uid
    assert fragments[0].origin_id == lamp.uid
    assert fragments[1].source_id == cave.uid


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


def test_each_sandbox_tick_sees_its_advanced_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = Graph(label="tick_namespace")
    scope = SandboxScope(label="scope", locals={"world_turn": 3})
    road = SandboxLocation(label="road")
    graph.add(scope)
    graph.add(road)
    scope.add_child(road)
    observed: list[tuple[int, int]] = []

    def observe_tick(caller, *, ctx, clock_tick, **_kw):
        observed.append((clock_tick, ctx.get_ns(caller)["world_time"].turn))
        return []

    monkeypatch.setattr(sandbox_handlers, "do_sandbox_tick", observe_tick)
    sandbox_handlers._sandbox_time_advance(
        road,
        ctx=PhaseCtx(graph=graph, cursor_id=road.uid),
        cost=SandboxTimeCost(kind="event", duration=2),
    )

    assert observed == [(4, 4), (5, 5)]


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
    assert [event.text for event in building_events] == ["Talk to traveler"]
    assert not building_events[0].available(
        ctx=PhaseCtx(graph=graph, cursor_id=building.uid)
    )


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

    # The reader really went to ``orientation``, so the ledger's history says so.
    history = {"cursor_history": list(ledger.cursor_history)}
    assert orientation.uid in ledger.cursor_history

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid, meta=history))
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []

    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid, meta=history))
    assert _dynamic_sandbox_actions_with_tag(building, "event") == []


def test_unavailable_triggered_event_does_not_auto_enter() -> None:
    graph = Graph(label="triggered_event_gate")
    scope = SandboxScope(label="scope", locals={"world_turn": 0})
    start = Block(label="start")
    road = SandboxLocation(
        label="road",
        scheduled_events=[
            ScheduledEvent(
                label="late_arrival",
                period=2,
                target="arrival",
                activation="first",
                text="A late arrival",
            )
        ],
    )
    arrival = Block(label="arrival", content="The arrival.")
    graph.add(scope)
    graph.add(start)
    graph.add(road)
    graph.add(arrival)
    scope.add_child(road)
    Action(registry=graph, predecessor_id=start.uid, successor_id=road.uid, text="Enter")

    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    enter = next(iter(start.edges_out(Selector(has_kind=Action))))
    ledger.resolve_choice(enter.uid)

    assert ledger.cursor is road


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

    event = _dynamic_sandbox_actions_with_tag(road, "event")[0]
    scope.scheduled_presence = []
    with pytest.raises(ValueError, match="Edge validation failed"):
        Ledger.from_graph(graph, entry_id=road.uid).resolve_choice(event.uid)


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


def _plate_graph() -> tuple[Graph, SandboxLocation, SandboxLocation]:
    """A map hub whose one neighbour claims a region on the hub's plate."""

    graph = Graph(label="quay")
    scope = SandboxScope(label="quay_scope")
    hub = SandboxLocation(
        label="quay_map",
        location_name="The Quay",
        sandbox_scope="quay",
        links={"in": "mill"},
        map=SandboxMap(
            name="quay",
            plate="quay_map.png",
            regions={
                "mill": SandboxMapRegion(x=0.31, y=0.44, w=0.12, h=0.18),
                "lighthouse": SandboxMapRegion(x=0.80, y=0.12, w=0.10, h=0.22),
            },
        ),
    )
    mill = SandboxLocation(
        label="mill",
        location_name="The Mill",
        sandbox_scope="quay",
        links={"out": "quay_map"},
        plates=["quay:mill", "world:quayside"],
    )
    graph.add(scope)
    graph.add(hub)
    graph.add(mill)
    scope.add_child(hub)
    scope.add_child(mill)
    return graph, hub, mill


def test_travel_choices_inherit_the_plate_regions_their_target_claims() -> None:
    graph, hub, _mill = _plate_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)

    fragments = render_block_choices(caller=hub, ctx=ctx)
    choices = [f for f in fragments or [] if isinstance(f, ChoiceFragment)]
    travel = next(
        choice
        for choice in choices
        if choice.ui_hints.source == "sandbox_link" and choice.ui_hints.target == "mill"
    )

    assert travel.tags == {"ui:plate:quay:mill", "ui:plate:world:quayside"}


def test_choice_tags_expose_the_ui_namespace_and_nothing_else() -> None:
    graph, hub, _mill = _plate_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)
    edge = next(
        action
        for action in _dynamic_sandbox_actions(hub)
        if action.ui_hints.source == "sandbox_link"
    )

    # The edge carries engine internals the client has no business seeing.
    assert {"dynamic", "sandbox", "movement"}.issubset(edge.tags)

    fragments = render_block_choices(caller=hub, ctx=ctx)
    choice = next(
        f
        for f in fragments or []
        if isinstance(f, ChoiceFragment) and f.ui_hints.source == "sandbox_link"
    )

    assert all(tag.startswith("ui:") for tag in choice.tags)


def test_a_location_claiming_no_region_renders_an_untagged_choice() -> None:
    graph, hub, mill = _plate_graph()
    mill.plates = []
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)

    fragments = render_block_choices(caller=hub, ctx=ctx)
    choice = next(
        f
        for f in fragments or []
        if isinstance(f, ChoiceFragment) and f.ui_hints.source == "sandbox_link"
    )

    assert choice.tags == set()


def test_map_travel_fans_out_over_the_regions_locations_claim() -> None:
    graph, hub, _mill = _plate_graph()
    lighthouse = SandboxLocation(
        label="lighthouse",
        location_name="The Lighthouse",
        sandbox_scope="quay",
        plates=["quay:lighthouse"],
    )
    graph.add(lighthouse)
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)

    travel = _dynamic_sandbox_actions_with_tag(hub, "map_travel")
    assert {action.text for action in travel} == {
        "Go to The Mill",
        "Go to The Lighthouse",
    }
    assert {action.ui_hints.region for action in travel} == {"mill", "lighthouse"}
    assert all(action.ui_hints.plate == "quay" for action in travel)


def test_a_region_no_location_claims_projects_no_travel() -> None:
    graph, hub, _mill = _plate_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)

    travel = _dynamic_sandbox_actions_with_tag(hub, "map_travel")
    # The plate declares "lighthouse"; nothing claims it, so the hitbox is inert.
    assert [action.ui_hints.region for action in travel] == ["mill"]


def test_map_travel_is_offered_on_the_destinations_own_terms() -> None:
    graph, hub, mill = _plate_graph()
    scope = graph.find_one(Selector.from_identifier("quay_scope"))
    mill.availability = [Predicate(expr="mill_is_open")]
    scope.locals["mill_is_open"] = False
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)
    travel = next(iter(_dynamic_sandbox_actions_with_tag(hub, "map_travel")))

    assert not travel.available(ctx=ctx)

    scope.locals["mill_is_open"] = True
    assert travel.available(ctx=ctx)


def test_unreachable_map_travel_renders_dimmed_rather_than_absent() -> None:
    graph, hub, mill = _plate_graph()
    scope = graph.find_one(Selector.from_identifier("quay_scope"))
    mill.availability = [Predicate(expr="mill_is_open")]
    scope.locals["mill_is_open"] = False
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)

    fragments = render_block_choices(caller=hub, ctx=ctx)
    choice = next(
        f
        for f in fragments or []
        if isinstance(f, ChoiceFragment)
        and getattr(f.ui_hints, "region", None) == "mill"
    )

    assert not choice.available
    assert choice.unavailable_reason
    assert choice.tags == {"ui:plate:quay:mill", "ui:plate:world:quayside"}


def test_a_region_two_locations_claim_projects_no_travel(caplog) -> None:
    """An ambiguous hitbox is left inert rather than silently resolved."""

    graph, hub, mill = _plate_graph()
    rival = SandboxLocation(
        label="rival_mill",
        location_name="The Other Mill",
        sandbox_scope="quay",
        plates=["quay:mill"],
    )
    graph.add(rival)
    graph.find_one(Selector.from_identifier("quay_scope")).add_child(rival)
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    with caplog.at_level("WARNING"):
        do_provision(hub, ctx=ctx)

    assert _dynamic_sandbox_actions_with_tag(hub, "map_travel") == []
    assert "claimed by" in caplog.text


def test_an_authored_travel_action_inherits_the_regions_claim() -> None:
    """A hand-written action keeps its region rather than losing the hitbox."""

    graph, hub, mill = _plate_graph()
    authored = Action(
        registry=graph,
        label="authored_walk",
        predecessor_id=hub.uid,
        successor_id=mill.uid,
        text="Walk down to the mill",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)

    # No rival generated action competes with the authored one...
    assert _dynamic_sandbox_actions_with_tag(hub, "map_travel") == []
    # ...and the authored action is what the region now binds to.
    assert "ui:plate:quay:mill" in authored.tags

    fragments = render_block_choices(caller=hub, ctx=ctx)
    choice = next(
        f
        for f in fragments or []
        if isinstance(f, ChoiceFragment) and f.text == "Walk down to the mill"
    )
    assert choice.tags == {"ui:plate:quay:mill", "ui:plate:world:quayside"}


def test_repeated_provisioning_does_not_stack_map_travel() -> None:
    """Planning runs every step; generated travel must not accumulate."""

    graph, hub, _mill = _plate_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    do_provision(hub, ctx=ctx)
    first = len(_dynamic_sandbox_actions_with_tag(hub, "map_travel"))
    do_provision(hub, ctx=ctx)
    do_provision(hub, ctx=ctx)

    assert first == 1
    assert len(_dynamic_sandbox_actions_with_tag(hub, "map_travel")) == first


def test_two_authored_routes_to_one_region_leave_it_inert(caplog) -> None:
    """Walking and sailing to the same quay is not a basis for owning a hitbox."""

    graph, hub, mill = _plate_graph()
    for label, text in (("walk_to_mill", "Walk"), ("sail_to_mill", "Sail")):
        Action(
            registry=graph,
            label=label,
            predecessor_id=hub.uid,
            successor_id=mill.uid,
            text=text,
        )
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid)

    with caplog.at_level("WARNING"):
        do_provision(hub, ctx=ctx)

    # Neither authored route takes the claim, and no rival is generated.
    fragments = render_block_choices(caller=hub, ctx=ctx)
    claimed = [
        f
        for f in fragments or []
        if isinstance(f, ChoiceFragment) and f.text in {"Walk", "Sail"} and f.tags
    ]
    assert claimed == []
    assert _dynamic_sandbox_actions_with_tag(hub, "map_travel") == []
    assert "authored routes" in caplog.text

    # Both routes are still offered; only the hitbox is withheld.
    offered = {
        f.text for f in fragments or []
        if isinstance(f, ChoiceFragment) and f.text in {"Walk", "Sail"}
    }
    assert offered == {"Walk", "Sail"}
