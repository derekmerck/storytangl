"""Opt-in packed portraits: UPDATE admits resources; JOURNAL only selects them."""

from __future__ import annotations

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from tangl.core import BehaviorRegistry, DispatchLayer, EntityTemplate, Node, Priority, Record
from tangl.core.bases import Unstructurable
from tangl.journal.fragments import AttributedFragment, MediaFragment
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.media_provisioning import MediaInventoryProvisioner
from tangl.media.media_resource.media_resource_inv_tag import is_materialized_media_file
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media.story_media import get_story_resource_manager
from tangl.media.system_media import get_system_resource_manager
from tangl.story import Block, Role, Setting, StoryGraph
from tangl.vm import Resolver
from tangl.vm.runtime.frame import PhaseCtx

Nonempty = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class PortraitLook(Unstructurable, extra="forbid"):
    """One packed look; its optional base is the neutral portrait."""

    base: Nonempty | None = None
    expressions: dict[Nonempty, Nonempty] = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )


class PackedPortraits(Unstructurable, extra="forbid"):
    """World-authored looks and exact full-attitude to expression mapping."""

    looks: dict[Nonempty, PortraitLook] = Field(
        default_factory=dict, json_schema_extra={"include": True, "unstructurable": True},
    )
    default_look: Nonempty | None = None
    attitudes: dict[Nonempty, Nonempty] = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )
    scope: Literal["world", "story", "sys"] = "world"

    @model_validator(mode="after")
    def _declared_default(self) -> Self:
        if self.default_look is not None and self.default_look not in self.looks:
            raise ValueError(f"default_look {self.default_look!r} is not declared in looks")
        return self


class HasPortraits(Node):
    """Optional graph concept with pure request-time look nomination.

    Compose with Actor/Location or another Node. Worlds override
    :meth:`nominate_portrait_look` using the current scoped context, returning a
    declared look key or None. No Presence, generation, or nomination history.
    """

    portraits: PackedPortraits = Field(
        default_factory=PackedPortraits,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    portrait_dependency_ids: dict[str, UUID] = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )

    def nominate_portrait_look(self, *, ctx: PhaseCtx, attitude: str | None) -> str | None:
        """Return a declared look key without changing concept or graph state."""
        return self.portraits.default_look

    def dialog_portrait(self, *, ctx: PhaseCtx, attitude: str | None) -> MediaRIT | None:
        look_key = self.nominate_portrait_look(ctx=ctx, attitude=attitude)
        if look_key is None:
            return None
        if look_key not in self.portraits.looks:
            raise ValueError(f"{self.get_label()}: nominated undeclared portrait look {look_key!r}")
        look = self.portraits.looks[look_key]
        expression = self.portraits.attitudes.get(attitude) if attitude is not None else None
        variant = look.expressions.get(expression) if expression not in (None, "neutral") else None
        for reference in (variant, look.base):
            if reference is None:
                continue
            dependency_id = self.portrait_dependency_ids.get(reference)
            dependency = ctx.graph.get(dependency_id) if dependency_id is not None else None
            if isinstance(dependency, MediaDep) and dependency.render_ready:
                resource = dependency.provider
                if resource.data is not None or (
                    resource.path is not None and is_materialized_media_file(resource.path)
                ):
                    return resource
        return None


portrait_dispatch = BehaviorRegistry(
    label="prose.portraits", default_dispatch_layer=DispatchLayer.AUTHOR,
)


def _portrait_resources(scope: str, *, ctx: PhaseCtx) -> ResourceManager | None:
    """Use the existing manager owned by the declared inventory scope."""
    if scope == "sys":
        return get_system_resource_manager()
    if not isinstance(ctx.graph, StoryGraph):
        return None
    if scope == "story":
        if ctx.graph.story_resources is None:
            ctx.graph.story_resources = get_story_resource_manager(ctx.graph.story_id, create=False)
        return ctx.graph.story_resources
    world = ctx.graph.world
    return world.resources if world is not None else None


@portrait_dispatch.register(task="apply_update", priority=Priority.LAST)
def prepare_portraits(*, caller: Block, ctx: PhaseCtx, **_kwargs: object) -> None:
    """Prepare finite resources of currently scoped providers, including lazy ones."""
    if not isinstance(caller, Block):
        return
    providers: dict[UUID, HasPortraits] = {}
    for value in ctx.get_ns(caller).values():
        provider = value.provider if isinstance(value, (Role, Setting)) else value
        if isinstance(provider, HasPortraits):
            providers[provider.uid] = provider
    for provider in providers.values():
        references = {
            reference for look in provider.portraits.looks.values()
            for reference in (look.base, *look.expressions.values()) if reference is not None
        }
        provider_ctx = ctx.derive(cursor_id=provider.uid)
        resolver = Resolver.from_ctx(provider_ctx)
        resources = _portrait_resources(provider.portraits.scope, ctx=provider_ctx)
        for reference in sorted(references):
            dependency_id = provider.portrait_dependency_ids.get(reference)
            if dependency_id is None:
                dependency = EntityTemplate.from_data({
                    "kind": MediaDep, "predecessor_id": provider.uid,
                    "media_id": reference, "scope": provider.portraits.scope,
                }).materialize(registry=ctx.graph)
                provider.portrait_dependency_ids[reference] = dependency.uid
            else:
                dependency = ctx.graph.get(dependency_id)
            if dependency.provider is None:
                if resources is not None:
                    MediaInventoryProvisioner.bind_named(
                        dependency, media_id=reference, resources=resources, ctx=provider_ctx,
                    )
                if dependency.provider is None:
                    resolver.resolve_dependency(dependency, _ctx=provider_ctx)


@portrait_dispatch.register(task="compose_journal", priority=Priority.LAST)
def compose_portraits(*, fragments: list[Record], ctx: PhaseCtx, **_kwargs: object) -> list[Record]:
    """Add ordinary following media without changing explicit block/base staging."""
    output: list[Record] = []
    for fragment in fragments:
        output.append(fragment)
        if not isinstance(fragment, AttributedFragment):
            continue
        metadata = fragment.model_extra or {}
        speaker_id = metadata.get("speaker_id")
        if speaker_id is None:
            continue
        provider = ctx.graph.get(UUID(str(speaker_id)))
        if not isinstance(provider, HasPortraits):
            continue
        resource = provider.dialog_portrait(ctx=ctx, attitude=metadata.get("speaker_attitude"))
        if resource is not None:
            output.append(MediaFragment(
                content=resource, content_format="rit", content_type=resource.data_type,
                media_role="dialog_im", scope=provider.portraits.scope,
                speaker_id=speaker_id,
                source_id=fragment.source_id, origin_id=fragment.origin_id, step=ctx.step,
            ))
    return output


def get_authorities() -> list[BehaviorRegistry]:
    """World-domain adoption through the ordinary authority chain."""
    return [portrait_dispatch]
