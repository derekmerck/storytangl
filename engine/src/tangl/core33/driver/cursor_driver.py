from uuid import UUID
import logging
from collections import ChainMap

from ..type_hints import StringMap
from ..enums import CoreScope, CoreService
from ..service.tier_view import TierView  # todo: no longer necessary after refactoring out service controller calls

from ..graph import Graph, ChoiceTrigger, EdgeState
from ..scope import Domain

# Phase helpers
from ..service.context.gather_context import gather_context
from ..service.provision.resolve_requirements import resolve_requirements
from ..service.gate.apply_gating import apply_gating
from ..service.effect.apply_effects import apply_effects
from ..service.render import Journal
from ..service.render.render_fragments import render_fragments

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
        #       use a multi-service CoreScope view?
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



    # def _run_finalize_phase(self, node, graph, domain, ctx):
    def _run_finalize_phase(self, node, handlers_view, ctx, *args, **kwargs):
        return
        logger.debug(f"Resolving node {node!r}")
        # -> call after effects (bookkeeping)
        # -> find satisfied after choices and optional short circuit
        # AFTER-Choice selection
        for CoreScope in CoreScope.range_outwards(CoreScope.NODE):
            for cap in handlers_view.iter_layer(CoreScope):
                if (cap.service is Service.CHOICE and
                    cap.trigger is ChoiceTrigger.AFTER and
                    cap.predicate(ctx)):
                    edge = cap.build_edge(node, self.graph, ctx)
                    if edge.open:
                        return edge
