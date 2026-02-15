from __future__ import annotations
from typing import Optional, Generic, TypeVar, Iterable
from uuid import UUID

from tangl.core38 import Entity, Registry, RegistryAware, Selector, Edge, Node, EntityTemplate
from .provisioner import ProvisionPolicy, ProvisionOffer

PT = TypeVar('PT', bound=RegistryAware)  # 'ProviderType'

class Requirement(Selector, Generic[PT]):
    """
    Example:
        >>> e = Entity(label='foo')
        >>> req = Requirement.from_identifier('foo')
        >>> req.satisfied
        False
        >>> req.satisfied_by(e)
        True
        >>> req.provider_id = e.uid
        >>> req.satisfied
        True
        >>> req = Requirement(hard_requirement=False)
        >>> req.satisfied
        True
    """

    # Not an entity, a serializable collection of traits that can be
    # used as a component on an entity with a requirement.

    provision_policy: ProvisionPolicy = ProvisionPolicy.ANY
    provider_id: Optional[UUID] = None
    hard_requirement: bool = True

    # todo: validate not none selector

    @property
    def satisfied(self):
        return self.provider_id is not None or not self.hard_requirement

    unsatisfiable: Optional[bool] = None           # unknown
    unambiguously_resolved: Optional[bool] = None  # unknown

    def satisfied_by(self, entity: PT) -> bool:
        return self.matches(entity)

    def _validate_satisfied_by(self, entity: PT) -> bool:
        if not self.satisfied_by(entity):
            raise ValueError(f'Requirement {self} not satisfied by {entity!r}')
        return True

    fallback_templ: Optional[EntityTemplate] = None
    # a requirement can satisfy itself if it carries an inline template
    # a cloner could take such an offer and combine it with an existing source


class HasRequirement(RegistryAware, Generic[PT]):
    """
    Example:
        >>> reg = Registry()
        >>> r = HasRequirement(requirement={'has_identifier': 'foo'}); reg.add(r)
        >>> r.satisfied
        False
        >>> e = RegistryAware(label='foo'); reg.add(e)
        >>> r.satisfied_by(e)
        True
        >>> r.provider = e
        >>> r.satisfied
        True
        >>> r.provider
        <RegistryAware:foo>
        >>> f = RegistryAware(label='bar'); reg.add(f)
        >>> r.satisfied_by(f)
        False
        >>> try:
        ...     r.provider = f
        ... except ValueError as e:
        ...     print(e)
        Requirement ... not satisfied by <RegistryAware:bar>

    """
    # typically an entity will have only one requirement to avoid bookkeeping confusion.
    # nodes may have multiple dependency edges, for example, but each dependency has
    # a single requirement.

    requirement: Requirement[PT]

    # delegators

    @property
    def provider(self) -> Optional[PT]:
        if self.requirement.provider_id is not None:
            return self.registry.get(self.requirement.provider_id)

    def set_provider(self, provider: PT, _ctx=None) -> None:
        if (self.requirement._validate_satisfied_by(provider) and
                self.registry._validate_linkable(provider)):
            self.requirement.provider_id = provider.uid

    @provider.setter
    def provider(self, value: PT) -> None:
        self.set_provider(value)

    @property
    def satisfied(self):
        return self.requirement.satisfied

    def satisfied_by(self, entity: PT) -> bool:
        return self.requirement.satisfied_by(entity)


# Provides the carrier mechanism to map requirements into the graph-topology.
# Alternatively, they could be represented as control-Nodes that weld together
# ingoing and outgoing edges under a given name.

# These are dynamic edges that can provoke a topological update via an 'update' event
# on their requirement component.  Need to be careful to watch that.


class Dependency(Edge, HasRequirement[PT], Generic[PT]):
    """
    The frontier node is _always_ the source/predecessor, resource is _always_ the
    dest/successor; dependenciess link from frontier to resources.

    Deps are 'pull' resources.

    Example:
        >>> reg = Registry()
        >>> r = Dependency(requirement={'has_identifier': 'foo'}); reg.add(r)
        >>> r.satisfied
        False
        >>> e = RegistryAware(label='foo'); reg.add(e)
        >>> r.successor = e
        >>> r.satisfied
        True
        >>> r.provider
        <RegistryAware:foo>
        >>> r.successor
        <RegistryAware:foo>

    """

    # another layer of delegators, the important thing here is that the 'on_link'
    # hook gets triggered when the provider is set.  Could do that by syncing the
    # provider and successor, or by ignoring successor_id and rewiring set_provider to
    # call the on_link hook.


    def set_provider(self, value: PT, _ctx=None) -> None:
        # could just leave successor_id None and defer to provider-id in all cases to
        # entirely avoid syncing concern.  might also make the end-type more clear as
        # the expected provider type.
        super().set_provider(value, _ctx=_ctx)
        super().set_successor(value, _ctx=_ctx)

    def set_successor(self, value: PT, _ctx=None) -> None:
        self.set_provider(value, _ctx=_ctx)


class Affordance(Edge, HasRequirement[PT], Generic[PT]):
    """
    Frontier node is _always_ the source/predecessor, resource is always the
    dest/successor; affordances provide resources to frontier.

    Affordances are 'push' resources.

    Example:
            >>> reg = Registry()
            >>> r = Affordance(requirement={'has_identifier': 'foo'}); reg.add(r)
            >>> r.satisfied
            False
            >>> e = RegistryAware(label='foo'); reg.add(e)
            >>> r.predecessor = e
            >>> r.satisfied
            True
            >>> r.provider
            <RegistryAware:foo>
            >>> r.predecessor
            <RegistryAware:foo>
    """
    # another layer of delegators

    def set_provider(self, value: PT, _ctx=None) -> None:
        super().set_provider(value, _ctx=_ctx)
        super().set_predecessor(value, _ctx=_ctx)

    def set_predecessor(self, value: PT, _ctx=None) -> None:
        self.set_provider(value, _ctx=_ctx)
