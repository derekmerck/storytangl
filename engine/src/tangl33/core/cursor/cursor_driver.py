from ..context import gather
from ..graph import Node, Graph
from ..runtime import CapabilityCache, ProvisionRegistry
from ..render import render_fragments, Journal
from ..resolver import resolve

class CursorDriver:

    def step(self, current: Node, graph: Graph, cap_cache: CapabilityCache, prov_reg: ProvisionRegistry, domain: 'Domain', journal: Journal):
        ctx = gather(current, graph, cap_cache, domain.get_globals())
        resolve(current, graph, prov_reg, cap_cache, ctx)
        # walk phase loop calling caps (redirect, effects, render, …)
        frags = render_fragments(current, ctx)
        journal.append_fragments(frags)
        self._advance_cursor()