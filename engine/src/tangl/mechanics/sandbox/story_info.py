"""Projected-state adapter for sandbox disclosure surfaces."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, cast

from tangl.core import Selector, Token
from tangl.service.response import (
    InfoAffordance,
    ItemListValue,
    KvListValue,
    ProjectedItem,
    KvRow,
    ProjectedSection,
    ProjectedState,
    StoryInfoRequest,
    TableValue,
)
from tangl.service.dispatch import on_advertise_info_channels, on_get_story_info
from tangl.service.story_info import DEFAULT_STORY_INFO_PROJECTOR
from tangl.story.concepts.asset import HasAssets
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.runtime.ledger import Ledger

from .handlers import (
    sandbox_player_assets,
    sandbox_present_mobs,
    sandbox_projection_state,
)
from .facets import ChargeFacet, ContainerFacet
from .location import SandboxExit, SandboxFixture, SandboxLocation, normalize_sandbox_direction
from .time import current_world_time


DEFAULT_PERIOD_LABELS = ("morning", "afternoon", "evening", "night")
MAP_KIND = "map"
SANDBOX_INFO_KINDS = {
    "exits",
    "fixtures",
    "inventory",
    "local_assets",
    "location",
    MAP_KIND,
    "map_edges",
    "map_nodes",
    "presence",
    "world_time",
}


class ProjectedAssetSurface(Protocol):
    """Minimal asset-token surface disclosed through story-info projection."""

    name: str
    traits: set[str]
    lit: bool
    charge: ChargeFacet | None
    container: ContainerFacet | None

    def get_label(self) -> str | None:
        """Return the graph/token label."""
        ...


class SandboxStoryInfoProjector:
    """Project disclosed sandbox state into generic ``ProjectedState`` sections."""

    def __init__(self, *, period_labels: Sequence[str] = DEFAULT_PERIOD_LABELS) -> None:
        self.period_labels = tuple(period_labels)

    def project(self, *, ledger: Ledger) -> ProjectedState:
        """Return portable state sections for the current sandbox location."""
        cursor = ledger.cursor
        if not isinstance(cursor, SandboxLocation):
            return DEFAULT_STORY_INFO_PROJECTOR.project(ledger=ledger)

        ctx = PhaseCtx(graph=ledger.graph, cursor_id=cursor.uid)
        return ProjectedState(sections=self.sections_for(cursor, ctx=ctx))

    def sections_for(
        self,
        location: SandboxLocation,
        *,
        ctx: PhaseCtx,
    ) -> list[ProjectedSection]:
        """Return disclosed sandbox status sections for ``location``."""
        projection = sandbox_projection_state(location, ctx)
        sections = [
            self._location_section(location, projection_active=projection.active),
            self._time_section(location),
            self._inventory_section(location),
        ]
        if not projection.suppress_location_description:
            sections.append(self._exits_section(location))
        if not projection.suppress_asset_affordances:
            sections.append(self._local_assets_section(location))
        if not projection.suppress_fixture_affordances:
            sections.append(self._fixtures_section(location))
        if not projection.suppress_location_description:
            sections.append(self._presence_section(location))
        return [section for section in sections if not _section_empty(section)]

    def _location_section(
        self,
        location: SandboxLocation,
        *,
        projection_active: bool,
    ) -> ProjectedSection:
        items = [
            KvRow(key="Location", value=location.location_name or location.get_label())
        ]
        if projection_active:
            items.append(KvRow(key="Visibility", value="limited"))
        return ProjectedSection(
            section_id="sandbox_location",
            title="Location",
            kind="location",
            value=KvListValue(items=items),
        )

    def _time_section(self, location: SandboxLocation) -> ProjectedSection:
        world_time = current_world_time(location)
        items = [
            KvRow(key="Turn", value=world_time.turn),
            KvRow(
                key="Period",
                value=_period_label(world_time.period, self.period_labels),
            ),
            KvRow(key="Day", value=world_time.day),
        ]
        return ProjectedSection(
            section_id="sandbox_time",
            title="Time",
            kind="world_time",
            value=KvListValue(items=items),
        )

    def _inventory_section(self, location: SandboxLocation) -> ProjectedSection:
        return ProjectedSection(
            section_id="sandbox_inventory",
            title="Inventory",
            kind="inventory",
            value=ItemListValue(items=_asset_items(sandbox_player_assets(location))),
        )

    def _local_assets_section(self, location: SandboxLocation) -> ProjectedSection:
        return ProjectedSection(
            section_id="sandbox_local_assets",
            title="Here",
            kind="local_assets",
            value=ItemListValue(items=_asset_items(location)),
        )

    def _fixtures_section(self, location: SandboxLocation) -> ProjectedSection:
        return ProjectedSection(
            section_id="sandbox_fixtures",
            title="Fixtures",
            kind="fixtures",
            value=ItemListValue(
                items=[_fixture_item(fixture) for fixture in location.fixtures]
            ),
        )

    def _presence_section(self, location: SandboxLocation) -> ProjectedSection:
        return ProjectedSection(
            section_id="sandbox_presence",
            title="Present",
            kind="presence",
            value=ItemListValue(
                items=[
                    ProjectedItem(
                        label=mob.name or mob.get_label(),
                        tags=["mob", *sorted(mob.traits)],
                    )
                    for mob in sandbox_present_mobs(location)
                ]
            ),
        )

    def _exits_section(self, location: SandboxLocation) -> ProjectedSection:
        return ProjectedSection(
            section_id="sandbox_exits",
            title="Exits",
            kind="exits",
            value=ItemListValue(
                items=[
                    _exit_item(location, direction=direction, exit_value=exit_value)
                    for direction, exit_value in sorted(location.links.items())
                ]
            ),
        )


@on_advertise_info_channels(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def advertise_sandbox_info_channels(
    *,
    caller: SandboxLocation,
    ctx: PhaseCtx,
    **_kw: object,
) -> list[InfoAffordance]:
    """Advertise sandbox story-info channels for the active location."""
    projection = sandbox_projection_state(caller, ctx)
    affordances = [
        InfoAffordance(
            kind="world_time",
            label="Watch",
            shortcuts=["t", "time"],
            query={"kinds": ["world_time"]},
        ),
        InfoAffordance(
            kind="location",
            label="Here",
            shortcuts=["h", "look"],
            query={"kinds": ["location", "presence"]},
        ),
        InfoAffordance(
            kind="inventory",
            label="Carrying",
            shortcuts=["i", "inv"],
            query={"kinds": ["inventory"]},
        ),
        InfoAffordance(
            kind=MAP_KIND,
            label="Map",
            shortcuts=["m", MAP_KIND],
            query={"kinds": [MAP_KIND], "scope": "known"},
        ),
    ]
    if projection.suppress_location_description:
        return affordances
    if not projection.suppress_asset_affordances:
        affordances.append(
            InfoAffordance(
                kind="local_assets",
                label="Here",
                shortcuts=["a", "assets"],
                query={"kinds": ["local_assets"]},
            )
        )
    if not projection.suppress_fixture_affordances:
        affordances.append(
            InfoAffordance(
                kind="fixtures",
                label="Fixtures",
                shortcuts=["f"],
                query={"kinds": ["fixtures"]},
            )
        )
    affordances.append(
        InfoAffordance(
            kind="presence",
            label="Present",
            shortcuts=["p"],
            query={"kinds": ["presence"]},
        )
    )
    affordances.append(
        InfoAffordance(
            kind="exits",
            label="Exits",
            shortcuts=["x"],
            query={"kinds": ["exits"]},
        )
    )
    return affordances


@on_get_story_info(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_map_info(
    *,
    caller: SandboxLocation,
    ctx: PhaseCtx,
    request: StoryInfoRequest,
    **_kw: object,
) -> list[ProjectedSection] | None:
    """Project requested disclosed sandbox channels for side-panel clients."""
    requested = set(request.requested_kinds())
    if not requested:
        return None
    if requested.isdisjoint(SANDBOX_INFO_KINDS):
        return None

    sections: list[ProjectedSection] = []
    status_sections = SandboxStoryInfoProjector().sections_for(caller, ctx=ctx)
    sections.extend(
        section
        for section in status_sections
        if _section_matches_requested(section, requested)
    )

    map_sections = _requested_map_sections(caller, ctx=ctx, requested=requested)
    sections.extend(map_sections)
    return sections or None


def _requested_map_sections(
    location: SandboxLocation,
    *,
    ctx: PhaseCtx,
    requested: set[str],
) -> list[ProjectedSection]:
    if not _map_requested(requested):
        return []
    sections = _map_sections(location, ctx)
    if MAP_KIND in requested:
        return sections
    return [
        section
        for section in sections
        if _section_matches_requested(section, requested)
    ]


def _map_requested(requested: set[str]) -> bool:
    return not requested.isdisjoint({MAP_KIND, "map_nodes", "map_edges"})


def _map_sections(location: SandboxLocation, ctx: PhaseCtx) -> list[ProjectedSection]:
    nodes = _known_map_locations(location, ctx)
    edge_rows = _map_edge_rows(location, ctx=ctx, known_locations=nodes)
    return [
        ProjectedSection(
            section_id="sandbox_map_summary",
            title="Map",
            kind=MAP_KIND,
            value=KvListValue(
                items=[
                    KvRow(
                        key="Current",
                        value=location.location_name or location.get_label(),
                    ),
                    KvRow(key="Known locations", value=len(nodes)),
                    KvRow(key="Known exits", value=len(edge_rows)),
                ]
            ),
        ),
        ProjectedSection(
            section_id="sandbox_map_nodes",
            title="Known Places",
            kind="map_nodes",
            value=ItemListValue(
                items=[_map_node_item(node, current=location) for node in nodes]
            ),
        ),
        ProjectedSection(
            section_id="sandbox_map_edges",
            title="Known Paths",
            kind="map_edges",
            value=TableValue(
                columns=["From", "Direction", "To", "State"],
                rows=edge_rows,
            ),
        ),
    ]


def _known_map_locations(
    location: SandboxLocation,
    ctx: PhaseCtx,
) -> list[SandboxLocation]:
    projection = sandbox_projection_state(location, ctx)
    known_by_label: dict[str, SandboxLocation] = {location.get_label(): location}
    for candidate in location.graph.find_all(Selector(has_kind=SandboxLocation)):
        if not isinstance(candidate, SandboxLocation):
            continue
        if candidate.locals.get("_visited"):
            known_by_label[candidate.get_label()] = candidate
    if not projection.suppress_location_description:
        for exit_value in location.links.values():
            target = _exit_target_location(location, exit_value)
            if target is not None:
                known_by_label.setdefault(target.get_label(), target)
    return sorted(known_by_label.values(), key=lambda node: node.get_label())


def _map_edge_rows(
    location: SandboxLocation,
    *,
    ctx: PhaseCtx,
    known_locations: list[SandboxLocation],
) -> list[list[str]]:
    known_labels = {node.get_label() for node in known_locations}
    projection = sandbox_projection_state(location, ctx)
    rows: list[list[str]] = []
    for source in known_locations:
        source_is_disclosed = source.locals.get("_visited") or (
            source is location and not projection.suppress_location_description
        )
        if not source_is_disclosed:
            continue
        for direction, exit_value in sorted(source.links.items()):
            rows.append(
                _map_edge_row(
                    source,
                    direction=direction,
                    exit_value=exit_value,
                    known_labels=known_labels,
                )
            )
    return rows


def _map_node_item(
    location: SandboxLocation,
    *,
    current: SandboxLocation,
) -> ProjectedItem:
    tags = ["location"]
    detail: str | None = None
    if location is current:
        tags.append("current")
        detail = "current"
    elif location.locals.get("_visited"):
        tags.append("visited")
        detail = "visited"
    else:
        tags.append("adjacent")
        detail = "nearby"
    return ProjectedItem(
        label=location.location_name or location.get_label(),
        detail=detail,
        tags=tags,
    )


def _map_edge_row(
    source: SandboxLocation,
    *,
    direction: str,
    exit_value: str | SandboxExit,
    known_labels: set[str],
) -> list[str]:
    target = _exit_target_location(source, exit_value)
    target_label = _map_target_label(
        target=target,
        target_ref=exit_value.target if isinstance(exit_value, SandboxExit) else exit_value,
        known_labels=known_labels,
    )
    return [
        source.location_name or source.get_label(),
        normalize_sandbox_direction(direction),
        target_label,
        _map_exit_state(source, exit_value),
    ]


def _exit_target_location(
    location: SandboxLocation,
    exit_value: str | SandboxExit,
) -> SandboxLocation | None:
    target_ref = exit_value.target if isinstance(exit_value, SandboxExit) else exit_value
    if target_ref is None:
        return None
    target = location.graph.find_one(Selector(label=target_ref))
    if isinstance(target, SandboxLocation):
        return target
    return None


def _map_target_label(
    *,
    target: SandboxLocation | None,
    target_ref: str | None,
    known_labels: set[str],
) -> str:
    if target is None:
        return (target_ref or "unknown").replace("_", " ")
    if target.get_label() in known_labels:
        return target.location_name or target.get_label()
    return "undiscovered"


def _map_exit_state(
    location: SandboxLocation,
    exit_value: str | SandboxExit,
) -> str:
    if isinstance(exit_value, SandboxExit) and exit_value.kind == "message":
        return "blocked"
    parts: list[str] = ["open"]
    if isinstance(exit_value, SandboxExit) and exit_value.through:
        try:
            fixture = location.fixture_by_label(exit_value.through)
        except KeyError:
            parts.append(f"via {exit_value.through}")
        else:
            parts = [_fixture_map_state(fixture)]
    return ", ".join(parts)


def _fixture_map_state(fixture: SandboxFixture) -> str:
    parts: list[str] = []
    if fixture.lockable is not None:
        parts.append("locked" if fixture.locked else "unlocked")
    if fixture.openable is not None:
        parts.append("open" if fixture.open else "closed")
    if not parts:
        parts.append("open")
    return ", ".join(parts)


def _period_label(period: int, labels: Sequence[str]) -> str:
    if 1 <= period <= len(labels):
        return labels[period - 1]
    return str(period)


def _section_empty(section: ProjectedSection) -> bool:
    value = section.value
    if isinstance(value, KvListValue):
        return not value.items
    if isinstance(value, ItemListValue):
        return not value.items
    return False


def _section_matches_requested(
    section: ProjectedSection,
    requested: set[str],
) -> bool:
    labels = {section.section_id}
    if section.kind is not None:
        labels.add(section.kind)
    return not labels.isdisjoint(requested)


def _asset_items(holder: HasAssets | None) -> list[ProjectedItem]:
    if holder is None:
        return []
    return [
        _asset_item(asset_label, asset)
        for asset_label, asset in sorted(holder.assets.items())
    ]


def _asset_item(asset_label: str, asset: Token) -> ProjectedItem:
    surface = _asset_surface(asset)
    return ProjectedItem(
        label=_asset_name(surface, fallback=asset_label),
        detail=_asset_detail(surface),
        tags=_asset_tags(surface),
    )


def _asset_surface(asset: Token) -> ProjectedAssetSurface:
    return cast(ProjectedAssetSurface, asset)


def _asset_name(asset: ProjectedAssetSurface, *, fallback: str) -> str:
    name = asset.name
    if name:
        return str(name)
    label = asset.get_label()
    if label:
        return label.replace("_", " ")
    return fallback.replace("_", " ")


def _asset_detail(asset: ProjectedAssetSurface) -> str | None:
    detail: list[str] = []
    if asset.lit:
        detail.append("lit")
    charge = asset.charge
    if isinstance(charge, ChargeFacet):
        detail.append(f"{charge.current} {charge.charge_name}")
    container = asset.container
    if container is not None:
        detail.append("open" if container.is_open else "closed")
    return ", ".join(detail) or None


def _asset_tags(asset: ProjectedAssetSurface) -> list[str]:
    tags = {"asset"}
    tags.update(str(trait) for trait in asset.traits)
    if asset.lit:
        tags.add("lit")
    if isinstance(asset.charge, ChargeFacet):
        tags.add("charged")
    if asset.container is not None:
        tags.add("container")
    return sorted(tags)


def _fixture_item(fixture: SandboxFixture) -> ProjectedItem:
    detail_parts: list[str] = []
    if fixture.lockable is not None:
        detail_parts.append("locked" if fixture.locked else "unlocked")
    if fixture.openable is not None:
        detail_parts.append("open" if fixture.open else "closed")
    tags = ["fixture"]
    if fixture.lockable is not None:
        tags.append("lockable")
    if fixture.openable is not None:
        tags.append("openable")
    if fixture.container is not None:
        tags.append("container")
    return ProjectedItem(
        label=fixture.name or fixture.label,
        detail=", ".join(detail_parts) or None,
        tags=tags,
    )


def _exit_item(
    location: SandboxLocation,
    *,
    direction: str,
    exit_value: str | SandboxExit,
) -> ProjectedItem:
    label = normalize_sandbox_direction(direction)
    target_ref = exit_value.target if isinstance(exit_value, SandboxExit) else exit_value
    if isinstance(exit_value, SandboxExit) and exit_value.kind == "message":
        return ProjectedItem(label=label, detail="blocked", tags=["exit", "message"])
    return ProjectedItem(
        label=label,
        detail=_target_name(location, target_ref),
        tags=["exit"],
    )


def _target_name(location: SandboxLocation, target_ref: str | None) -> str | None:
    if target_ref is None:
        return None
    target = location.graph.find_one(Selector(label=target_ref))
    if isinstance(target, SandboxLocation):
        return target.location_name or target.get_label()
    return target_ref.replace("_", " ")


__all__ = [
    "DEFAULT_PERIOD_LABELS",
    "MAP_KIND",
    "SandboxStoryInfoProjector",
    "advertise_sandbox_info_channels",
    "project_sandbox_map_info",
]
