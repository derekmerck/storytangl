import logging

from ..enums import Service, Tier
from ..tier_view import TierView
from ..graph import GlobalScope, EdgeKind, EdgeState, EdgeTrigger, Node

logger = logging.getLogger(__name__)


def resolve_requirements(node, graph, domain, ctx):
    logger.debug(f"Resolving node {node!r}")

    # ---------------------------------------------------------
    # 1. compose views
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

    # ---------------------------------------------------------
    # 2. resolve outgoing edges breadth-first one hop
    next_edge = None
    for edge in filter(lambda e: e.kind is EdgeKind.CHOICE, graph.edges_out[node.uid]):

        # ---------- 1. resolve one-hop cone ----------
        if _resolve_target(edge.dst_uid, graph, provider_view, template_view, ctx):
            edge.state = EdgeState.RESOLVED
        else:
            edge.state = EdgeState.LATENT

        # ---------- 2. first BEFORE-choice wins ----------
        if (edge.state is EdgeState.RESOLVED
                and edge.trigger is EdgeTrigger.BEFORE
                and edge.open):
            next_edge = edge
            break

def _resolve_target(uid, graph, providers, templates, ctx, depth=1):

    # ---------- target missing?  ----------
    if uid not in graph:
        raise RuntimeError(f"Trying to resolve an unlinked node: {uid}")

    # trivial depth-first resolver (1 hop)
    tgt = graph[uid]
    for req in getattr(tgt, "requires", []):
        prov = _find_provider(req, graph, providers, ctx)
        if not prov:
            prov = _build_from_template(req, graph, templates, ctx)
            if prov is not None:
                graph.add(prov)
        if prov:
            # todo: If found as an existing node-level provides it may be already linked?
            graph.link(uid, prov, EdgeKind.PROVIDES)
            # todo: This should be in the graph ctx layer, any outgoing link of type provides gets added (dynamically?) to the context at the graph layer, we don't want to write the entire locals of each provision into the node itself...
            # auto-register context injector so render sees the new provider
            node = graph[uid]
            key = prov.locals.get('role', req.key)
            logger.debug(f"adding key {key} to {node!r} ctx for provider {prov!r}")
            node.locals[key] = prov.locals
        else:
            return False
    return True

def _find_provider(req, graph, provider_view, ctx):
    for tier in Tier.range_outwards(Tier.NODE):
        for prov in provider_view._get_layer(tier):
            if prov.provides(req) and req.strategy.select(prov, req, ctx):
                return prov
    return None

def _build_from_template(req, graph, template_view, ctx):
    for tier in Tier.range_outwards(Tier.NODE):
        for tpl in template_view._get_layer(tier).values():
            if req.key in tpl.provides:
                cap = tpl.build(ctx)  # returns ProviderCap
                # store in the proper layer so later look-ups see it
                graph.handler_layer(Service.PROVIDER).append(cap)
                return cap
    return None
