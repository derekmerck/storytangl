"""Experimental compiler for compact sandbox slice specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tangl.core import Token
from tangl.story import StoryGraph
from tangl.story.concepts.asset import AssetType

from .location import SandboxExit, SandboxLocation, SandboxLockable
from .mob import SandboxMob, SandboxMobAffordance
from .scope import SandboxScope
from .visibility import SandboxVisibilityRule


class SandboxCompiledAssetType(AssetType):
    """Asset type used by the compact sandbox slice compiler."""

    name: str = ""
    kind: str = ""
    portable: bool = False
    readable: bool = False
    read_text: str | None = None
    light_source: bool = False
    lit: bool = Field(default=False, json_schema_extra={"instance_var": True})
    charge: int | None = Field(default=None, json_schema_extra={"instance_var": True})
    turn_on_text: str | None = None
    turn_off_text: str | None = None
    take_text: str | None = None
    drop_text: str | None = None


class SandboxSourceSpec(BaseModel):
    """Optional source provenance for a compact sandbox slice."""

    kind: str = ""
    path: str = ""
    stance: str = ""
    notes: str = ""


class SandboxStableMaterializationSpec(BaseModel):
    """Concept labels that need stable runtime identity before first visit."""

    locations: list[str] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    mobs: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)


class SandboxMaterializationSpec(BaseModel):
    """Materialization policy hints for compact sandbox slices."""

    policy: str = "eager"
    stable: SandboxStableMaterializationSpec = Field(
        default_factory=SandboxStableMaterializationSpec
    )
    notes: str = ""


class SandboxScopeVisibilitySpec(BaseModel):
    """Scope-level visibility phrasing for compact sandbox slices."""

    darkness_text: str = "It is pitch dark."


class SandboxScopeSpec(BaseModel):
    """Authored sandbox scope data."""

    id: str
    state: dict[str, Any] = Field(default_factory=dict)
    visibility: SandboxScopeVisibilitySpec = Field(
        default_factory=SandboxScopeVisibilitySpec
    )
    materialization: SandboxMaterializationSpec = Field(
        default_factory=SandboxMaterializationSpec
    )


class SandboxRuntimeIdentitySpec(BaseModel):
    """Optional per-concept runtime identity hint."""

    stable: bool = False
    notes: str = ""


class SandboxDescriptionSpec(BaseModel):
    """Common description slots used by the compact sandbox schema."""

    model_config = ConfigDict(extra="allow")

    look: str | None = None
    first: str | None = None
    lit: str | None = None
    dark: str | None = None
    repeat: str | None = None
    ambient: str | None = None
    present: str | None = None
    nearby: str | None = None
    examine: str | None = None
    take: str | None = None
    drop: str | None = None
    turn_on: str | None = None
    turn_off: str | None = None
    unlock: str | None = None
    open: str | None = None
    close: str | None = None


class SandboxExitSpec(BaseModel):
    """Structured sandbox exit declaration."""

    kind: str | None = None
    target: str | None = None
    to: str | None = None
    text: str | None = None
    journal: str | None = None
    journal_text: str | None = None
    through: str | None = None

    def as_sandbox_exit(self) -> SandboxExit:
        """Return the runtime sandbox exit object."""
        return SandboxExit(
            target=self.target or self.to,
            text=self.text,
            kind=self.kind,
            journal_text=self.journal_text or self.journal,
            through=self.through,
        )


class SandboxLocationSpec(BaseModel):
    """Authored compact sandbox location."""

    model_config = ConfigDict(extra="allow")

    name: str
    region: str = ""
    traits: list[str] = Field(default_factory=list)
    descriptions: SandboxDescriptionSpec = Field(default_factory=SandboxDescriptionSpec)
    exits: dict[str, str | SandboxExitSpec] = Field(default_factory=dict)
    runtime_identity: SandboxRuntimeIdentitySpec = Field(
        default_factory=SandboxRuntimeIdentitySpec
    )


class SandboxInitialAssetSpec(BaseModel):
    """Initial placement and state for one compiled asset."""

    location: str
    state: dict[str, Any] = Field(default_factory=dict)


class SandboxAssetSpec(BaseModel):
    """Authored compact sandbox asset."""

    model_config = ConfigDict(extra="allow")

    name: str
    kind: str = ""
    traits: list[str] = Field(default_factory=list)
    initial: SandboxInitialAssetSpec
    descriptions: SandboxDescriptionSpec = Field(default_factory=SandboxDescriptionSpec)
    runtime_identity: SandboxRuntimeIdentitySpec = Field(
        default_factory=SandboxRuntimeIdentitySpec
    )


class SandboxInitialFixtureSpec(BaseModel):
    """Initial placement and state for one compiled fixture."""

    locations: list[str] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)


class SandboxFixtureSpec(BaseModel):
    """Authored compact sandbox fixture."""

    model_config = ConfigDict(extra="allow")

    name: str
    kind: str = ""
    traits: list[str] = Field(default_factory=list)
    initial: SandboxInitialFixtureSpec = Field(default_factory=SandboxInitialFixtureSpec)
    key: str = "key"
    descriptions: SandboxDescriptionSpec = Field(default_factory=SandboxDescriptionSpec)
    runtime_identity: SandboxRuntimeIdentitySpec = Field(
        default_factory=SandboxRuntimeIdentitySpec
    )


class SandboxInitialMobSpec(BaseModel):
    """Initial placement and state for one compiled mob."""

    location: str
    state: dict[str, Any] = Field(default_factory=dict)


class SandboxMobActionSpec(BaseModel):
    """Authored compact mob affordance."""

    text: str
    journal: str | None = None
    journal_text: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)

    def as_affordance(self, label: str) -> SandboxMobAffordance:
        """Return the runtime mob affordance object."""
        return SandboxMobAffordance(
            label=label,
            text=self.text,
            journal_text=self.journal_text or self.journal or "",
            state_effects=dict(self.state),
        )


class SandboxMobContributionsSpec(BaseModel):
    """Authored contribution tables for one compact mob."""

    affordances: dict[str, SandboxMobActionSpec] = Field(default_factory=dict)


class SandboxMobSpec(BaseModel):
    """Authored compact sandbox mob."""

    model_config = ConfigDict(extra="allow")

    name: str
    kind: str = ""
    traits: list[str] = Field(default_factory=list)
    initial: SandboxInitialMobSpec
    descriptions: SandboxDescriptionSpec = Field(default_factory=SandboxDescriptionSpec)
    contributes: SandboxMobContributionsSpec = Field(
        default_factory=SandboxMobContributionsSpec
    )
    runtime_identity: SandboxRuntimeIdentitySpec = Field(
        default_factory=SandboxRuntimeIdentitySpec
    )


class SandboxSliceSpec(BaseModel):
    """Compact sandbox slice IR for exploratory story demos."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str = ""
    source: SandboxSourceSpec | None = None
    scope: SandboxScopeSpec
    locations: dict[str, SandboxLocationSpec] = Field(default_factory=dict)
    assets: dict[str, SandboxAssetSpec] = Field(default_factory=dict)
    fixtures: dict[str, SandboxFixtureSpec] = Field(default_factory=dict)
    mobs: dict[str, SandboxMobSpec] = Field(default_factory=dict)


