from typing import Callable

from ...enums import CoreScope, CoreService
from ...capability import Capability

# ChoiceCaps are like ProviderCaps, but they link choice edges instead of providing nodes.

# choice caps that are 'found' will relink their _source_ to the current node and abandon their prior node, this allows edges to places to be re-used and avoids unnecessary edges.
# choice caps that are 'created' will should check that their destination is resolvable before presenting themselves.
# Then they can be gated as usual.

# an explicit choice is just a choice cap added directly to a node.
# scoped choices can be added at different tiers, like an ancestor/subgraph wide "return to lobby" or a domain-wide "return home"

# I am still thinking that we need _more_ scopes and the ability to add them flexibly (or incremental scope?).  Like what if the user is in a country within their story world (Domain) and we want country-wide rules that layer under domain?  Or a country on a world within a story universe (Domain), gravity is different on the world, but the same for all countries.

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
