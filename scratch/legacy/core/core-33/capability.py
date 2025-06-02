"""
tangl.core.capability
=====================

Executable behavior units with phased, tiered execution semantics.

Capabilities are the primary extension mechanism in StoryTangl,
representing discrete behaviors that execute during specific phases
of graph traversal. Key features include:

- Phase-targeted execution (context gathering, rendering, etc.)
- CoreScope-based scope control (node-local, graph-wide, etc.)
- Priority-based ordering within phase/CoreScope combinations
- Conditional activation through predicates
- Owner-based filtering for node-specific behaviors

This design enables a clean separation between:
- WHAT happens (the capability implementation)
- WHEN it happens (phase, CoreScope, priority)
- WHERE it happens (owner node)
- IF it happens (predicate)

Unlike traditional event systems, capabilities form a structured
protocol that ensures deterministic execution while maintaining
flexibility for authors and developers.

See Also
--------
context_cap, render_cap, redirect_handler, continue_handler:
    Decorator factories for service capabilities
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from uuid import UUID

from .enums import CoreScope, CoreService
from .type_hints import Predicate, StringMap

if TYPE_CHECKING:
    from .scope import Node, Graph

# ------------------------------------------------------------
# Capability base
# ------------------------------------------------------------
@dataclass(kw_only=True)
class Capability:
    """
    A single scheduled unit of service work for a given phase and CoreScope

    Order is **deterministic across phases / tiers** and
    **priority-sorted within the same phase/CoreScope**.
    """
    # phase: DriverPhase
    CoreScope: CoreScope
    service: CoreService
    priority: int = 0
    predicate: Predicate = lambda ctx: True  # ctx should satisfy the predicate
    owner_uid: UUID = None  # points back to registering provider, but avoids import

    # Note, only PROVIDER capabilities need provision keys, b/c only PROVIDERS match requirements

    # -----------------------------------------------------------------
    # core API
    # -----------------------------------------------------------------
    def should_run(self, ctx: StringMap) -> bool:
        return self.predicate(ctx)

    def apply(self, node: Node, driver, graph: Graph, ctx: StringMap) -> Any:
        """
        Sub-classes override.  Return type depends on service type:
        * PROVIDER         -> New node to link as a provider
        * CONTEXT          →  Mapping layer
        * CHOICE           →  Optional[Edge]
        * GATE             → ?
        * EFFECTS          →  None
        * RENDER           →  list[Fragment]
        """
        raise NotImplementedError

    # todo: Should gating be in here?

    # -----------------------------------------------------------------
    # rich comparison for heap / sort() stability
    # -----------------------------------------------------------------

    # todo: do we use this or want to use phase?  caps don't care what phase they belong to, just what phase they are being called in (basically before or after).  They will only be sorted _within_ a service bucket anyway.  And they get sorted at by CoreScope level in the view.
    def _sort_key(self):
        """(phase, CoreScope, service, -priority)  → deterministic ascending"""
        return (self.CoreScope, -self.priority)

    def __lt__(self, other: Capability):
        return self._sort_key() < other._sort_key()
