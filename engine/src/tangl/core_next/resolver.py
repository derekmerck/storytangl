import logging

from .task_handler import HandlerRegistry

logger = logging.getLogger(__name__)

class Resolver:
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
