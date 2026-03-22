"""Frontier constraint edges for the vm provisioning pipeline.

Defines the requirement data model and the topology carriers that embed
requirements into the runtime graph.
"""

from __future__ import annotations
from typing import Any, Optional, Generic, Iterable, TypeVar
from uuid import UUID

from pydantic import Field

from tangl.core import Entity, Registry, RegistryAware, Selector, Edge, Node, EntityTemplate
from ..ctx import VmPhaseCtx
from .provisioner import ProvisionPolicy

PT = TypeVar('PT', bound=RegistryAware)  # 'ProviderType'

class Requirement(Selector, Generic[PT]):
    """Requirement(has_kind: type | None, has_identifier: str | None)

    Unsatisfied resource contract carried by a frontier edge.

    Why
    ----
    Requirements separate the shape of what is needed from the graph structure
    that carries that need. This lets the resolver reason about candidates,
    policy, and diagnostics before mutating runtime topology.

    Key Features
    ------------
    * Extends :class:`~tangl.core.Selector` so requirement matching reuses the
      engine's normal selection semantics.
    * Tracks satisfaction, selected policy, and resolution metadata for replay
      and diagnostics.
    * Supports soft requirements and deferred UPDATE or CLONE formulas.

    API
    ---
    - :attr:`satisfied` reports whether the requirement is currently fulfilled.
    - :meth:`satisfied_by` evaluates a candidate provider.
    - :meth:`from_identifier` builds a simple identifier-driven requirement.

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
    selected_offer_policy: Optional[ProvisionPolicy] = None
    resolved_step: Optional[int] = None
    resolved_cursor_id: Optional[UUID] = None
    resolution_reason: Optional[str] = None
    resolution_meta: Optional[dict[str, Any]] = None

    def _matches_identifier(self, entity: PT) -> bool:
        extra = self.__pydantic_extra__ or {}
        identifier = extra.get("has_identifier")
        if not isinstance(identifier, str) or not identifier:
            return True

        has_identifier = getattr(entity, "has_identifier", None)
        if callable(has_identifier):
            try:
                if bool(has_identifier(identifier)):
                    return True
            except (TypeError, ValueError, AttributeError):
                pass

        if "." in identifier:
            path = getattr(entity, "path", None)
            if isinstance(path, str) and path == identifier:
                return True

        return False

    def satisfied_by(self, entity: PT) -> bool:
        if not self._matches_identifier(entity):
            return False

        criteria = dict(self.__pydantic_extra__ or {})
        for key in ("has_identifier", "authored_path", "is_qualified", "is_absolute"):
            criteria.pop(key, None)
        return Selector(predicate=self.predicate, **criteria).matches(entity)

    def _validate_satisfied_by(self, entity: PT) -> bool:
        if not self.satisfied_by(entity):
            raise ValueError(f'Requirement {self} not satisfied by {entity!r}')
        return True

    fallback_templ: Optional[EntityTemplate] = None
    # a requirement can satisfy itself if it carries an inline template
    # a cloner could take such an offer and combine it with an existing source

    # Authoring-path metadata used by qualified/unqualified policy forks.
    authored_path: str | None = None
    is_qualified: bool = False
    is_absolute: bool = False

    # Optional two-part formula for late synthesized UPDATE/CLONE offers.
    # These are typed fields (not selector extras), so they do not participate
    # in provider matching criteria.
    reference_selector: Optional[Selector] = None
    update_template_selector: Optional[Selector] = None
    media_spec: Any = None
    media_ref_id: Optional[UUID] = None
    media_basename: Optional[str] = None


def stamp_requirement_resolution(
    requirement: Requirement[Any],
    *,
    _ctx: VmPhaseCtx | None = None,
) -> None:
    """Write shared step/cursor resolution metadata from a typed runtime context."""
    if _ctx is None:
        requirement.resolved_step = None
        requirement.resolved_cursor_id = None
        return

    step = _ctx.step
    requirement.resolved_step = step if isinstance(step, int) else None

    cursor_id = _ctx.cursor_id
    requirement.resolved_cursor_id = cursor_id if isinstance(cursor_id, UUID) else None


class HasRequirement(RegistryAware, Generic[PT]):
    """HasRequirement(requirement: Requirement[PT])

    Mixin that makes a registry-aware carrier expose one embedded requirement.

    Why
    ----
    Resolver logic needs a uniform way to read satisfaction state, retrieve the
    resolved provider, and write resolution metadata back to the carrier edge.

    Key Features
    ------------
    * Centralizes provider bookkeeping on the embedded
      :class:`Requirement`.
    * Mirrors satisfaction and resolution metadata through simple properties.
    * Validates provider compatibility before storing the resolved provider id.

    API
    ---
    - :attr:`provider` and :meth:`set_provider` synchronize the embedded
      requirement with registry linkage.
    - :attr:`satisfied` and :meth:`satisfied_by` delegate to the embedded
      requirement.

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
            stamp_requirement_resolution(self.requirement, _ctx=_ctx)

    @provider.setter
    def provider(self, value: PT) -> None:
        self.set_provider(value)

    @property
    def satisfied(self):
        return self.requirement.satisfied

    @property
    def resolution_reason(self) -> Optional[str]:
        return self.requirement.resolution_reason

    @property
    def resolution_meta(self) -> Optional[dict[str, Any]]:
        return self.requirement.resolution_meta

    def satisfied_by(self, entity: PT) -> bool:
        return self.requirement.satisfied_by(entity)


# Provides the carrier mechanism to map requirements into the graph-topology.
# Alternatively, they could be represented as control-Nodes that weld together
# ingoing and outgoing edges under a given name.

