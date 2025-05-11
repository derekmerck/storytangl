from typing import Mapping, Any
from collections import ChainMap

from ..type_hints import StringMap
from ..enums import Tier, Phase
from ..graph import Node, Graph
from ..runtime import HandlerCache
from ..tiered_map import TieredMap

# ---------------------------------------------------------------------------
# tier_owner helper
# ---------------------------------------------------------------------------
def tier_owner(node: Node, graph: Graph, tier: Tier) -> Any:
    """
    Return the *object that owns capabilities* for a given tier with respect
    to `node` & `graph`.

    * NODE      → the node itself
    * GRAPH     → the enclosing graph
    * DOMAIN    → graph.domain  (may be None)
    * GLOBAL    → a process‑wide singleton `globals()` dict stub

    Tier.ANCESTORS is handled separately by gather().
    """
    match tier:
        case Tier.NODE:
            return node
        case Tier.GRAPH:
            return graph
        case Tier.DOMAIN:
            return getattr(graph, "domain", None)
        case Tier.GLOBAL:
            # Could point at a real singleton registry; for tests an empty dict works
            return getattr(graph, "globals_layer", {})
        case _ if tier in Tier:
            # Could grab something out of the args or point at a singleton registry; for tests an empty dict works
            return {}

    raise ValueError(f"Unsupported tier {tier}")

def gather(node: Node, graph: Graph, cap_cache: HandlerCache, globals: Mapping) -> StringMap:
    res = TieredMap()
    res.inject(Tier.GLOBAL, globals)
    for tier in Tier:
        layers = []
        if tier is Tier.ANCESTORS:
            owners = list(node.iter_ancestors(graph=graph))
            effective_tier = Tier.NODE  # ancestor providers live at NODE tier
        else:
            owners = [tier_owner(node, graph, tier)]
            effective_tier = tier

        for owner in owners:
            for cap in cap_cache.iter_phase(Phase.GATHER, effective_tier):
                if cap.should_run(globals) and cap.owner_uid == owner.uid:
                    layers.append(cap.apply(owner, None, graph, globals))

        res.inject(tier, ChainMap(*layers))

    return res  # Apparently not reversed here
