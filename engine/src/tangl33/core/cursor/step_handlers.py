from typing import Callable

from ..enums import Phase, Tier
from ..capability import Capability

class RedirectHandler(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.CHECK_REDIRECTS, **meta)
        self.func = func

def redirect_handler(priority: int = 0, **kw):
    def _wrap(fn): return RedirectHandler(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap

class EffectHandler(Capability):
    def apply(self, node, driver, graph, ctx):  # mutates state
        self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.APPLY_EFFECTS, **meta)
        self.func = func

# todo: I think we need an effect handler, this should probably be with that.

def effect_handler(priority: int = 0, **kw):
    def _wrap(fn): return EffectHandler(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap

class ContinueHandler(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.CHECK_CONTINUES, **meta)
        self.func = func

def continue_handler(priority: int = 0, **kw):
    def _wrap(fn): return ContinueHandler(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap
