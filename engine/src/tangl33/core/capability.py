from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .enums import Phase, Tier
from .type_hints import Predicate, Context

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

    # -----------------------------------------------------------------
    # core API
    # -----------------------------------------------------------------
    def should_run(self, ctx: Context) -> bool:
        return self.predicate(ctx)

    def apply(self, node: Node, driver, graph: Graph, ctx: Context) -> Any:
        """
        Sub-classes override.  Return type depends on phase:
        * GATHER_CONTEXT   →  Mapping layer
        * CHECK_REDIRECTS  →  Optional[Edge]
        * APPLY_EFFECTS    →  None
        * RENDER           →  list[Fragment]
        * CHECK_CONTINUES  →  Optional[Edge]
        """
        raise NotImplementedError

    # -----------------------------------------------------------------
    # rich comparison for heap / sort() stability
    # -----------------------------------------------------------------
    # __slots__ = ()

    def _sort_key(self):
        """(phase, tier, -priority)  → deterministic ascending"""
        return (self.phase, self.tier, -self.priority)

    def __lt__(self, other: Capability):
        return self._sort_key() < other._sort_key()
