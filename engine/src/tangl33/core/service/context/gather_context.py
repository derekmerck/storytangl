from collections import ChainMap

from ...type_hints import StringMap
from ...tier_view import TierView
from ...enums import CoreService, CoreScope
from ...scope import GlobalScope

def gather_context(node, graph, domain) -> StringMap:

    # ---------------------------------------------------------
    # 1. compose view
    ctx_view = TierView.compose(
        service=CoreService.CONTEXT,
        NODE=node.local_layer(),  # locals dict
        ANCESTORS=ChainMap(*(anc.local_layer()
                             for anc in node.iter_ancestors(graph=graph))),
        GRAPH=graph.local_layer(),
        DOMAIN=domain.local_layer(),
        GLOBAL=GlobalScope.get_instance().local_layer()
    )

    # todo: There is no particular reason to re-write the ctx-view like below, I think?
    return ctx_view

    # ---------------------------------------------------------
    # 2. walk tiers inner→outer, merging dicts
    layers = []
    for CoreScope in CoreScope.range_outwards(CoreScope.NODE):
        # todo: I feel like we should use context_caps here and update the base ctx.
        #       Originally not done with a cap b/c of bootstrapping, but now ctx is independent of handlers
        layers.append(ctx_view._get_layer(CoreScope))
    # _earlier_ tiers closer to the origin win
    return ChainMap(*layers)  # plain dict for speed
