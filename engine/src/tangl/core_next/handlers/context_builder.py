from __future__ import annotations
from typing import Mapping, Any
from collections import ChainMap

from ..type_hints import Context
from ..enums import Tier, StepPhase
from ..provision import CapabilityCache

def gather(node, graph, *, cap_cache: CapabilityCache, globals: Mapping[str, Any]) -> Context:
    """
    Build a read-only ChainMap for the current cursor step.

    Order:  global ◀ domain ◀ graph ◀ ancestors ◀ node
            (earlier layers win on key collision)
    """
    layers: list[Mapping[str, Any]] = [globals]         # global tier first

    # ---- walk tiers outer ➜ inner -------------------------------
    for tier in Tier:                                    # Enum iteration is ordered
        # Ancestor tier needs special handling – walk the chain
        if tier is Tier.ANCESTORS:
            for anc in node.iter_ancestors(graph=graph):
                _run_caps_for_owner(anc, tier, layers, globals, cap_cache)
        else:
            owner = {
                Tier.GLOBAL: graph.domain.globals,
                Tier.DOMAIN: graph.domain,
                Tier.GRAPH:  graph,
                Tier.NODE:   node,
            }[tier]
            _run_caps_for_owner(owner, tier, layers, globals, cap_cache)

    return ChainMap(*reversed(layers))                   # deepest last


# -----------------------------------------------------------------
# helpers
# -----------------------------------------------------------------
def _run_caps_for_owner(owner, tier: Tier,
                        layers: list[Mapping[str, Any]],
                        globals_layer: Mapping[str, Any],
                        cap_cache: CapabilityCache):
    """
    Push context-provider capabilities from *owner*’s tier into *layers*.
    """
    phase = StepPhase.GATHER_CONTEXT
    for cap in cap_cache.iter_phase(phase, tier):
        # Providers declare their tier explicitly; skip those whose *owner* mismatches.
        if cap.should_run(globals_layer) and getattr(cap, "owner", None) is owner:
            layer = cap.apply(owner, None, None, globals_layer)   # driver & graph unused
            if layer:                                             # allow None
                layers.append(layer)

