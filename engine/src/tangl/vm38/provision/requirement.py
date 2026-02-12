from __future__ import annotations
from typing import Optional, Generic, TypeVar, Iterable
from uuid import UUID

from tangl.core38 import Entity, Registry, RegistryAware, Selector, Edge, EntityTemplate
from .provisioner import ProvisionPolicy, ProvisionOffer

RT = TypeVar('RT', bound=RegistryAware)


class Requirement(Selector, Generic[RT]):
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

    unsatisfiable: bool = None           # unknown
    unambiguously_resolved: bool = None  # unknown

    def satisfied_by(self, entity: RT) -> bool:
        return self.matches(entity)

    def _validate_satisfied_by(self, entity: RT) -> bool:
        if not self.satisfied_by(entity):
            raise ValueError(f'Requirement {self} not satisfied by {entity!r}')
        return True

    fallback_templ: Optional[EntityTemplate] = None
    # a requirement can satisfy itself if it carries an inline template
    # a cloner could take such an offer and combine it with an existing source


class HasRequirement(RegistryAware, Generic[RT]):
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

    requirement: Requirement[RT]

    # delegators

    @property
    def provider(self) -> Optional[RT]:
        if self.requirement.provider_id is not None:
            return self.registry.get(self.requirement.provider_id)

    def set_provider(self, provider: RT, _ctx=None) -> None:
        if (self.requirement._validate_satisfied_by(provider) and
                self.registry._validate_linkable(provider)):
            self.requirement.provider_id = provider.uid

    @provider.setter
    def provider(self, value: RT) -> None:
        self.set_provider(value)

    @property
    def satisfied(self):
        return self.requirement.satisfied

    def satisfied_by(self, entity: RT) -> bool:
        return self.requirement.satisfied_by(entity)


# Provides the carrier mechanism to map requirements into the graph-topology.
# Alternatively, they could be represented as control-Nodes that weld together
# ingoing and outgoing edges under a given name.

# These are dynamic edges that can provoke a topological update via an 'update' event
# on their requirement component.  Need to be careful to watch that.


class Dependency(Edge, HasRequirement, Generic[RT]):
    """
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

    # another layer of delegators

    # frontier is always the source/predecessor, resource is always the dest/successor
    # deps link from frontier to resources

    def set_provider(self, value: RT, _ctx=None) -> None:
        super().set_provider(value, _ctx=_ctx)
        super().set_successor(value, _ctx=_ctx)

    def set_successor(self, value: RT, _ctx=None) -> None:
        self.set_provider(value, _ctx=_ctx)


class Affordance(Edge, HasRequirement, Generic[RT]):
    """
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

    # frontier is always the source/predecessor, resource is always the dest/successor
    # affordances provide resources to frontier

    def set_provider(self, value: RT, _ctx=None) -> None:
        super().set_provider(value, _ctx=_ctx)
        super().set_predecessor(value, _ctx=_ctx)

    def set_predecessor(self, value: RT, _ctx=None) -> None:
        self.set_provider(value, _ctx=_ctx)