@dataclass(slots=True)
class SandboxCompiledSlice:
    """Compiled runtime surface for one compact sandbox slice."""

    graph: StoryGraph
    scope: SandboxScope
    locations: dict[str, SandboxLocation]
    assets: dict[str, Token]
    fixtures: dict[str, SandboxLockable]
    mobs: dict[str, SandboxMob]
    materialization: SandboxMaterializationSpec = field(
        default_factory=SandboxMaterializationSpec
    )
    source_map: dict[str, Any] = field(default_factory=dict)
    codec_state: dict[str, Any] = field(default_factory=dict)


class SandboxSliceCompiler:
    """Compile compact sandbox slice data into runtime sandbox objects.

    This is an experimental mechanics-level compiler boundary. It intentionally
    stops short of the full world-bundle loader path: codecs and bundle assembly
    can use this shape later, but this compiler only lowers compact sandbox
    facts into a runtime `StoryGraph` that exercises the current mechanics.

    It should stay aligned with the loader compiler split:

    * source-format cleanup and extraction belongs in a `StoryCodec`;
    * world-specific authorities belong in domain modules/registries;
    * this compiler owns only the compact sandbox IR to sandbox runtime lowering.
    """

    @staticmethod
    def validate_ir(data: dict[str, Any]) -> SandboxSliceSpec:
        """Validate raw compact sandbox slice data."""
        return SandboxSliceSpec.model_validate(data)

    def compile(
        self,
        data: dict[str, Any] | SandboxSliceSpec,
        *,
        source_map: dict[str, Any] | None = None,
        codec_state: dict[str, Any] | None = None,
    ) -> SandboxCompiledSlice:
        """Compile compact sandbox slice data into runtime sandbox objects."""
        spec = data if isinstance(data, SandboxSliceSpec) else self.validate_ir(data)
        graph = StoryGraph(label=spec.id)
        scope = self._compile_scope(spec)
        graph.add(scope)

        locations = self._compile_locations(graph=graph, scope=scope, spec=spec)
        assets = self._compile_assets(graph=graph, locations=locations, spec=spec)
        fixtures = self._compile_fixtures(locations=locations, spec=spec)
        mobs = self._compile_mobs(
            graph=graph,
            scope=scope,
            locations=locations,
            spec=spec,
        )

        return SandboxCompiledSlice(
            graph=graph,
            scope=scope,
            locations=locations,
            assets=assets,
            fixtures=fixtures,
            mobs=mobs,
            materialization=spec.scope.materialization,
            source_map=dict(source_map or {}),
            codec_state=dict(codec_state or {}),
        )

    def _compile_scope(self, spec: SandboxSliceSpec) -> SandboxScope:
        return SandboxScope(
            label=spec.scope.id,
            locals=dict(spec.scope.state),
            visibility_rules=[
                SandboxVisibilityRule(journal_text=spec.scope.visibility.darkness_text)
            ],
        )

    def _compile_locations(
        self,
        *,
        graph: StoryGraph,
        scope: SandboxScope,
        spec: SandboxSliceSpec,
    ) -> dict[str, SandboxLocation]:
        locations: dict[str, SandboxLocation] = {}
        for label, location_spec in spec.locations.items():
            traits = set(location_spec.traits)
            descriptions = location_spec.descriptions
            location = SandboxLocation(
                label=label,
                location_name=location_spec.name,
                sandbox_scope=scope.get_label(),
                light="light" in traits,
                content=descriptions.lit or descriptions.look or descriptions.first or "",
                dark_text=descriptions.dark,
            )
            links: dict[str, str | SandboxExit] = {}
            for direction, exit_spec in location_spec.exits.items():
                compiled_exit = self._compile_exit(exit_spec)
                target_label = (
                    compiled_exit
                    if isinstance(compiled_exit, str)
                    else compiled_exit.target
                )
                if target_label is not None and target_label not in spec.locations:
                    raise ValueError(
                        f"Location {label!r} exit {direction!r} targets unknown "
                        f"sandbox location {target_label!r}"
                    )
                links[direction] = compiled_exit
            location.links = links
            graph.add(location)
            scope.add_child(location)
            locations[label] = location
        return locations

    def _compile_exit(self, exit_spec: str | SandboxExitSpec) -> str | SandboxExit:
        if isinstance(exit_spec, str):
            return exit_spec
        return exit_spec.as_sandbox_exit()

    def _require_location(
        self,
        locations: dict[str, SandboxLocation],
        location_label: str,
        *,
        source_kind: str,
        source_label: str,
        relation: str,
    ) -> SandboxLocation:
        if location_label not in locations:
            raise ValueError(
                f"{source_kind} {source_label!r} {relation} unknown sandbox "
                f"location {location_label!r}"
            )
        return locations[location_label]

    def _compile_assets(
        self,
        *,
        graph: StoryGraph,
        locations: dict[str, SandboxLocation],
        spec: SandboxSliceSpec,
    ) -> dict[str, Token]:
        assets: dict[str, Token] = {}
        for label, asset_spec in spec.assets.items():
            traits = set(asset_spec.traits)
            state = asset_spec.initial.state
            self._ensure_asset_type(label, asset_spec, traits, state)
            asset = Token[SandboxCompiledAssetType](token_from=label, label=label)
            graph.add(asset)
            self._require_location(
                locations,
                asset_spec.initial.location,
                source_kind="Asset",
                source_label=label,
                relation="starts in",
            ).add_asset(asset)
            assets[label] = asset
        return assets

    def _ensure_asset_type(
        self,
        label: str,
        spec: SandboxAssetSpec,
        traits: set[str],
        state: dict[str, Any],
    ) -> SandboxCompiledAssetType:
        expected = self._asset_type_values(spec=spec, traits=traits, state=state)
        existing = SandboxCompiledAssetType.get_instance(label)
        if existing is not None:
            current = {key: getattr(existing, key) for key in expected}
            if current != expected:
                raise ValueError(
                    f"Sandbox asset type {label!r} is already registered with "
                    "a different definition"
                )
            return existing
        return SandboxCompiledAssetType(
            label=label,
            **expected,
        )

    def _asset_type_values(
        self,
        *,
        spec: SandboxAssetSpec,
        traits: set[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "name": spec.name,
            "kind": spec.kind,
            "portable": "portable" in traits,
            "readable": "readable" in traits,
            "light_source": "provides_light" in traits,
            "lit": bool(state.get("lit", False)),
            "charge": state.get("charge"),
            "read_text": spec.descriptions.examine,
            "turn_on_text": (
                spec.descriptions.turn_on or f"Your {spec.name} is now on."
            ),
            "turn_off_text": (
                spec.descriptions.turn_off or f"Your {spec.name} is now off."
            ),
            "take_text": spec.descriptions.take,
            "drop_text": spec.descriptions.drop,
        }

    def _compile_fixtures(
        self,
        *,
        locations: dict[str, SandboxLocation],
        spec: SandboxSliceSpec,
    ) -> dict[str, SandboxLockable]:
        fixtures: dict[str, SandboxLockable] = {}
        for label, fixture_spec in spec.fixtures.items():
            traits = set(fixture_spec.traits)
            state = fixture_spec.initial.state
            fixture = SandboxLockable(
                label=label,
                name=fixture_spec.name,
                key=fixture_spec.key,
                locked=bool(state.get("locked", False)),
                open=bool(state.get("open", False)),
                openable="openable" in traits,
                unlock_text=(
                    fixture_spec.descriptions.unlock
                    or f"The key turns with a click. The {label} unlocks."
                ),
                open_text=fixture_spec.descriptions.open or f"The {label} opens.",
                close_text=fixture_spec.descriptions.close or f"The {label} closes.",
            )
            for location_label in fixture_spec.initial.locations:
                self._require_location(
                    locations,
                    location_label,
                    source_kind="Fixture",
                    source_label=label,
                    relation="is placed in",
                ).lockables.append(fixture)
            fixtures[label] = fixture
        return fixtures

    def _compile_mobs(
        self,
        *,
        graph: StoryGraph,
        scope: SandboxScope,
        locations: dict[str, SandboxLocation],
        spec: SandboxSliceSpec,
    ) -> dict[str, SandboxMob]:
        mobs: dict[str, SandboxMob] = {}
        for label, mob_spec in spec.mobs.items():
            initial = mob_spec.initial
            self._require_location(
                locations,
                initial.location,
                source_kind="Mob",
                source_label=label,
                relation="starts in",
            )
            mob = SandboxMob(
                label=label,
                name=mob_spec.name,
                kind=mob_spec.kind,
                traits=set(mob_spec.traits),
                location=initial.location,
                state=dict(initial.state),
                present_text=(
                    mob_spec.descriptions.present or mob_spec.descriptions.ambient
                ),
                nearby_text=mob_spec.descriptions.nearby,
                affordances=[
                    action_spec.as_affordance(action_label)
                    for action_label, action_spec
                    in mob_spec.contributes.affordances.items()
                ],
            )
            graph.add(mob)
            scope.add_child(mob)
            scope.mobs.append(mob)
            mobs[label] = mob
        return mobs
