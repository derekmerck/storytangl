from typing import Callable

from ..capability import Capability
from ..enums import Phase, Tier, Service

class RenderCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns list[Fragment]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(phase=Phase.RENDER, service=Service.RENDER, **meta)
        self.func = func


def render_cap(priority: int = 0, **kw):
    def _wrap(fn): return RenderCap(fn, tier=kw.get("tier", Tier.NODE), priority=priority)
    return _wrap
