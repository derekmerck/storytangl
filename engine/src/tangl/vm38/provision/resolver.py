from dataclasses import dataclass
from typing import Iterable, Optional, TypeAlias, Union, Self

from tangl.core38 import EntityGroup, EntityTemplate, resolve_ctx, Node, Selector
from ..dispatch import on_provision
from .provisioner import ProvisionOffer, FindProvisioner, TemplateProvisioner, FallbackProvisioner, ProvisionPolicy
from .requirement import Requirement, PT, Dependency

# Not necessarily a hierarchical template group, just an iterator of
# templates at the same scope-distance
TemplateGroup: TypeAlias = Union[EntityGroup, EntityTemplate]


@dataclass
class Resolver:

    # order of the groups indicates 'distance' from the requirement carrier,
    # so resolver can be created per frontier node and then re-used multiple
    # times to resolve its requirements.
    # Pushes entire 'scope' discussion into however the frontier wants to define
    # it and provides a working default with a single group, single distance.

    entity_groups: Iterable[EntityGroup] = ()       # existing sources by scope dist
    template_groups: Iterable[TemplateGroup] = ()   # template sources by scope dist

    @classmethod
    def from_ctx(cls, ctx) -> Self:
        return cls(entity_groups=ctx.get_entity_groups(),
                   template_groups=ctx.get_template_groups())

    def gather_offers(self, requirement: Requirement[PT], *, _ctx=None) -> list[ProvisionOffer]:

        # todo: need an AffordanceProvider that can satisfy requirements with
        #       an already linked affordance edge on this node

        offers: list[ProvisionOffer] = []

        # If there are more than 20 groups, the distance-based priorities will slip
        # from the NORMAL tier to LATE, maybe just collapse everything after a few scopes
        # out but not global into "far away" tier and then include globals as the last group.
        for i, entity_group in enumerate(self.entity_groups):
            offers.extend(FindProvisioner(values=entity_group, distance=i).get_dependency_offers(requirement))

        for i, template_group in enumerate(self.template_groups):
            offers.extend(TemplateProvisioner(templates=template_group, distance=i).get_dependency_offers(requirement))

        offers.extend(FallbackProvisioner.get_dependency_offers(requirement))

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # give dispatch a chance to modify the offers
            from tangl.vm38.dispatch import do_resolve
            offers = do_resolve(requirement=requirement, offers=offers, ctx=_ctx)

        # force always passes, otherwise use flag.__contains__
        offers = list(filter(
            lambda offer: offer.policy is ProvisionPolicy.FORCE or
                          offer.policy in requirement.provision_policy, offers))
        offers.sort(key=lambda v: v.sort_key())
        return offers

    def resolve_requirement(self, requirement: Requirement[PT], *, _ctx=None) -> Optional[PT]:
        # updates requirement in place, returns provider to allow linking at dependency level

        offers = self.gather_offers(requirement, _ctx=_ctx)

        if len(offers) == 0:
            # No valid offers available
            requirement.unsatisfiable = True
            return None
        else:
            requirement.unsatisfiable = False

        if len(offers) == 1:
            # Unambiguous offer available
            requirement.unambiguously_resolved = True
        else:
            requirement.unambiguously_resolved = False

        # todo: should we return the selected offer and let caller invoke it later
        #       and/or stash it somewhere for audit?
        return offers[0].callback(_ctx=_ctx)

    def resolve_dependency(self, dependency: Dependency[PT], *, _ctx=None) -> bool:

        provider = self.resolve_requirement(requirement=dependency.requirement, _ctx=_ctx)
        if provider is not None:
            dependency.set_provider(provider, _ctx=_ctx)
            return True
        return False

    def resolve_frontier_node(self, node: Node, _ctx=None) -> bool:

        # todo: need to link any available affordances first, then use an affordance
        #       provider to provide very cheap provision offers?

        # Note this is not unsatisfied deps, it's anyone without a provider
        # satisfied could mean not a hard req
        open_deps = node.edges_out(Selector(has_kind=Dependency, provider=None))
        for dep in open_deps:
            self.resolve_dependency(dep, _ctx=_ctx)

        # Find unsat blockers with no provider and a hard-requirement
        unsatisfied_deps = node.edges_out(Selector(has_kind=Dependency, satisfied=False))
        if next(unsatisfied_deps, None) is not None:
            return False

        return True

# Register the resolution process with dispatch so it will be invoked from the phase bus
@on_provision
def provision_node(caller: Node, *, ctx):
    Resolver.from_ctx(ctx).resolve_frontier_node(node=caller, _ctx=ctx)
