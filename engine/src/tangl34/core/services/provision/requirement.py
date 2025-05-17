from typing import Callable, Optional, Literal, Dict, Any

from ...entity import Entity

# Requirements:
# - Select _provider_, uses `entity.match(**req_criteria)`; then links
# - Select _builder_ uses `entity.provides_match(**req_criteria)`, where the entity is an indirect provider, then calls entity.build(ctx) and links

# Gated, available:
# - Uses entity.predicate(ctx) -> bool (where ctx is an entity's ns view)

class Requirement(Entity):
    """
    A Requirement represents a declarative need that a node may have within a given context.

    Terminology:
    - requirement_gate: a callable predicate (ctx → bool) that determines whether this requirement applies.
    - provider_criteria: a dict of attribute filters used to identify matching providers.
    - fallback_cap: an optional capability used to satisfy the requirement if no provider is found.
    - scope_bounds: defines how far the resolution search should go (e.g. local, graph, domain, global).
    """

    scope_bounds: Any = None  # Limits where to search for satisfying providers
    requirement_gate: Callable[[Dict[str, Any]], bool]  # Predicate that gates whether the requirement is active
    provider_criteria: Dict[str, Any]  # Used for provider match or can-provide-match
    fallback_cap: Optional['Capability'] = None  # Fallback capability for soft resolution

    def satisfied(self, ctx: Dict[str, Any]) -> bool:
        """Check whether the requirement is active and should be processed."""
        return self.requirement_gate(ctx)

    def satisfied_by(self, provider: Entity) -> bool:
        """Check whether the given provider satisfies this requirement."""
        return provider.match(**self.provider_criteria)

    def resolve(self, ctx: Dict[str, Any]) -> bool:
        """Attempt to resolve the requirement by any means: direct, indirect, or fallback."""
        return (self.satisfied(ctx) or
                self.find_satisfier(ctx) or
                self.create_satisfier(ctx))

    def find_satisfier(self, ctx: Dict[str, Any]) -> bool:
        """Placeholder for search among existing providers."""
        return False

    def create_satisfier(self, ctx: Dict[str, Any]) -> bool:
        """Placeholder for invoking builder or fallback capability."""
        return False
