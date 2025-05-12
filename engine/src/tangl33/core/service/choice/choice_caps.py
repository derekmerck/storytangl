from typing import Callable

from ...enums import CoreScope, CoreService
from ...capability import Capability

class RedirectCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(service=CoreService.CHOICE, **meta)
        self.func = func

def redirect_cap(priority: int = 0, **kw):
    def _wrap(fn): return RedirectCap(fn, CoreScope=kw.get("CoreScope", CoreScope.NODE), priority=priority)
    return _wrap


class ContinueCap(Capability):
    def apply(self, node, driver, graph, ctx):  # returns Optional[Edge]
        return self.func(node, driver, graph, ctx)

    def __init__(self, func: Callable, **meta):
        super().__init__(service=CoreService.CHOICE, **meta)
        self.func = func

def continue_cap(priority: int = 0, **kw):
    def _wrap(fn): return ContinueCap(fn, CoreScope=kw.get("CoreScope", CoreScope.NODE), priority=priority)
    return _wrap
