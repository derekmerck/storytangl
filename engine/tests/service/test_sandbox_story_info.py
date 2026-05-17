"""Sandbox projected-state adapter contracts."""

from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Graph, Token
from tangl.mechanics.sandbox import (
    ChargeFacet,
    LightSourceFacet,
    LockableFacet,
    OpenableFacet,
    SandboxFixture,
    SandboxLocation,
    SandboxMob,
    SandboxScope,
    SandboxVisibilityRule,
    SwitchableFacet,
)
from tangl.mechanics.sandbox.story_info import SandboxStoryInfoProjector
from tangl.service.response import ItemListValue, KvListValue, ProjectedSection
from tangl.story.concepts.asset import AssetType
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
