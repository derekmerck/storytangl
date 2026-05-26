from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from tangl.core import Graph, Priority, Selector, Token
from tangl.journal.intent import KvRow
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
from tangl.mechanics.sandbox.handlers import sandbox_player_assets
from tangl.mechanics.sandbox.story_info import SandboxStoryInfoProjector
from tangl.service.response import KvListValue, ProjectedSection, ProjectedState
from tangl.story import Action, StoryGraph
from tangl.story.concepts.asset import AssetTransactionManager
from tangl.vm import Ledger, on_gather_ns, on_provision, on_update
from tangl.vm.ctx import VmPhaseCtx


TREASURE_LABEL = "gold_nugget"


class AdventureMagicAnchor(BaseModel):
    """One Adventure-style magic-word hop sponsored by a location."""

    word: str
    target: str
    journal_text: str
    requires_discovery: bool = False


class AdventureMovementHazard(BaseModel):
    """Movement rewrite/block rule selected by Adventure domain state."""

    direction: str
    carried_asset: str | None = None
    outcome: str = "block"
    journal_text: str


class AdventureSandboxLocation(SandboxLocation):
    """A demo Adventure-like location using the generic sandbox handlers."""

    treasure_deposit_site: bool = False
    magic_anchors: list[AdventureMagicAnchor] = Field(default_factory=list)
    movement_hazards: list[AdventureMovementHazard] = Field(default_factory=list)


def _location(graph: Graph, label: str) -> AdventureSandboxLocation:
    location = graph.find_one(Selector.from_identifier(label))
    if not isinstance(location, AdventureSandboxLocation):
        raise ValueError(f"Adventure sandbox location {label!r} is missing")
    return location


def _asset_type(label: str, **values: object) -> SandboxCompiledAssetType:
    existing = SandboxCompiledAssetType.get_instance(label)
    if existing is not None:
        return existing
    return SandboxCompiledAssetType(label=label, **values)


def _graph_frozen_shape(graph: Graph) -> bool:
    return isinstance(graph, StoryGraph) and graph.frozen_shape


def _add_asset(
    graph: Graph,
    label: str,
    location: AdventureSandboxLocation,
    **values: object,
) -> Token[SandboxCompiledAssetType]:
    asset_type = _asset_type(label, **values)
    asset = Token[SandboxCompiledAssetType](token_from=label, label=label)
    graph.add(asset)
    location.add_asset(asset)
    return asset


def _adventure_scope(location: AdventureSandboxLocation) -> SandboxScope:
    scope = _maybe_adventure_scope(location)
    if scope is None:
        raise ValueError("Adventure sandbox location is not under its sandbox scope")
    return scope


def _maybe_adventure_scope(location: AdventureSandboxLocation) -> SandboxScope | None:
    for candidate in location.ancestors:
        if isinstance(candidate, SandboxScope):
            return candidate
    return None


def _adventure_score(location: AdventureSandboxLocation) -> int:
    scope = _adventure_scope(location)
    return int(scope.locals.get("adventure_score", 0))


def _deposited_treasures(location: AdventureSandboxLocation) -> list[str]:
    scope = _adventure_scope(location)
    raw = scope.locals.setdefault("deposited_treasures", [])
    if not isinstance(raw, list):
        raise TypeError("deposited_treasures must be a list")
    return raw


def _treasure_deposited(location: AdventureSandboxLocation, label: str) -> bool:
    return label in _deposited_treasures(location)


def _player_has_asset(location: AdventureSandboxLocation, label: str) -> bool:
    holder = sandbox_player_assets(location)
    return bool(holder and holder.get_asset(label) is not None)


def _clear_adventure_actions(location: AdventureSandboxLocation, ctx: VmPhaseCtx) -> None:
    for edge in list(location.edges_out(Selector(has_kind=Action))):
        if {"dynamic", "sandbox", "adventure"}.issubset(edge.tags or set()):
            location.graph.remove(edge.uid, _ctx=ctx)


def _adventure_payload(kind: str, **extra: object) -> dict[str, object]:
    return {
        "adventure_action": kind,
        "sandbox_time_cost": {"kind": "adventure", "duration": 0},
        **extra,
    }


