from typing import Optional, Literal, Any
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.handler import Predicate
from tangl.core.entity import Entity, Edge, Graph
from .enums import ResolutionState

class Requirement(Edge):
    """
    Declarative need to link a resource in the graph. May be attached to nodes/events/choices as a
    'requires' edge with an initially undefined destination.

    _Resource requirements_ are resolved by a _provisioner_, which may choose to create a new resource
    if it cannot find one that satisfies the requirement within the allowable search scope.

    The returned resource is attached to the requirement with a 'provider' edge and can be accessed
    by the requirement's label from the owner's context.

    Terminology:
    - label: a locally unique string that identifies the requirement in the context of its parent node.
    - predicate: a callable predicate (ctx → bool) that determines whether this requirement applies.
    - provider_criteria: a dict of attribute filters used to identify matching providers.
    - provider_predicate: a function that takes the provider.context? and returns a boolean.
    - scope_bounds: defines how far the resolution search should go (e.g. local, graph, domain, global).
    - obligation: determines how the requirement is handled, e.g. "find_only", "find_or_create", "create_only", "optional".  Optional requirements are ignored if unresolvable.    - fallback_provisioner: an optional local provisioner that can satisfy the requirement if obligation can't be met.
    - resolution_state: the current state of the requirement, e.g. "unresolved", "resolved", "unresolvable", "in_progress".
    """
    edge_kind: EdgeKind = EdgeKind.REQUIREMENT
    dst_id: Optional[UUID] = Field(None, alias="provider_id")
    provider_criteria: StringMap = Field(default_factory=dict)
    provider_predicate: Predicate = Field(None)  # todo: is a predicate just part of the criteria?
    scope_bounds: Any = None
    obligation: Literal["find_only", "find_or_create", "create_only", "optional"] = "find_or_create"
    fallback_provisioner: Optional['Provisioner'] = None
    resolution_state: Optional[ResolutionState] = ResolutionState.UNRESOLVED

    # alias to dest
    def provider(self, g: Graph) -> Optional[Entity]:
        if self.dst_id is not None:
            return super().dst(g)

    @property
    def is_resolved(self) -> bool:
        return self.resolution_state is ResolutionState.RESOLVED or self.resolution_state is ResolutionState.UNRESOLVED and self.obligation == "optional"

    def is_satisfied(self, *, ctx: StringMap, **kwargs) -> bool:
        # resolved and ungated
        return self.is_resolved and super().is_satisfied(ctx=ctx, **kwargs)

    def matches_provider(self, provider: Entity) -> bool:
        """Check whether the given provider satisfies this requirement."""
        return provider.match(**self.provider_criteria)

    # todo: when a provider is assigned, we can add a origin edge to the provisioner that
    #       provided it as well
