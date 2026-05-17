"""Projected-state adapter for sandbox disclosure surfaces."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, cast

from tangl.core import Selector, Token
from tangl.service.response import (
    ItemListValue,
    KvListValue,
    ProjectedItem,
    ProjectedKVItem,
    ProjectedSection,
    ProjectedState,
)
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
        projection = sandbox_projection_state(cursor, ctx)
        sections = [
            self._location_section(cursor, projection_active=projection.active),
            self._time_section(cursor),
            self._inventory_section(cursor),
        ]
        if not projection.suppress_location_description:
            sections.append(self._exits_section(cursor))
        if not projection.suppress_asset_affordances:
            sections.append(self._local_assets_section(cursor))
        if not projection.suppress_fixture_affordances:
            sections.append(self._fixtures_section(cursor))
        if not projection.suppress_location_description:
            sections.append(self._presence_section(cursor))
        return ProjectedState(
            sections=[
                section
                for section in sections
                if not _section_empty(section)
            ]
        )

    def _location_section(
        self,
        location: SandboxLocation,
        *,
        projection_active: bool,
    ) -> ProjectedSection:
        items = [
            ProjectedKVItem(key="Location", value=location.location_name or location.get_label())
        ]
        if projection_active:
            items.append(ProjectedKVItem(key="Visibility", value="limited"))
        return ProjectedSection(
            section_id="sandbox_location",
            title="Location",
            kind="location",
            value=KvListValue(items=items),
        )

    def _time_section(self, location: SandboxLocation) -> ProjectedSection:
        world_time = current_world_time(location)
        items = [
            ProjectedKVItem(key="Turn", value=world_time.turn),
            ProjectedKVItem(
                key="Period",
                value=_period_label(world_time.period, self.period_labels),
            ),
            ProjectedKVItem(key="Day", value=world_time.day),
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
    "SandboxStoryInfoProjector",
]
