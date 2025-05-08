from typing import Mapping
from collections import ChainMap

from ..type_hints import Context
from ..enums import Tier, Phase
from ..graph import Node, Graph
from ..runtime import CapabilityCache

def gather(node: Node, graph: Graph, cap_cache: CapabilityCache, globals: Mapping) -> Context:
    layers = [globals]
    for tier in Tier:
        owners = (
            node.iter_ancestors(graph) if tier is Tier.ANCESTORS
            else [tier_owner(node, graph, tier)]
        )
        for owner in owners:
            for cap in cap_cache.iter_phase(Phase.GATHER_CONTEXT, tier):
                if cap.should_run(globals) and cap.owner_uid == owner.uid:
                    layers.append(cap.apply(owner, None, graph, globals))
    return ChainMap(*reversed(layers))
