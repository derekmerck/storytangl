from __future__ import annotations
from typing import Optional, Any
from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.graph import Node, Graph
from tangl.core.handlers import TaskPipeline, HandlerPriority, PipelineStrategy

on_init = TaskPipeline[Entity, Any](
    label="on_init",
    pipeline_strategy=PipelineStrategy.GATHER)
"""
The global pipeline for hooking the init process. Handlers for initialization
should decorate methods with ``@on_init.register(...)``.
"""

class InitializationHandler(Entity):

    @on_init.register(caller_cls=Entity)
    def _default_init(self, **context):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "gather_context"):
            context = self.gather_context()
        else:
            context = {}
        on_init.execute(**context)
