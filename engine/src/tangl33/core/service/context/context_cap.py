from typing import Callable

from ...enums import CoreScope, CoreService
from ...capability import Capability

class ContextCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Mapping
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(service=CoreService.CONTEXT, **meta)
        self.func = func

def context_cap(priority: int = 0, **kw):
    def _wrap(fn): return ContextCap(fn, CoreScope=kw.get("CoreScope", CoreScope.NODE), priority=priority)
    return _wrap
