from dataclasses import dataclass
from typing import Any, Iterable, Optional, Protocol, TypeAlias, Union, Self, runtime_checkable
from uuid import UUID

from tangl.core38 import (
    Edge,
    EntityGroup,
    EntityTemplate,
    Priority,
    RegistryAware,
    resolve_ctx,
    Node,
    Selector,
)
from ..dispatch import on_provision
from .provisioner import (
    ProvisionOffer,
    FindProvisioner,
    TemplateProvisioner,
    InlineTemplateProvisioner,
    FallbackProvisioner,
    ProvisionPolicy,
)
from .matching import annotate_offer_specificity, summarize_offer
from .requirement import Requirement, PT, Dependency, Affordance

# Not necessarily a hierarchical template group, just an iterator of
# templates at the same scope-distance
TemplateGroup: TypeAlias = Union[EntityGroup, EntityTemplate]


@runtime_checkable
class ResolverCtx(Protocol):
    def get_location_entity_groups(self) -> Iterable[Iterable[Any]]: ...
    def get_template_scope_groups(self) -> Iterable[TemplateGroup]: ...
    def get_entity_groups(self) -> Iterable[EntityGroup]: ...
    def get_template_groups(self) -> Iterable[TemplateGroup]: ...


@dataclass
class Resolver:

    # order of the groups indicates 'distance' from the requirement carrier,
    # so resolver can be created per frontier node and then re-used multiple
    # times to resolve its requirements.
    # Pushes entire 'scope' discussion into however the frontier wants to define
    # it and provides a working default with a single group, single distance.

    location_entity_groups: Iterable[Iterable[Any]] = ()
    template_scope_groups: Iterable[TemplateGroup] = ()
    # Legacy aliases kept for backward compatibility.
    entity_groups: Iterable[Iterable[Any]] = ()
    template_groups: Iterable[TemplateGroup] = ()

    def __post_init__(self) -> None:
        if not self.location_entity_groups and self.entity_groups:
            self.location_entity_groups = self.entity_groups
        if not self.template_scope_groups and self.template_groups:
            self.template_scope_groups = self.template_groups

    @staticmethod
    def _ctx_location_entity_groups(ctx) -> Iterable[Iterable[Any]]:
        getter = getattr(ctx, "get_location_entity_groups", None)
        if callable(getter):
            return getter()
        getter = getattr(ctx, "get_entity_groups", None)
        if callable(getter):
            return getter()
        raise TypeError(
            "Resolver context must provide get_location_entity_groups() or get_entity_groups()"
        )

    @staticmethod
    def _ctx_template_scope_groups(ctx) -> Iterable[TemplateGroup]:
        getter = getattr(ctx, "get_template_scope_groups", None)
        if callable(getter):
            return getter()
        getter = getattr(ctx, "get_template_groups", None)
        if callable(getter):
            return getter()
        raise TypeError(
            "Resolver context must provide get_template_scope_groups() or get_template_groups()"
        )

    @classmethod
    def from_ctx(cls, ctx: ResolverCtx) -> Self:
        return cls(
            location_entity_groups=cls._ctx_location_entity_groups(ctx),
            template_scope_groups=cls._ctx_template_scope_groups(ctx),
        )

    def gather_offers(
        self,
        requirement: Requirement[PT],
        *,
        force: bool = False,
        preferred_offers: Iterable[ProvisionOffer] = (),
        _ctx=None,
    ) -> list[ProvisionOffer]:
        offers: list[ProvisionOffer] = list(preferred_offers or [])

        # If there are more than 20 groups, the distance-based priorities will slip
        # from the NORMAL tier to LATE, maybe just collapse everything after a few scopes
        # out but not global into "far away" tier and then include globals as the last group.
        for i, entity_group in enumerate(self.location_entity_groups):
            offers.extend(FindProvisioner(values=entity_group, distance=i).get_dependency_offers(requirement))

        for i, template_group in enumerate(self.template_scope_groups):
            offers.extend(TemplateProvisioner(templates=template_group, distance=i).get_dependency_offers(requirement))

        offers.extend(InlineTemplateProvisioner.get_dependency_offers(requirement))

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # give dispatch a chance to modify the offers
            from tangl.vm38.dispatch import do_resolve
            try:
                resolved_offers = do_resolve(requirement=requirement, offers=offers, ctx=_ctx)
            except TypeError as exc:
                requirement.resolution_reason = "override_invalid"
                requirement.resolution_meta = {"error": str(exc)}
            else:
                if resolved_offers is not None:
                    offers = resolved_offers

        offers = [annotate_offer_specificity(requirement, offer) for offer in offers]

        def _allowed(offer: ProvisionOffer) -> bool:
            if offer.policy & ProvisionPolicy.FORCE:
                return force
            return bool(offer.policy & requirement.provision_policy)

        offers = [offer for offer in offers if _allowed(offer)]

        # Judgment call: synthetic fallback is an emergency path only.
        # It is offered only when force=True and no other provider yielded a valid offer.
        if force and not offers:
            offers.extend(FallbackProvisioner.get_dependency_offers(requirement))

        offers.sort(key=lambda v: v.sort_key())
        return offers

    @staticmethod
    def _iter_local_affordance_providers(frontier: Node | None) -> Iterable[RegistryAware]:
        """Yield unique providers from affordance edges already linked to ``frontier``."""
        if frontier is None:
            return

        seen_ids: set[UUID] = set()
        for affordance in frontier.edges(Selector(has_kind=Affordance)):
            provider = affordance.provider
            if provider is None:
                predecessor = affordance.predecessor
                successor = affordance.successor
                if predecessor is frontier:
                    provider = successor
                elif successor is frontier:
                    provider = predecessor
                else:
                    provider = predecessor or successor

            if not isinstance(provider, RegistryAware):
                continue
            if provider.uid in seen_ids:
                continue
            seen_ids.add(provider.uid)
            yield provider

    def _linked_affordance_offers(
        self,
        *,
        requirement: Requirement[PT],
        frontier: Node | None,
    ) -> list[ProvisionOffer]:
        """Build EXISTING offers from already-linked local affordance providers."""
        offers: list[ProvisionOffer] = []
        for provider in self._iter_local_affordance_providers(frontier):
            try:
                if not requirement.satisfied_by(provider):
                    continue
            except Exception:
                continue
            offers.append(
                ProvisionOffer(
                    origin_id="LinkedAffordance",
                    policy=ProvisionPolicy.EXISTING,
                    priority=Priority.EARLY,
                    distance_from_caller=0,
                    candidate=provider,
                    callback=lambda *_, _provider=provider, **__: _provider,
                )
            )
        return offers

    def resolve_requirement(
        self,
        requirement: Requirement[PT],
        *,
        force: bool = False,
        preferred_offers: Iterable[ProvisionOffer] = (),
        _ctx=None,
    ) -> Optional[PT]:
        # updates requirement in place, returns provider to allow linking at dependency level

        offers = self.gather_offers(
            requirement,
            force=force,
            preferred_offers=preferred_offers,
            _ctx=_ctx,
        )

        if len(offers) == 0:
            # No valid offers available
            requirement.unsatisfiable = True
            requirement.unambiguously_resolved = None
            requirement.selected_offer_policy = None
            requirement.resolved_step = None
            requirement.resolved_cursor_id = None
            if requirement.resolution_reason is None:
                requirement.resolution_reason = "no_offers"
            requirement.resolution_meta = requirement.resolution_meta or {
                "alternatives": [],
            }
            return None
        else:
            requirement.unsatisfiable = False

        if len(offers) == 1:
            # Unambiguous offer available
            requirement.unambiguously_resolved = True
        else:
            requirement.unambiguously_resolved = False

        selected_offer = offers[0]
        requirement.selected_offer_policy = selected_offer.policy
        requirement.resolution_reason = "resolved"
        requirement.resolution_meta = {
            "selected": summarize_offer(selected_offer),
            "alternatives": [summarize_offer(offer) for offer in offers[:5]],
        }

        # todo: should we return the selected offer and let caller invoke it later
        #       and/or stash it somewhere for audit?
        provider = selected_offer.callback(_ctx=_ctx)
        if provider is None:
            requirement.unsatisfiable = True
            requirement.resolution_reason = "provider_none"
            return None
        return provider

    def resolve_dependency(self, dependency: Dependency[PT], *, force: bool = False, _ctx=None) -> bool:
        preferred_offers = self._linked_affordance_offers(
            requirement=dependency.requirement,
            frontier=dependency.predecessor,
        )

        provider = self.resolve_requirement(
            requirement=dependency.requirement,
            force=force,
            preferred_offers=preferred_offers,
            _ctx=_ctx,
        )
        if provider is not None:
            if force and dependency.requirement.selected_offer_policy is ProvisionPolicy.FORCE:
                # Judgment call: force fallback is an emergency "shape only" provider.
                # We bypass requirement predicate validation here intentionally.
                if not isinstance(provider, RegistryAware):
                    raise TypeError(
                        "Force fallback provider must be RegistryAware for dependency linkage"
                    )
                if provider.registry is not dependency.registry:
                    dependency.registry.add(provider, _ctx=_ctx)
                dependency.requirement.provider_id = provider.uid
                dependency.requirement.resolved_step = (
                    getattr(_ctx, "step", None)
                    if isinstance(getattr(_ctx, "step", None), int)
                    else None
                )
                cursor_id = getattr(_ctx, "cursor_id", None)
                if cursor_id is None:
                    cursor = getattr(_ctx, "cursor", None)
                    cursor_id = getattr(cursor, "uid", None)
                dependency.requirement.resolved_cursor_id = (
                    cursor_id if isinstance(cursor_id, UUID) else None
                )
                dependency.requirement.resolution_reason = "forced_fallback_resolved"
                Edge.set_successor(dependency, provider, _ctx=_ctx)
                return True
            try:
                dependency.set_provider(provider, _ctx=_ctx)
            except ValueError:
                dependency.requirement.resolution_reason = "provider_rejected"
                return False
            if dependency.requirement.resolution_reason is None:
                dependency.requirement.resolution_reason = "resolved"
            return True
        return False

    def resolve_frontier_node(self, node: Node, *, force: bool = False, _ctx=None) -> bool:
        # Note this is not unsatisfied deps, it's anyone without a provider
        # satisfied could mean not a hard req
        open_deps = node.edges_out(Selector(has_kind=Dependency, provider=None))
        for dep in open_deps:
            self.resolve_dependency(dep, force=force, _ctx=_ctx)

        # Find unsat blockers with no provider and a hard-requirement
        unsatisfied_deps = node.edges_out(Selector(has_kind=Dependency, satisfied=False))
        if next(unsatisfied_deps, None) is not None:
            return False

        # Containers must have a reachable sink from their source.
        from ..traversable import TraversableNode

        if isinstance(node, TraversableNode) and node.is_container:
            source = node.source
            sink = node.sink
            if source is None or sink is None:
                return False
            ns = None
            if _ctx is not None and hasattr(_ctx, "get_ns"):
                ns = dict(_ctx.get_ns(source))
            if not node.has_forward_progress(source, ns=ns):
                return False

        return True

# Register the resolution process with dispatch so it will be invoked from the phase bus
@on_provision
def provision_node(caller: Node, *, ctx, force: bool = False):
    Resolver.from_ctx(ctx).resolve_frontier_node(node=caller, force=force, _ctx=ctx)
