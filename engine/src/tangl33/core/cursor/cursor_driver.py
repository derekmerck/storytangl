from uuid import UUID
import logging
from collections import ChainMap

from ..type_hints import StringMap
from ..enums import Phase, Tier, Service
from ..resolver.resolve import resolve
from ..render.render_fragments import render_fragments
from ..render.journal import Journal
from ..tier_view import TierView
from ..runtime.handler_cache import HandlerCache
from ..runtime.provider_registry import ProviderRegistry
from ..graph import Graph, EdgeKind, EdgeTrigger, EdgeState, GlobalScope, Domain

logger = logging.getLogger(__name__)

class CursorDriver:
    def __init__(self, graph: Graph,
                 cap_cache: HandlerCache,
                 prov_reg: ProviderRegistry,
                 domain: Domain = None,
                 journal: Journal = None):
        self.graph = graph
        self.cap_cache = cap_cache
        self.prov_reg = prov_reg
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
        ctx = self._run_gather_phase(node, self.graph, self.domain)

        # 2. check redirects and resolve unmet requirements (may mutate graph)
        # next_edge = resolve(node, self.graph, self.prov_reg, self.cap_cache, ctx)
        # todo: turn this into a service/phase call
        next_edge = self._run_resolve_phase(node, self.graph, self.domain, ctx)
        # todo: run new gate phase
        if next_edge:
            # 2.5 cursor advance
            self.cursor_uid = next_edge.dst_uid
            return

        # 3. render phase and update journal
        self._run_render_phase(node, self.graph, self.domain, ctx)

        # 4. finalize phase and check continues
        next_edge = self._run_phase(node, Phase.FINALIZE, ctx)
        # todo: turn this into a service/phase call
        # next_edge = self._run_finalize_phase(node, self.graph, self.domain, ctx)
        if next_edge:
            # 2.5. cursor advance
            self.cursor_uid = next_edge.dst_uid
            return

        # 5. block on player input or end-state
        pass

    # -----------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------
    def _run_phase(self, node, phase: Phase, ctx):
        logger.debug(f"Running phase {phase.name}")
        for tier in Tier.range_outwards(Tier.NODE):
            for cap in self.cap_cache.iter_phase(phase, tier):
                if tier is Tier.NODE and cap.owner_uid not in (None, node.uid):
                    continue
                edge = cap.apply(node, self, self.graph, ctx)
                if edge:
                    return edge

    def _run_gather_phase(self, node, graph, domain) -> StringMap:
        # 1) compose a view for CONTEXT service
        ctx_view = TierView.compose(
            service=Service.CONTEXT,
            NODE=node.local_layer(),  # locals dict
            ANCESTORS=ChainMap(*(anc.local_layer()
                                 for anc in node.iter_ancestors(graph=graph))),
            GRAPH=graph.local_layer(),
            DOMAIN=domain.local_layer(),
            GLOBAL=GlobalScope.get_instance().local_layer()
        )

        # 2) walk tiers inner→outer, merging dicts
        layers = []
        for tier in Tier.range_outwards(Tier.NODE):
            layers.append(ctx_view._get_layer(tier))
        # _earlier_ tiers closer to the origin win
        return ChainMap(*layers)  # plain dict for speed

    def _run_resolve_phase(self, node, graph, domain, ctx):
        logger.debug(f"Resolving node {node!r}")
        # Build provider & template views once
        provider_view = TierView.compose(
            service=Service.PROVIDER,
            NODE=node.handler_layer(Service.PROVIDER),
            GRAPH=graph.handler_layer(Service.PROVIDER),
            DOMAIN=domain.handler_layer(Service.PROVIDER),
            GLOBAL=GlobalScope.get_instance().handler_layer(Service.PROVIDER)
        )
        template_view = TierView.compose(
            service=Service.TEMPLATE,
            NODE=node.template_layer(),
            GRAPH=graph.template_layer(),
            DOMAIN=domain.template_layer(),
            GLOBAL=GlobalScope.get_instance().template_layer(),
        )

        # -> find satisfied before choices and optional short circuit
        # -> call resolver service
        # -> run before effects

        # todo: template build is a fallback provider service?

        # Resolve outgoing edges breadth-first one hop
        next_edge = None
        for edge in filter(lambda e: e.kind is EdgeKind.CHOICE, graph.edges_out[node.uid]):

            # ---------- 1. resolve one-hop cone ----------
            if self._resolve_target(edge.dst_uid, provider_view, template_view, ctx):
                edge.state = EdgeState.RESOLVED
            else:
                edge.state = EdgeState.LATENT

            # ---------- 2. first BEFORE-choice wins ----------
            if (edge.state is EdgeState.RESOLVED
                    and edge.trigger is EdgeTrigger.BEFORE
                    and edge.open):
                next_edge = edge
                break

    def _resolve_target(self, uid, providers, templates, ctx, depth=1):

        # ---------- target missing?  ----------
        if uid not in self.graph:
            raise RuntimeError(f"Trying to resolve an unlinked node: {uid}")

        # trivial depth-first resolver (1 hop)
        tgt = self.graph[uid]
        for req in getattr(tgt, "requires", []):
            prov = self._find_provider(req, providers, ctx)
            if not prov:
                prov = self._build_from_template(req, templates, ctx)
                if prov is not None:
                    self.graph.add(prov)
            if prov:
                # todo: If found as an existing node-level provides it may be already linked?
                self.graph.link(uid, prov, EdgeKind.PROVIDES)
                # todo: This should be in the graph ctx layer, any outgoing link of type provides gets added (dynamically?) to the context at the graph layer, we don't want to write the entire locals of each provision into the node itself...
                # auto-register context injector so render sees the new provider
                node = self.graph[uid]
                key = prov.locals.get('role', req.key)
                logger.debug(f"adding key {key} to {node!r} ctx for provider {prov!r}")
                node.locals[key] = prov.locals
            else:
                return False
        return True

    def _find_provider(self, req, provider_view, ctx):
        for tier in Tier.range_outwards(Tier.NODE):
            for prov in provider_view._get_layer(tier):
                if prov.provides(req) and req.strategy.select(prov, req, ctx):
                    return prov
        return None

    def _build_from_template(self, req, template_view, ctx):
        for tier in Tier.range_outwards(Tier.NODE):
            for tpl in template_view._get_layer(tier).values():
                if req.key in tpl.provides:
                    cap = tpl.build(ctx)  # returns ProviderCap
                    # store in the proper layer so later look-ups see it
                    self.graph.handler_layer(Service.PROVIDER).append(cap)
                    return cap
        return None

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

    def _run_render_phase(self, node, graph, domain, ctx):
        # -> Run render service
        # -> Update journal
        logger.debug(f"Rendering node {node!r}")
        frags = render_fragments(node, graph, domain, ctx)
        logger.debug(f"Got frags: {frags!r}")
        self.journal.append_fragments(frags)

    # def _run_finalize_phase(self, node, graph, domain, ctx):
    def _run_finalize_phase(self, node, handlers_view, ctx):
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