# These are dynamic edges that can provoke a topological update via an 'update' event
# on their requirement component.  Need to be careful to watch that.


class Dependency(Edge, HasRequirement[PT], Generic[PT]):
    """Dependency(predecessor_id: UUID | None = None, requirement: Requirement[PT])

    Pull-resource edge whose predecessor declares a needed provider.

    Why
    ----
    Dependencies make missing topology explicit. A frontier node can advertise
    what it needs before any provider exists, then let the resolver bind a
    concrete successor later during planning.

    Key Features
    ------------
    * Couples one embedded :class:`Requirement` to graph topology.
    * Keeps ``provider`` and ``successor`` synchronized so resolution state is
      visible through normal edge traversal.

    API
    ---
    - :meth:`set_provider` validates and stores the resolved provider while
      synchronizing ``successor``.
    - :meth:`set_successor` provides a topology-first alias that also updates
      requirement state.

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


    def set_provider(self, value: Optional[PT], _ctx=None) -> None:
        # could just leave successor_id None and defer to provider-id in all cases to
        # entirely avoid syncing concern.  might also make the end-type more clear as
        # the expected provider type.
        if value is None:
            self.requirement.provider_id = None
            self.requirement.resolved_step = None
            self.requirement.resolved_cursor_id = None
            super().set_successor(None, _ctx=_ctx)
            return
        super().set_provider(value, _ctx=_ctx)
        super().set_successor(value, _ctx=_ctx)

    def set_successor(self, value: Optional[PT], _ctx=None) -> None:
        if value is None:
            self.requirement.provider_id = None
            self.requirement.resolved_step = None
            self.requirement.resolved_cursor_id = None
            super().set_successor(None, _ctx=_ctx)
            return
        self.set_provider(value, _ctx=_ctx)


class Affordance(Edge, HasRequirement[PT], Generic[PT]):
    """Affordance(predecessor_id: UUID | None = None, requirement: Requirement[PT])

    Push-resource edge whose predecessor offers a provider to nearby consumers.

    Why
    ----
    Affordances model already-available local providers that should be treated
    as preferred EXISTING offers before wider search proceeds.

    Key Features
    ------------
    * Couples one embedded :class:`Requirement` to a provider edge that pushes
      availability outward from its predecessor.
    * Keeps ``provider`` and ``successor`` synchronized so local offer graphs
      stay consistent.

    API
    ---
    - :meth:`set_provider` validates and stores the resolved provider while
      synchronizing ``successor``.
    - :meth:`set_successor` provides a topology-first alias that also updates
      requirement state.

    Example:
        >>> reg = Registry()
        >>> r = Affordance(requirement={'has_identifier': 'foo'}); reg.add(r)
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

    def set_provider(self, value: Optional[PT], _ctx=None) -> None:
        """Bind provider and synchronize to ``successor`` (push resource)."""
        if value is None:
            self.requirement.provider_id = None
            self.requirement.resolved_step = None
            self.requirement.resolved_cursor_id = None
            super().set_successor(None, _ctx=_ctx)
            return
        super().set_provider(value, _ctx=_ctx)
        super().set_successor(value, _ctx=_ctx)

    def set_successor(self, value: Optional[PT], _ctx=None) -> None:
        """Provider alias for ``successor`` on affordance edges."""
        if value is None:
            self.requirement.provider_id = None
            self.requirement.resolved_step = None
            self.requirement.resolved_cursor_id = None
            super().set_successor(None, _ctx=_ctx)
            return
        self.set_provider(value, _ctx=_ctx)


class Fanout(Edge, Generic[PT]):
    """Fanout(predecessor_id: UUID | None = None, requirement: Requirement[PT])

    Non-blocking gather edge that resolves to every eligible provider.

    Why
    ----
    Some runtime nodes, such as activity hubs or sandbox menus, do not need one
    best provider. They need the complete set of currently eligible providers so
    later planning handlers can surface them as affordances or dynamic actions.

    Key Features
    ------------
    * Carries one selector-shaped :class:`Requirement` while storing many
      resolved provider ids.
    * Exposes dereferenced ``providers`` plus explicit ``set_providers`` and
      ``clear_providers`` helpers.
    * Remains non-blocking: an empty provider set is valid and does not make
      frontier resolution fail.

    API
    ---
    - :attr:`providers` dereferences all currently linked provider ids.
    - :meth:`set_providers` validates and stores a whole provider set.
    - :meth:`clear_providers` removes all current links.
    """

    requirement: Requirement[PT]
    provider_ids: list[UUID] = Field(default_factory=list)

    @property
    def providers(self) -> list[PT]:
        registry = getattr(self, "registry", None)
        if registry is None:
            return []

        providers: list[PT] = []
        for provider_id in self.provider_ids:
            provider = registry.get(provider_id)
            if provider is not None:
                providers.append(provider)
        return providers

    def set_providers(self, providers: Iterable[PT], _ctx=None) -> None:
        registry = getattr(self, "registry", None)
        if registry is None:
            raise ValueError("Fanout must be bound to a registry before setting providers")

        validated_ids: list[UUID] = []
        seen_ids: set[UUID] = set()
        for provider in providers:
            if not self.requirement._validate_satisfied_by(provider):
                continue
            if registry._validate_linkable(provider):
                if provider.uid in seen_ids:
                    continue
                seen_ids.add(provider.uid)
                validated_ids.append(provider.uid)

        self.provider_ids = validated_ids
        stamp_requirement_resolution(self.requirement, _ctx=_ctx)

    def clear_providers(self) -> None:
        self.provider_ids.clear()
        self.requirement.resolved_step = None
        self.requirement.resolved_cursor_id = None
