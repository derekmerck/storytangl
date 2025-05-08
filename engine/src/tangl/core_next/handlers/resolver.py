import logging

from ..enums import Tier
from ..provision import Requirement
from .task_handler import HandlerRegistry

logger = logging.getLogger(__name__)

class Resolver:

    @classmethod
    def new_resolve(cls, req: Requirement, scope_tier: Tier, reg: 'ProvisionRegistry'):
        for tier in Tier.range_inwards(scope_tier):  # NODE → … → GLOBAL
            for prov in reg.providers(req.key, tier.value):
                if prov.predicate(ctx) and req.strategy.select(prov, req):
                    return prov
        # none found → create via strategy
        new_prov = req.strategy.create(req, ctx)
        reg.add(new_prov)
        return new_prov


    link_pipeline = HandlerRegistry(label='on_link')

    @classmethod
    def resolve(cls, node, graph, ctx):
        unresolved = []
        for req in node.requires:
            provider = next(req.select_candidates(node, graph, ctx), None)
            if provider is None:
                provider = req.maybe_create(node, graph, ctx)
                logger.debug(f"Created provider {list(provider)}")
                if provider:
                    graph.add(provider)
            if provider:
                cls.link_pipeline.execute_all(entity=node, link=provider, key=req.key, ctx=ctx)
                # call on_link pipeline once
            else:
                unresolved.append(req)
        return not unresolved
