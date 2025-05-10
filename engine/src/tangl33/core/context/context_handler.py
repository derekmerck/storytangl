from typing import Callable

from ..enums import Phase, Tier
from ..capability import Capability

class ContextHandler(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Mapping
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.CONTEXT, **meta)
        self.func = func

def context_handler(priority: int = 0, **kw):
    def _wrap(fn): return ContextHandler(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap
