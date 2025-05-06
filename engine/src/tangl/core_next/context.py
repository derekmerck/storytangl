from typing import Mapping, Any
from collections import ChainMap

from .task_handler import TaskRegistry as HandlerPipeline, TaskRegistry

ContextView = Mapping[str, Any]

class ContextBuilder:
    pipeline = HandlerPipeline(label='on_gather_context')   # hookable

    @classmethod
    def gather(cls, node, graph, *, globals) -> ContextView:
        base_layer = {"node": node, "graph": graph, **globals}
        ctx_layers: list[dict] = cls.pipeline.execute_all(entity=node, ctx=base_layer)
        return ChainMap(*ctx_layers, node.locals, graph.locals, globals)
