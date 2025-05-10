from uuid import UUID
import logging
from typing import Mapping

from .. import TieredMap
from ..enums import Phase, Tier
from ..context.gather import gather
from ..resolver.resolve import resolve
from ..render.render_fragments import render_fragments
from ..render.journal import Journal
from ..runtime.handler_cache import HandlerCache
from ..runtime.provider_registry import ProviderRegistry
from ..graph.graph import Graph, EdgeKind
from ..graph.domain import Domain

logger = logging.getLogger(__name__)

class CursorDriver:
    def __init__(self, graph: Graph,
                 cap_cache: HandlerCache,
                 prov_reg: ProviderRegistry,
                 domain: Domain = None,
                 journal: Journal = None,
                 globals: Mapping = None):
        self.graph = graph
        self.cap_cache = cap_cache
        self.prov_reg = prov_reg
        self.domain = domain if domain is not None else Domain()
        self.journal = journal if journal is not None else Journal()
        self.globals = globals if globals is not None else {}
        self.cursor_uid: UUID = None     # set externally

    # -----------------------------------------------------------------
    # public API
    # -----------------------------------------------------------------
    def step(self):
        if self.cursor_uid not in self.graph:
            raise RuntimeError(f"Cursor uid {self.cursor_uid} not in graph {list(self.graph.keys())}")
        node = self.graph.get(self.cursor_uid)
        logger.debug(f"Stepping at {node!r}")

        ctx = gather(node, self.graph, self.cap_cache, self.globals)

        # from ..provision import Template
        # templates = TieredMap[Template]()
        # templates.inject(Tier.DOMAIN, self.domain.get_templates())
        #
        # from ..capability import Capability
        # cap_cache = TieredMap[Capability]()
        # cap_cache.inject(Tier.GLOBAL, self.cap_cache)

        # ctx['templates'] = self.domain.get_templates()

        # 1. resolve unmet requirements (may mutate graph)
        resolve(node, self.graph, self.prov_reg, self.cap_cache, ctx)

        # 2. phase loop
        next_edge = (
            self._run_phase(node, Phase.REDIRECTS, ctx)
            or self._run_phase(node, Phase.EFFECTS , ctx)
            or self._render_phase(node, ctx)
            or self._run_phase(node, Phase.CONTINUES, ctx)
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
    # def _run_phase(self, node, phase: Phase, ctx):
    #     for tier in Tier.range_inwards(Tier.NODE):
    #         for cap in self.cap_cache.iter_phase(phase, tier):
    #             if cap.owner_uid == node.uid or tier is not Tier.NODE:
    #                 edge = cap.apply(node, self, self.graph, ctx)
    #                 if edge:          # first non-None wins
    #                     return edge
    def _run_phase(self, node, phase: Phase, ctx):
        logger.debug(f"Running phase {phase.name}")
        for tier in Tier.range_inwards(Tier.NODE):
            for cap in self.cap_cache.iter_phase(phase, tier):
                if tier is Tier.NODE and cap.owner_uid not in (None, node.uid):
                    continue
                edge = cap.apply(node, self, self.graph, ctx)
                if edge:
                    return edge

    def _render_phase(self, node, ctx):
        logger.debug(f"Rendering node {node!r}")
        frags = render_fragments(node, ctx, self.cap_cache)
        logger.debug(f"Got frags: {frags!r}")
        self.journal.append_fragments(frags)