def _project_adventure_action(
    location: AdventureSandboxLocation,
    *,
    text: str,
    action: str,
    target: AdventureSandboxLocation,
    journal_text: str,
    **hints: object,
) -> None:
    Action(
        registry=location.graph,
        label=f"adventure_{action}_{location.get_label()}",
        predecessor_id=location.uid,
        successor_id=target.uid,
        text=text,
        payload=_adventure_payload(action, **hints),
        journal_text=journal_text,
        tags={"dynamic", "sandbox", "adventure", action},
        ui_hints={
            "source_kind": "world_authority",
            "contribution": action,
            **hints,
        },
    )


def _asset_score(asset: Token) -> int:
    score = getattr(asset, "treasure_score", 0)
    return int(score)


def _held_treasures(location: AdventureSandboxLocation) -> list[Token]:
    holder = sandbox_player_assets(location)
    if holder is None:
        return []
    treasures: list[Token] = []
    for asset in holder.assets.values():
        if "treasure" in asset.traits:
            treasures.append(asset)
    return treasures


def _deposit_treasure(location: AdventureSandboxLocation, label: str) -> None:
    if _treasure_deposited(location, label):
        return
    holder = sandbox_player_assets(location)
    if holder is None:
        return
    asset = holder.get_asset(label)
    if asset is None:
        return
    AssetTransactionManager().give_asset(holder, location, label)
    scope = _adventure_scope(location)
    _deposited_treasures(location).append(label)
    scope.locals["adventure_score"] = _adventure_score(location) + _asset_score(asset)


def _magic_word_known(location: AdventureSandboxLocation, word: str) -> bool:
    scope = _adventure_scope(location)
    known = scope.locals.setdefault("magic_words_known", [])
    if not isinstance(known, list):
        raise TypeError("magic_words_known must be a list")
    return word.lower() in {str(item).lower() for item in known}


def _movement_hazard_applies(
    location: AdventureSandboxLocation,
    hazard: AdventureMovementHazard,
) -> bool:
    if hazard.carried_asset is None:
        return True
    return _player_has_asset(location, hazard.carried_asset)


def _rewrite_movement_hazards(
    location: AdventureSandboxLocation,
    ctx: VmPhaseCtx,
) -> None:
    graph = location.graph
    if graph is None:
        return
    for hazard in location.movement_hazards:
        if not _movement_hazard_applies(location, hazard):
            continue
        for edge in list(location.edges_out(Selector(has_kind=Action))):
            if not {"dynamic", "sandbox", "movement"}.issubset(edge.tags or set()):
                continue
            hints = edge.ui_hints.model_dump()
            if hints.get("direction") != hazard.direction:
                continue
            graph.remove(edge.uid, _ctx=ctx)
            Action(
                registry=graph,
                label=f"adventure_hazard_{location.get_label()}_{hazard.direction}",
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=edge.text,
                payload=_adventure_payload(
                    "movement_hazard",
                    direction=hazard.direction,
                    outcome=hazard.outcome,
                ),
                journal_text=hazard.journal_text,
                tags={"dynamic", "sandbox", "adventure", "movement", "hazard"},
                ui_hints={
                    **hints,
                    "source_kind": "world_authority",
                    "contribution": "movement_hazard",
                    "hazard_outcome": hazard.outcome,
                },
            )


class AdventureSandboxStoryInfoProjector:
    """Adventure-specific story-info wrapper over the generic sandbox projector."""

    def __init__(self) -> None:
        self.sandbox = SandboxStoryInfoProjector()

    def project(self, *, ledger: Ledger) -> ProjectedState:
        projected = self.sandbox.project(ledger=ledger)
        cursor = ledger.cursor
        if not isinstance(cursor, AdventureSandboxLocation):
            return projected
        return ProjectedState(
            sections=[
                *projected.sections,
                ProjectedSection(
                    section_id="adventure_score",
                    title="Score",
                    kind="score",
                    value=KvListValue(
                        items=[
                            KvRow(key="Score", value=_adventure_score(cursor), max=350),
                            KvRow(
                                key="Deposited",
                                value=len(_deposited_treasures(cursor)),
                                unit="treasure",
                            ),
                        ]
                    ),
                ),
            ]
        )


