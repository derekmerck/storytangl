from typing import Mapping, Any
from collections import ChainMap

ContextView = Mapping[str, Any]
# Idea is that it is a mapping that is _always_ indexed by variable-friendly strings

TIER_ORDER = ("global","domain","graph","ancestors","node")

class ContextBuilder:
    @classmethod
    def gather(cls, node, graph, *, globals) -> ContextView:
        layers = []

        # global tier ----
        layers.append(globals)

        # domain tier ----
        if graph.domain:
            for p in graph.domain.context_providers:
                if p.phase=='early' and p.predicate(globals):
                    layers.append(p.provide(globals))

        # graph tier -----
        for p in graph.context_providers:
            if p.phase=='early' and p.predicate(globals):
                layers.append(p.provide(globals))

        # todo: not clear when we want to trigger 'parenting' vs. 'linking'
        # # ancestor chain --
        # uid = node.uid
        # while uid and uid in graph.parent_of:
        #     anc = graph.registry[graph.parent_of[uid]]
        #     for p in anc.context_providers:
        #         if p.phase=='early' and p.predicate(globals):
        #             layers.append(p.provide(globals))
        #     uid = graph.parent_of.get(uid)

        # node tier -------
        for p in node.context_providers:
            if p.phase=='early' and p.predicate(globals):
                layers.append(p.provide(globals))

        return ChainMap(*reversed(layers))   # deepest node last
