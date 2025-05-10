"""
tangl.core.capability
=====================

Executable behavior units with phased, tiered execution semantics.

Capabilities are the primary extension mechanism in StoryTangl33,
representing discrete behaviors that execute during specific phases
of graph traversal. Key features include:

- Phase-targeted execution (context gathering, rendering, etc.)
- Tier-based scope control (node-local, graph-wide, etc.)
- Priority-based ordering within phase/tier combinations
- Conditional activation through predicates
- Owner-based filtering for node-specific behaviors

This design enables a clean separation between:
- WHAT happens (the capability implementation)
- WHEN it happens (phase, tier, priority)
- WHERE it happens (owner node)
- IF it happens (predicate)

Unlike traditional event systems, capabilities form a structured
protocol that ensures deterministic execution while maintaining
flexibility for authors and developers.

See Also
--------
context_handler, render_handler, redirect_handler, continue_handler:
    Decorator factories for common capability types
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from uuid import UUID

from .enums import Phase, Tier
from .type_hints import Predicate, StringMap

if TYPE_CHECKING:
    from .graph import Node, Graph

# ------------------------------------------------------------
# Capability base
# ------------------------------------------------------------
@dataclass(kw_only=True)
class Capability:
    """
    A single scheduled unit of work.

    Order is **deterministic across phases / tiers** and
    **priority-sorted within the same phase/tier**.
    """
    phase: Phase
    tier: Tier
    priority: int = 0
    predicate: Predicate = lambda ctx: True
    owner_uid: UUID = None  # points back to registering provider, but avoids import

    # -----------------------------------------------------------------
    # core API
    # -----------------------------------------------------------------
    def should_run(self, ctx: StringMap) -> bool:
        return self.predicate(ctx)

    def apply(self, node: Node, driver, graph: Graph, ctx: StringMap) -> Any:
        """
        Sub-classes override.  Return type depends on phase:
        * CONTEXT   →  Mapping layer
        * CHECK_REDIRECTS  →  Optional[Edge]
        * APPLY_EFFECTS    →  None
        * RENDER           →  list[Fragment]
        * CHECK_CONTINUES  →  Optional[Edge]
        """
        raise NotImplementedError

    # -----------------------------------------------------------------
    # rich comparison for heap / sort() stability
    # -----------------------------------------------------------------

    def _sort_key(self):
        """(phase, tier, -priority)  → deterministic ascending"""
        return (self.phase, self.tier, -self.priority)

    def __lt__(self, other: Capability):
        return self._sort_key() < other._sort_key()
