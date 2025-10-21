# tangl/core/domain/affiliate.py
from typing import ClassVar, Type

from tangl.type_hints import StringMap
from tangl.core import Entity, Registry, Singleton
from tangl.core.entity import Selectable, MatchPredicate
from .domain import global_domain, Domain


class AffiliateDomain(Selectable, Domain):
    """
    AffiliateDomains are opt-in. An Entity can self-subscribe to an affiliate domain
    by various supported mechanisms:

    - including a domain:x selector tag
    - belonging to a selector class
    """

    # todo: we actually want to freeze the vars dict for affiliates and the handlers once they are built;
    #       we don't want to accidentally mutate anything global through graph handlers

    # default selection criteria is assembled from instance and class vars
    selector_prefix: ClassVar[str] = "domain"
    selector_type: ClassVar[Type[Entity]] = Entity

    @property
    def selector(self) -> MatchPredicate:
        # todo: legacy accessor for selector, i.e., tester predicate
        return self.get_selection_criteria().get('predicate', lambda _: False)

    def get_selection_criteria(self) -> StringMap:
        criteria = super().get_selection_criteria()  # returns a copy
        if self.selector_prefix is not None:
            selector_tag = f'{self.selector_prefix}:{self.label}'
            if criteria.get('has_tags') is None:
                criteria['has_tags'] = {selector_tag}
            else:
                # maybe want to handle case that it is a list?
                criteria['has_tags'].add(selector_tag)
        if self.selector_type is not None:
            criteria.setdefault('is_instance', self.selector_type)
        return criteria

AffiliateRegistry = Registry[AffiliateDomain]


class SingletonDomain(Singleton, AffiliateDomain):
    # ONLY use singleton domains in anything that needs to be serialized
    ...
