from typing import Mapping, Any
from collections import ChainMap

from ..type_hints import StringMap
from ..enums import CoreScope, Phase
from ..graph import Node, Graph
from ..runtime import HandlerCache
from ..tier_view import TierView

# ---------------------------------------------------------------------------
# tier_owner helper
# ---------------------------------------------------------------------------
def tier_owner(node: Node, graph: Graph, CoreScope: CoreScope) -> Any:
    """
    Return the *object that owns capabilities* for a given CoreScope with respect
    to `node` & `graph`.

    * NODE      → the node itself
    * GRAPH     → the enclosing graph
    * DOMAIN    → graph.domain  (may be None)
    * GLOBAL    → a process‑wide singleton `globals()` dict stub

    CoreScope.ANCESTORS is handled separately by gather().
    """
    match CoreScope:
        case CoreScope.NODE:
            return node
        case CoreScope.GRAPH:
            return graph
        case CoreScope.DOMAIN:
            return getattr(graph, "domain", None)
        case CoreScope.GLOBAL:
            # Could point at a real singleton registry; for tests an empty dict works
            return getattr(graph, "globals_layer", {})
        case _ if CoreScope in CoreScope:
            # Could grab something out of the args or point at a singleton registry; for tests an empty dict works
            return {}

    raise ValueError(f"Unsupported CoreScope {CoreScope}")

def gather(node: Node, graph: Graph, cap_cache: HandlerCache, globals: Mapping) -> StringMap:
    res = TierView()
    res.inject(CoreScope.GLOBAL, globals)
    for CoreScope in CoreScope:
        layers = []
        if CoreScope is CoreScope.ANCESTORS:
            owners = list(node.iter_ancestors(graph=graph))
            effective_tier = CoreScope.NODE  # ancestor providers live at NODE CoreScope
        else:
            owners = [tier_owner(node, graph, CoreScope)]
            effective_tier = CoreScope

        for owner in owners:
            for cap in cap_cache.iter_phase(Phase.GATHER, effective_tier):
                if cap.should_run(globals) and cap.owner_uid == owner.uid:
                    layers.append(cap.apply(owner, None, graph, globals))

        res.inject(CoreScope, ChainMap(*layers))

    return res  # Apparently not reversed here
