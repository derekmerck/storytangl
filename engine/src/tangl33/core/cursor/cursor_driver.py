from uuid import UUID
import logging
from collections import ChainMap

from ..type_hints import StringMap
from ..enums import Phase, Tier, Service
from ..tier_view import TierView

from ..render.journal import Journal
from ..graph import Graph, EdgeKind, EdgeTrigger, EdgeState, GlobalScope, Domain

# Phase helpers
from ..context.gather_context import gather_context
from ..provision.resolve_requirements import resolve_requirements
from ..render.render_fragments import render_fragments

logger = logging.getLogger(__name__)

class CursorDriver:
    def __init__(self,
                 graph: Graph,
                 domain: Domain = None,
                 journal: Journal = None):
        self.graph = graph
        self.domain = domain if domain is not None else Domain()
        self.journal = journal if journal is not None else Journal()
        self.cursor_uid: None | UUID = None     # set externally

    # -----------------------------------------------------------------
    # public API
    # -----------------------------------------------------------------
    def step(self):
        if self.cursor_uid is None:
            raise RuntimeError(f"Cursor uid not set")
        if self.cursor_uid not in self.graph:
            raise RuntimeError(f"Cursor uid {self.cursor_uid} not in graph {list(self.graph.keys())}")
        node = self.graph.get(self.cursor_uid)
        logger.debug(f"Stepping into {node!r}")

        # 1. gather ctx phase
        # -------------------
        logger.debug(f"Building context for node {node!r}")
        ctx = gather_context(node, self.graph, self.domain)

        # 2. check redirects and resolve unmet requirements (may mutate graph)
        # -------------------
        logger.debug(f"Resolving node {node!r}")
        next_edge = resolve_requirements(node, self.graph, self.domain, ctx)
        # todo: this doesn't return a 'next_edge' anymore?

        # todo: run 'before-effect phase'

        # todo: run new gate phase, or is this just another predicate part of resolution,
        #       it's resolvable but still latent b/c unavailable?
        if next_edge:
            # 2.5 cursor advance
            self.cursor_uid = next_edge.dst_uid
            return

        # 3. render phase and update journal
        # -------------------
        logger.debug(f"Rendering node {node!r}")
        frags = render_fragments(node, self.graph, self.domain, ctx)
        logger.debug(f"Got frags: {frags!r}")
        self.journal.append_fragments(frags)

        # 4. finalize phase and check continues
        # -------------------
        next_edge = self._run_finalize_phase(node, self.graph, self.domain, ctx)
        # todo: this is stubbed out, why are we changing the interface here and trying to
        #       use a multi-service tier view?
        # todo: run after-effect phase
        if next_edge:
            # 2.5. cursor advance
            self.cursor_uid = next_edge.dst_uid
            return

        # 5. block on player input or end-state
        pass

    # -----------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------

    def _run_gate_phase(self, node, handlers_view, ctx):
        # 1) run GATE caps (stat predicates, etc.)
        for tier in Tier.range_outwards(Tier.NODE):
            for cap in handlers_view.iter_layer(tier):
                if cap.service is not Service.GATE:
                    continue
                if tier is Tier.NODE and cap.owner_uid not in (None, node.uid):
                    continue
                cap.apply(node, self, self.graph, ctx)

        # 2) set edge.state → OPEN when gate passes
        for edge in filter(lambda x: x.kind is EdgeKind.CHOICE, self.graph.edges_out[node.uid]):
            if edge.state == EdgeState.RESOLVED and edge.gate_pred(ctx):
                edge.state = EdgeState.OPEN

    # def _run_finalize_phase(self, node, graph, domain, ctx):
    def _run_finalize_phase(self, node, handlers_view, ctx, *args, **kwargs):
        return
        logger.debug(f"Resolving node {node!r}")
        # -> call after effects (bookkeeping)
        # -> find satisfied after choices and optional short circuit
        # AFTER-Choice selection
        for tier in Tier.range_outwards(Tier.NODE):
            for cap in handlers_view.iter_layer(tier):
                if (cap.service is Service.CHOICE and
                    cap.trigger is EdgeTrigger.AFTER and
                    cap.predicate(ctx)):
                    edge = cap.build_edge(node, self.graph, ctx)
                    if edge.open:
                        return edge
