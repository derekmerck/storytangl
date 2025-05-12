from collections import ChainMap

from ..type_hints import StringMap
from ..tier_view import TierView
from ..enums import Service, Tier
from ..graph import GlobalScope

def gather_context(node, graph, domain) -> StringMap:

    # ---------------------------------------------------------
    # 1. compose view
    ctx_view = TierView.compose(
        service=Service.CONTEXT,
        NODE=node.local_layer(),  # locals dict
        ANCESTORS=ChainMap(*(anc.local_layer()
                             for anc in node.iter_ancestors(graph=graph))),
        GRAPH=graph.local_layer(),
        DOMAIN=domain.local_layer(),
        GLOBAL=GlobalScope.get_instance().local_layer()
    )

    # ---------------------------------------------------------
    # 2. walk tiers inner→outer, merging dicts
    layers = []
    for tier in Tier.range_outwards(Tier.NODE):
        layers.append(ctx_view._get_layer(tier))
    # _earlier_ tiers closer to the origin win
    return ChainMap(*layers)  # plain dict for speed
