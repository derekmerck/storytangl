from dataclasses import dataclass
from typing import Iterable, Optional, TypeAlias, Union

from tangl.core38 import EntityGroup, EntityTemplate, resolve_ctx
from .provisioner import ProvisionOffer, FindProvisioner, TemplateProvisioner, FallbackProvisioner
from .requirement import Requirement

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

    entity_groups: Iterable[EntityGroup] = None       # existing sources by scope dist
    template_groups: Iterable[TemplateGroup] = None   # template sources by scope dist

    def gather_offers(self, requirement: Requirement, _ctx) -> list[ProvisionOffer]:

        offers: list[ProvisionOffer] = []

        # If there are more than 20 groups, the priorities will slip from NORMAL
        # to LATE
        for i, entity_group in enumerate(self.entity_groups):
            offers.extend(FindProvisioner(values=entity_group, distance=i).get_dependency_offers(requirement))

        for i, template_group in enumerate(self.template_groups):
            offers.extend(TemplateProvisioner(templates=template_group, distance=i).get_dependency_offers(requirement))

        offers.extend(FallbackProvisioner.get_dependency_offers(requirement))

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            from tangl.vm38.dispatch import do_resolve
            offers = do_resolve(offers, _ctx)

        offers = filter(lambda offer: offer.policy in requirement.provision_policy, offers)
        offers.sort(key=lambda v: v.sort_key())
        return offers

    def resolve_requirement(self, requirement: Requirement, _ctx=None) -> Optional[ProvisionOffer]:

        offers = self.gather_offers(requirement, _ctx)

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

        return offers[0].callback()
