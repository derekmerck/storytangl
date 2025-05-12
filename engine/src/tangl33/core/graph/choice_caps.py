from typing import Callable

from ..enums import Phase, Tier, Service
from ..capability import Capability

class RedirectCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.RESOLVE, service=Service.CHOICE, **meta)
        self.func = func

def redirect_cap(priority: int = 0, **kw):
    def _wrap(fn): return RedirectCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap


class ContinueCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.FINALIZE, service=Service.CHOICE, **meta)
        self.func = func

def continue_cap(priority: int = 0, **kw):
    def _wrap(fn): return ContinueCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap
