"""Sandbox projected-state adapter contracts."""

from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Graph, Selector, Token
from tangl.mechanics.sandbox import (
    ChargeFacet,
    ContainerFacet,
    LightSourceFacet,
    LockableFacet,
    OpenableFacet,
    SandboxExit,
    SandboxFixture,
    SandboxLocation,
    SandboxMap,
    SandboxMapRegion,
    SandboxMob,
    SandboxScope,
    SandboxVisibilityRule,
    SwitchableFacet,
)
from tangl.mechanics.sandbox.story_info import SandboxStoryInfoProjector
from tangl.service.dispatch import do_advertise_info_channels, do_get_story_info
from tangl.service.response import (
    ItemListValue,
    KvListValue,
    ProjectedSection,
    StoryInfoRequest,
    TableValue,
)
from tangl.story.concepts.asset import AssetType
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.runtime.ledger import Ledger


class SandboxInfoItemType(AssetType):
    name: str = ""
    traits: set[str] = Field(default_factory=set)
    portable: bool = True
    lit: bool = Field(default=False, json_schema_extra={"instance_var": True})
    charge: ChargeFacet | None = Field(
        default=None,
        json_schema_extra={"instance_var": True},
    )
    container: ContainerFacet | None = Field(
        default=None,
        json_schema_extra={"instance_var": True},
    )
    light_source: LightSourceFacet | None = None
    switchable: SwitchableFacet | None = None


@pytest.fixture(autouse=True)
def _clear_sandbox_info_item_types() -> None:
    """Clear singleton item fixtures before and after each test for isolation."""
    SandboxInfoItemType.clear_instances()
    yield
    SandboxInfoItemType.clear_instances()


def _section_by_id(sections: list[ProjectedSection]) -> dict[str, ProjectedSection]:
    return {section.section_id: section for section in sections}


def _item_labels(section: ProjectedSection) -> list[str]:
    assert isinstance(section.value, ItemListValue)
    return [item.label for item in section.value.items]


def test_sandbox_story_info_projects_disclosed_location_state() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope", locals={"world_turn": 2})
    road = SandboxLocation(
        label="road",
        location_name="End of Road",
        links={"east": "building"},
        fixtures=[
            SandboxFixture(
                label="grate",
                name="steel grate",
                openable=OpenableFacet(is_open=False),
                lockable=LockableFacet(is_locked=True),
            )
        ],
    )
    building = SandboxLocation(label="building", location_name="Inside Building")
    pirate = SandboxMob(
        label="pirate",
        name="wounded pirate",
        location="road",
        traits={"injured"},
    )
    SandboxInfoItemType(
        label="lamp",
        name="brass lantern",
        traits={"portable"},
        charge=ChargeFacet(current=25, maximum=30, charge_name="oil"),
    )
    SandboxInfoItemType(label="keys", name="set of keys", traits={"portable", "tiny"})
    lamp = Token[SandboxInfoItemType](token_from="lamp", label="lamp")
    keys = Token[SandboxInfoItemType](token_from="keys", label="keys")
    scope.player_assets.add_asset(lamp)
    road.add_asset(keys)
    for item in (scope, road, building, pirate, lamp, keys):
        graph.add(item)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)
    scope.mobs.append(pirate)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    projected = SandboxStoryInfoProjector().project(ledger=ledger)
    sections = _section_by_id(projected.sections)

    assert set(sections) == {
        "sandbox_location",
        "sandbox_time",
        "sandbox_inventory",
        "sandbox_exits",
        "sandbox_local_assets",
        "sandbox_fixtures",
        "sandbox_presence",
    }
    assert isinstance(sections["sandbox_time"].value, KvListValue)
    assert [(item.key, item.value) for item in sections["sandbox_time"].value.items] == [
        ("Turn", 2),
        ("Period", "evening"),
        ("Day", 1),
    ]
    assert _item_labels(sections["sandbox_inventory"]) == ["brass lantern"]
    inventory = sections["sandbox_inventory"].value
    assert isinstance(inventory, ItemListValue)
    assert inventory.items[0].detail == "25 oil"
    assert _item_labels(sections["sandbox_local_assets"]) == ["set of keys"]
    assert _item_labels(sections["sandbox_fixtures"]) == ["steel grate"]
    assert _item_labels(sections["sandbox_presence"]) == ["wounded pirate"]
    assert _item_labels(sections["sandbox_exits"]) == ["east"]


def test_sandbox_story_info_hides_suppressed_surroundings_but_keeps_inventory() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(
        label="dark_cave",
        location_name="Dark Cave",
        links={"west": "deeper_cave"},
        fixtures=[SandboxFixture(label="grate", name="steel grate")],
    )
    deeper = SandboxLocation(label="deeper_cave", location_name="Deeper Cave")
    pirate = SandboxMob(label="pirate", name="wounded pirate", location="dark_cave")
    SandboxInfoItemType(label="lamp", name="brass lantern")
    SandboxInfoItemType(label="nugget", name="gold nugget")
    lamp = Token[SandboxInfoItemType](token_from="lamp", label="lamp")
    nugget = Token[SandboxInfoItemType](token_from="nugget", label="nugget")
    scope.player_assets.add_asset(lamp)
    cave.add_asset(nugget)
    for item in (scope, cave, deeper, pirate, lamp, nugget):
        graph.add(item)
    scope.add_child(cave)
    scope.add_child(deeper)
    scope.add_child(pirate)
    scope.mobs.append(pirate)
    ledger = Ledger.from_graph(graph, entry_id=cave.uid)

    projected = SandboxStoryInfoProjector().project(ledger=ledger)
    sections = _section_by_id(projected.sections)

    assert set(sections) == {
        "sandbox_location",
        "sandbox_time",
        "sandbox_inventory",
    }
    assert _item_labels(sections["sandbox_inventory"]) == ["brass lantern"]
    assert isinstance(sections["sandbox_location"].value, KvListValue)
    assert ("Visibility", "limited") in [
        (item.key, item.value) for item in sections["sandbox_location"].value.items
    ]


def test_sandbox_advertises_map_info_channel() -> None:
    graph = Graph(label="tiny_cave")
    road = SandboxLocation(label="road", location_name="End of Road")
    graph.add(road)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid, step=ledger.step)

    affordances = do_advertise_info_channels(road, ctx=ctx)

    assert [affordance.kind for affordance in affordances] == [
        "world_time",
        "location",
        "inventory",
        "map",
        "local_assets",
        "fixtures",
        "presence",
        "exits",
    ]
    map_affordance = next(
        affordance for affordance in affordances if affordance.kind == "map"
    )
    assert map_affordance.query == {"kinds": ["map"], "scope": "known"}


def test_sandbox_dispatch_projects_requested_status_channels() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope", locals={"world_turn": 1})
    road = SandboxLocation(
        label="road",
        location_name="End of Road",
        links={"east": "building"},
    )
    building = SandboxLocation(label="building", location_name="Inside Building")
    pirate = SandboxMob(label="pirate", name="wounded pirate", location="road")
    SandboxInfoItemType(label="lamp", name="brass lantern", traits={"portable"})
    lamp = Token[SandboxInfoItemType](token_from="lamp", label="lamp")
    scope.player_assets.add_asset(lamp)
    for item in (scope, road, building, pirate, lamp):
        graph.add(item)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(pirate)
    scope.mobs.append(pirate)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid, step=ledger.step)

    projected = do_get_story_info(
        road,
        ctx=ctx,
        request=StoryInfoRequest(
            kinds=["location", "world_time", "inventory", "presence", "exits"]
        ),
    )
    sections = _section_by_id(projected.sections)

    assert set(sections) == {
        "sandbox_location",
        "sandbox_time",
        "sandbox_inventory",
        "sandbox_presence",
        "sandbox_exits",
    }
    assert _item_labels(sections["sandbox_inventory"]) == ["brass lantern"]
    assert _item_labels(sections["sandbox_presence"]) == ["wounded pirate"]
    assert _item_labels(sections["sandbox_exits"]) == ["east"]


def test_sandbox_dispatch_filters_requested_status_channels() -> None:
    graph = Graph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="End of Road",
        links={"east": "building"},
    )
    building = SandboxLocation(label="building", location_name="Inside Building")
    for item in (road, building):
        graph.add(item)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid, step=ledger.step)

    projected = do_get_story_info(
        road,
        ctx=ctx,
        request=StoryInfoRequest(kind="location"),
    )
    assert [section.section_id for section in projected.sections] == [
        "sandbox_location"
    ]

    map_nodes = do_get_story_info(
        road,
        ctx=ctx,
        request=StoryInfoRequest(kind="map_nodes"),
    )
    assert [section.section_id for section in map_nodes.sections] == [
        "sandbox_map_nodes"
    ]


def test_sandbox_dispatch_empty_request_stays_explicit_only() -> None:
    graph = Graph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="End of Road",
        links={"east": "building"},
    )
    building = SandboxLocation(label="building", location_name="Inside Building")
    for item in (road, building):
        graph.add(item)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid, step=ledger.step)

    projected = do_get_story_info(
        road,
        ctx=ctx,
        request=StoryInfoRequest(),
    )

    assert projected.sections == []