def get_story_info_projector() -> AdventureSandboxStoryInfoProjector:
    """Return the Adventure-specific projected-state adapter."""
    return AdventureSandboxStoryInfoProjector()


def _ensure_adventure_sandbox(graph: Graph) -> None:
    if graph.find_one(Selector.from_identifier("cave")) is not None:
        return

    scope = SandboxScope(
        label="cave",
        locals={
            "world_turn": 0,
            "adventure_score": 0,
            "deposited_treasures": [],
            "magic_words_known": [],
        },
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
    _add_asset(
        graph,
        TREASURE_LABEL,
        cobble_crawl,
        name="gold nugget",
        kind="treasure",
        traits={"portable", "treasure"},
        portable=True,
        treasure_score=10,
        treasure_loss_penalty=5,
        read_text="It is a large sparkling nugget of gold.",
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


@on_provision(
    wants_caller_kind=AdventureSandboxLocation,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def setup_adventure_sandbox(
    *,
    caller: AdventureSandboxLocation,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Attach the demo's shared sandbox state before location planning."""

    _ = ctx
    _ensure_adventure_sandbox(caller.graph)
    return None


@on_gather_ns(
    wants_caller_kind=AdventureSandboxLocation,
    wants_exact_kind=False,
)
def contribute_adventure_score(
    *,
    caller: AdventureSandboxLocation,
    **_kw: object,
) -> dict[str, int]:
    """Publish Adventure-specific score facts for journal formatting."""
    if _maybe_adventure_scope(caller) is None:
        return {"adventure_score": 0, "adventure_deposited_count": 0}
    return {
        "adventure_score": _adventure_score(caller),
        "adventure_deposited_count": len(_deposited_treasures(caller)),
    }


@on_provision(
    wants_caller_kind=AdventureSandboxLocation,
    wants_exact_kind=False,
    priority=Priority.LAST,
)
def project_adventure_world_actions(
    *,
    caller: AdventureSandboxLocation,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Project Adventure-specific charm/rules as ordinary sandbox actions."""
    if not caller.auto_provision:
        return None
    graph = caller.graph
    if graph is None or _graph_frozen_shape(graph):
        return None

    _clear_adventure_actions(caller, ctx)
    _rewrite_movement_hazards(caller, ctx)

    if caller.treasure_deposit_site:
        for treasure in _held_treasures(caller):
            treasure_label = treasure.get_label()
            if _treasure_deposited(caller, treasure_label):
                continue
            treasure_name = treasure.name or treasure_label
            _project_adventure_action(
                caller,
                text=f"Deposit the {treasure_name}",
                action="deposit_treasure",
                target=caller,
                journal_text=(
                    f"The {treasure_name} is safely deposited in the well house. "
                    "Your score has increased."
                ),
                asset=treasure_label,
            )

    for anchor in caller.magic_anchors:
        if anchor.requires_discovery and not _magic_word_known(caller, anchor.word):
            continue
        target = _location(graph, anchor.target)
        _project_adventure_action(
            caller,
            text=f"Say {anchor.word.upper()}",
            action="magic_word",
            target=target,
            journal_text=anchor.journal_text,
            word=anchor.word.upper(),
        )
    return None


@on_update(
    wants_caller_kind=AdventureSandboxLocation,
    wants_exact_kind=False,
)
def apply_adventure_world_action(
    *,
    caller: AdventureSandboxLocation,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Apply Adventure-specific world-authority action effects."""
    payload = getattr(ctx, "selected_payload", None)
    if not isinstance(payload, dict):
        return None
    if payload.get("adventure_action") == "deposit_treasure":
        asset = payload.get("asset")
        if isinstance(asset, str):
            _deposit_treasure(caller, asset)
    return None


AdventureSandboxLocation.model_rebuild(_types_namespace={"UUID": UUID})
