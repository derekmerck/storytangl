from uuid import UUID

from ..enums import Phase, Tier
from ..context.gather import gather
from ..resolver.resolve import resolve
from ..render.render_fragments import render_fragments
from ..render.journal import Journal
from ..runtime.handler_cache import HandlerCache
from ..runtime.provider_registry import ProviderRegistry
from ..graph.graph import Graph, EdgeKind

class CursorDriver:
    def __init__(self, graph: Graph,
                 cap_cache: HandlerCache,
                 prov_reg: ProviderRegistry,
                 domain,
                 journal: Journal):
        self.graph = graph
        self.cap_cache = cap_cache
        self.prov_reg = prov_reg
        self.domain = domain
        self.journal = journal
        self.cursor_uid: UUID = None     # set externally

    # -----------------------------------------------------------------
    # public API
    # -----------------------------------------------------------------
    def step(self):
        node = self.graph.get(self.cursor_uid)
        ctx  = gather(node, self.graph, self.cap_cache,
                      globals=self.domain.get_globals())

        # 1. resolve unmet requirements (may mutate graph)
        resolve(node, self.graph, self.prov_reg, self.cap_cache, ctx)

        # 2. phase loop
        next_edge = (
            self._run_phase(node, Phase.CHECK_REDIRECTS, ctx)
            or self._run_phase(node, Phase.APPLY_EFFECTS , ctx)
            or self._render_phase(node, ctx)
            or self._run_phase(node, Phase.CHECK_CONTINUES, ctx)
        )

        # 3. cursor advance
        if next_edge:
            self.cursor_uid = next_edge.dst_uid
        else:
            # block on player input or end-state
            pass

    # -----------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------
    def _run_phase(self, node, phase: Phase, ctx):
        for tier in Tier.range_inwards(Tier.NODE):
            for cap in self.cap_cache.iter_phase(phase, tier):
                if cap.owner_uid == node.uid or tier is not Tier.NODE:
                    edge = cap.apply(node, self, self.graph, ctx)
                    if edge:          # first non-None wins
                        return edge

    def _render_phase(self, node, ctx):
        frags = render_fragments(node, ctx, self.cap_cache)
        self.journal.append_fragments(frags)