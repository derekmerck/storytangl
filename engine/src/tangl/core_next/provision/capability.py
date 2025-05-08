from __future__ import annotations

from pydantic.dataclasses import dataclass, Field
from typing import Callable, Any, Set

from ..enums import StepPhase, Tier
from ..entity import Entity
from ..type_hints import Context, Predicate

# ------------------------------------------------------------
# Capability base
# ------------------------------------------------------------
@dataclass  # Can't be slotted and still mix-in with Entity later
class Capability:
    """
    A single scheduled unit of work.

    Order is **deterministic across phases / tiers** and
    **priority-sorted within the same phase/tier**.
    """
    phase:     StepPhase
    tier:      Tier
    priority:  int = 0
    predicate: Predicate = Field(default=lambda ctx: True, repr=False)

    # -----------------------------------------------------------------
    # core API
    # -----------------------------------------------------------------
    def should_run(self, ctx: Context) -> bool:
        return self.predicate(ctx)

    def apply(self, node, driver, graph, ctx: Context) -> Any:
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

    def __lt__(self, other: "Capability"):
        return self._sort_key() < other._sort_key()


# ------------------------------------------------------------
# Concrete subclasses  (thin wrappers around old handlers)
# ------------------------------------------------------------
class ContextCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Mapping
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=StepPhase.GATHER_CONTEXT, **meta)
        self.func = func


class RedirectCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=StepPhase.CHECK_REDIRECTS, **meta)
        self.func = func


class EffectCap(Capability):
    def apply(self, node, driver, graph, ctx):  # mutates state
        self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=StepPhase.APPLY_EFFECTS, **meta)
        self.func = func


class RenderCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns list[Fragment]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=StepPhase.RENDER, **meta)
        self.func = func


class ContinueCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=StepPhase.CHECK_CONTINUES, **meta)
        self.func = func


class ProvisionCap(Capability):
    """
    Registers a *provider* for some resource (shop, actor, sound, …).

    *provides* is a set of keys this provider can satisfy.
    """
    provides: Set[str]

    def __init__(
        self,
        provides: Set[str],
        predicate: Predicate = lambda ctx: True,
        tier: Tier = Tier.NODE,
        priority: int = 0,
    ):
        super().__init__(
            phase=StepPhase.GATHER_CONTEXT,  # consulted by Resolver, not cursor
            tier=tier,
            priority=priority,
            predicate=predicate,
        )
        self.provides = provides

    # In most cases apply() just returns the provider-node reference
    def apply(self, node, driver, graph, ctx):
        return node


# ------------------------------------------------------------
# Convenience decorators (keep compatibility with old code)
# ------------------------------------------------------------
def context_cap(priority: int = 0, **kw):
    def _wrap(fn): return ContextCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap

def redirect_cap(priority: int = 0, **kw):
    def _wrap(fn): return RedirectCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap

def effect_cap(priority: int = 0, **kw):
    def _wrap(fn): return EffectCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap

def render_cap(priority: int = 0, **kw):
    def _wrap(fn): return RenderCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap

def continue_cap(priority: int = 0, **kw):
    def _wrap(fn): return ContinueCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap
