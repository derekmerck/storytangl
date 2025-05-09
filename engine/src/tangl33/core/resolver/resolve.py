from typing import TYPE_CHECKING

from ..enums import Tier
from ..requirement import Requirement
from ..graph import Node, Graph, Edge, EdgeKind
from ..provision import ResourceProvider
from ..runtime import ProviderRegistry, HandlerCache
from ..type_hints import Context

def resolve(node: Node, graph: Graph, reg: ProviderRegistry, cache: HandlerCache, ctx: Context):

    def _find_or_create(req: Requirement,
                        scope_tier: Tier,
                        reg: ProviderRegistry,
                        ctx: Context) -> ResourceProvider | None:
        """Return an existing provider that satisfies *req* or create one."""
        # 1. search outward
        for tier in Tier.range_inwards(scope_tier):  # NODE → … → GLOBAL
            for prov in reg.providers(req.key, tier):
                if prov.predicate(ctx) and req.strategy.select(prov, req, ctx):
                    return prov

        # 2. none found → create
        new_prov = req.strategy.create(req, ctx)
        if new_prov is not None:
            reg.add(new_prov)
        return new_prov

    # Search order: node-local, each ancestor, graph, domain, global
    search_chain = [Tier.NODE]                               # 1. node‑local
    search_chain.extend([Tier.ANCESTORS] * len(list(node.iter_ancestors(graph=graph))))  # 2. each ancestor
    search_chain.extend([Tier.GRAPH, Tier.DOMAIN, Tier.GLOBAL])                   # 3‑5

    # Nodes may not have requirements, although structure nodes probably should
    for req in getattr(node, "requires", []):
        # Walk the chain until a provider is found/created
        cap: ResourceProvider | None = None
        for tier in search_chain:
            cap = _find_or_create(req, tier, reg, ctx)
            if cap:
                break
        if cap is None:   # last safeguard – shouldn’t happen if strategy.create() never returns None
            raise RuntimeError(f"Unresolved requirement: {req.key!r}")
        graph.link(node.uid, cap.owner_uid, EdgeKind.PROVIDES)

