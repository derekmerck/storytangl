from typing import Callable

from ...enums import CoreScope, CoreService
from ...capability import Capability

# todo: I think we need an effect handler, this should probably be with that.

class EffectCap(Capability):
    def apply(self, node, driver, graph, ctx):  # mutates state
        self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(service=CoreService.EFFECT, **meta)
        self.func = func

def effect_cap(priority: int = 0, **kw):
    def _wrap(fn): return EffectCap(fn, CoreScope=kw.get("CoreScope", CoreScope.NODE), priority=priority)
    return _wrap