def test_sandbox_map_projects_known_geography_as_portable_sections() -> None:
    graph = Graph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="End of Road",
        links={
            "east": "building",
            "down": SandboxExit(target="below_grate", through="grate"),
        },
        fixtures=[
            SandboxFixture(
                label="grate",
                name="steel grate",
                openable=OpenableFacet(is_open=False),
                lockable=LockableFacet(is_locked=True),
            )
        ],
    )
    building = SandboxLocation(label="building", location_name="Inside Building")
    below = SandboxLocation(label="below_grate", location_name="Below the Grate")
    for item in (road, building, below):
        graph.add(item)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid, step=ledger.step)

    projected = do_get_story_info(
        road,
        ctx=ctx,
        request=StoryInfoRequest(kind="map"),
    )
    sections = _section_by_id(projected.sections)

    assert set(sections) == {
        "sandbox_map_summary",
        "sandbox_map_nodes",
        "sandbox_map_edges",
    }
    summary = sections["sandbox_map_summary"].value
    assert isinstance(summary, KvListValue)
    assert [(item.key, item.value) for item in summary.items] == [
        ("Current", "End of Road"),
        ("Known locations", 3),
        ("Known exits", 2),
    ]
    assert _item_labels(sections["sandbox_map_nodes"]) == [
        "Below the Grate",
        "Inside Building",
        "End of Road",
    ]
    edges = sections["sandbox_map_edges"].value
    assert isinstance(edges, TableValue)
    assert edges.columns == ["From", "Direction", "To", "State"]
    assert edges.rows == [
        ["End of Road", "down", "Below the Grate", "locked, closed"],
        ["End of Road", "east", "Inside Building", "open"],
    ]


def test_sandbox_map_honors_visibility_suppression() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(
        label="dark_cave",
        location_name="Dark Cave",
        links={"west": "deeper_cave"},
    )
    deeper = SandboxLocation(label="deeper_cave", location_name="Deeper Cave")
    for item in (scope, cave, deeper):
        graph.add(item)
    scope.add_child(cave)
    scope.add_child(deeper)
    ledger = Ledger.from_graph(graph, entry_id=cave.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=cave.uid, step=ledger.step)

    projected = do_get_story_info(
        cave,
        ctx=ctx,
        request=StoryInfoRequest(kind="map"),
    )
    sections = _section_by_id(projected.sections)

    assert _item_labels(sections["sandbox_map_nodes"]) == ["Dark Cave"]
    edges = sections["sandbox_map_edges"].value
    assert isinstance(edges, TableValue)
    assert edges.rows == []


def _plate_hub() -> tuple[Graph, SandboxLocation]:
    graph = Graph(label="quay")
    hub = SandboxLocation(
        label="quay_map",
        location_name="The Quay",
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
    mill = SandboxLocation(label="mill", location_name="The Mill", plates=["quay:mill"])
    graph.add(hub)
    graph.add(mill)
    return graph, hub


def test_sandbox_plate_geometry_projects_when_asked_for_by_name() -> None:
    graph, hub = _plate_hub()
    ledger = Ledger.from_graph(graph, entry_id=hub.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid, step=ledger.step)

    projected = do_get_story_info(
        hub,
        ctx=ctx,
        request=StoryInfoRequest(kinds=["map_plate", "map_regions"]),
    )

    sections = _section_by_id(projected.sections)
    plate = sections["sandbox_map_plate"]
    assert isinstance(plate.value, KvListValue)
    assert [(row.key, row.value) for row in plate.value.items] == [
        ("Name", "quay"),
        ("Image", "quay_map.png"),
        ("Regions", 2),
    ]

    regions = sections["sandbox_map_regions"]
    assert isinstance(regions.value, TableValue)
    assert regions.value.columns == ["Region", "x", "y", "w", "h"]
    assert regions.value.rows == [
        ["lighthouse", 0.80, 0.12, 0.10, 0.22],
        ["mill", 0.31, 0.44, 0.12, 0.18],
    ]


def test_sandbox_map_channel_stays_reader_facing() -> None:
    """The gazetteer must not hand a text client a table of hitboxes."""

    graph, hub = _plate_hub()
    ledger = Ledger.from_graph(graph, entry_id=hub.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=hub.uid, step=ledger.step)

    projected = do_get_story_info(hub, ctx=ctx, request=StoryInfoRequest(kind="map"))

    assert "sandbox_map_nodes" in _section_by_id(projected.sections)
    assert "sandbox_map_plate" not in _section_by_id(projected.sections)
    assert "sandbox_map_regions" not in _section_by_id(projected.sections)


def test_sandbox_plate_channel_is_advertised_only_by_the_plate_owner() -> None:
    graph, hub = _plate_hub()
    mill = graph.find_one(Selector.from_identifier("mill"))
    ledger = Ledger.from_graph(graph, entry_id=hub.uid)

    hub_ctx = PhaseCtx(graph=graph, cursor_id=hub.uid, step=ledger.step)
    mill_ctx = PhaseCtx(graph=graph, cursor_id=mill.uid, step=ledger.step)

    hub_kinds = {a.kind for a in do_advertise_info_channels(hub, ctx=hub_ctx)}
    mill_kinds = {a.kind for a in do_advertise_info_channels(mill, ctx=mill_ctx)}

    assert "map_plate" in hub_kinds
    assert "map_plate" not in mill_kinds
