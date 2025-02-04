from __future__ import annotations
from typing import Optional, Self, Any

from tangl.core.graph import Node, Edge
from tangl.core.entity.handlers import HasContext, Renderable, on_render, HasEffects, on_apply_effects
from tangl.core.task_handler import TaskHandler, TaskPipeline, HandlerPriority, PipelineStrategy

class Associating:
    ...
