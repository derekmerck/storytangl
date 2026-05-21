from __future__ import annotations

from uuid import UUID

from tangl.core import Priority, Selector, Token
from tangl.mechanics.sandbox import (
    ChargeFacet,
    ContainerFacet,
    LightSourceFacet,
    LockableFacet,
    OpenableFacet,
    SandboxCompiledAssetType,
    SandboxFixture,
    SandboxLocation,
    SandboxMob,
    SandboxMobAffordance,
    SandboxScope,
    SandboxVisibilityRule,
    SwitchableFacet,
)
from tangl.vm import on_prereqs


class AdventureSandboxLocation(SandboxLocation):
    """A demo Adventure-like location using the generic sandbox handlers."""


def _location(graph, label: str) -> AdventureSandboxLocation:
    location = graph.find_one(Selector.from_identifier(label))
    if not isinstance(location, AdventureSandboxLocation):
        raise ValueError(f"Adventure sandbox location {label!r} is missing")
    return location


def _asset_type(label: str, **values) -> SandboxCompiledAssetType:
    existing = SandboxCompiledAssetType.get_instance(label)
    if existing is not None:
        return existing
    return SandboxCompiledAssetType(label=label, **values)


def _add_asset(graph, label: str, location: AdventureSandboxLocation, **values) -> Token:
    asset_type = _asset_type(label, **values)
    asset = Token[SandboxCompiledAssetType](token_from=label, label=label)
    graph.add(asset)
    location.add_asset(asset)
    return asset


def _ensure_adventure_sandbox(graph) -> None:
    if graph.find_one(Selector.from_identifier("cave")) is not None:
        return

    scope = SandboxScope(
        label="cave",
        locals={"world_turn": 0},
        visibility_rules=[
            SandboxVisibilityRule(
                journal_text=(
                    "It is now pitch dark. If you proceed you will likely fall "
                    "into a pit."
                )
            )
        ],
        wait_enabled=True,
        wait_text="Wait",
        wait_turn_delta=1,
    )
    graph.add(scope)

    locations = [
        location
        for location in graph.find_all(Selector(has_kind=AdventureSandboxLocation))
    ]
    for location in locations:
        location.sandbox_scope = "cave"
        scope.add_child(location)

    building = _location(graph, "building")
    outside_grate = _location(graph, "outside_grate")
    below_grate = _location(graph, "below_grate")
    cobble_crawl = _location(graph, "cobble_crawl")

    _add_asset(
        graph,
        "keys",
        building,
        name="set of keys",
        kind="keyring",
        traits={"portable", "tiny"},
        portable=True,
        read_text="It's just a normal-looking set of keys.",
        take_text="Taken.",
        drop_text="Dropped.",
    )
    _add_asset(
        graph,
        "brass_lamp",
        building,
        name="brass lantern",
        kind="lamp",
        traits={"portable", "switchable", "provides_light", "requires_charge"},
        portable=True,
        switchable=SwitchableFacet(),
        light_source=LightSourceFacet(requires_switch=True),
        lit=False,
        charge=ChargeFacet(current=330, maximum=330, charge_name="oil"),
        read_text="It is a shiny brass lamp.",
        turn_on_text="Your lamp is now on.",
        turn_off_text="Your lamp is now off.",
        take_text="Taken.",
        drop_text="Dropped.",
    )
    _add_asset(
        graph,
        "wicker_cage",
        cobble_crawl,
        name="wicker cage",
        kind="container",
        traits={"portable", "container"},
        portable=True,
        container=ContainerFacet(
            is_open=True,
            max_items=1,
            accepts_traits={"tiny"},
            open_text="The cage opens.",
            close_text="The cage snaps shut.",
        ),
        read_text="It's a small wicker cage.",
        take_text="Taken.",
        drop_text="Dropped.",
    )

    grate = SandboxFixture(
        label="grate",
        name="steel grate",
        lockable=LockableFacet(
            key="keys",
            is_locked=True,
            unlock_text="The key turns with a click. The grate unlocks.",
        ),
        openable=OpenableFacet(
            is_open=False,
            open_text="The grate opens.",
            close_text="The grate closes.",
        ),
    )
    outside_grate.fixtures.append(grate)
    below_grate.fixtures.append(grate)

    pirate = SandboxMob(
        label="wounded_pirate",
        name="wounded pirate",
        kind="mobile_actor",
        traits={"mobile", "audible_nearby", "can_carry"},
        location="cobble_crawl",
        state={"hp": 3, "injured": True, "hostile": False},
        present_text="A wounded pirate leans against the wall, watching you.",
        nearby_text="You hear someone breathing raggedly nearby.",
        affordances=[
            SandboxMobAffordance(
                label="help",
                text="Make sure the wounded pirate is okay",
                journal_text="The pirate eyes you suspiciously, but accepts your help.",
                state_effects={"helped": True, "hostile": False},
            )
        ],
    )
    graph.add(pirate)
    scope.add_child(pirate)
    scope.mobs.append(pirate)


@on_prereqs(
    wants_caller_kind=AdventureSandboxLocation,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def setup_adventure_sandbox(*, caller, ctx, **_kw):
    """Attach the demo's shared sandbox state before location planning."""

    if not isinstance(caller, AdventureSandboxLocation):
        return None
    _ensure_adventure_sandbox(caller.graph)
    return None


AdventureSandboxLocation.model_rebuild(_types_namespace={"UUID": UUID})
