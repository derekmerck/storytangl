# Note, this subpackage has lots of interdependencies and requires careful
# import ordering.

from .entity import Entity

# deps entity only
from .registry import Registry
from .fragment import ContentFragment, ControlFragment, GroupFragment, KvFragment, PresentationHints
from .task_handler import TaskHandler, HandlerPriority

# deps registry
from .singleton import Singleton, InheritingSingleton
from .graph import Node, Graph, SingletonNode, Edge, DynamicEdge

# deps singleton, task_handler, registry
from .handler_pipeline import PipelineStrategy, HandlerPipeline, HandlerRegistry
from .data_resources import ResourceDataType, ResourceInventoryTag, ResourceRegistry
from .entity_handlers import HasContext, on_gather_context, HasConditions, on_check_conditions, HasEffects, on_apply_effects, Renderable, on_render, Available, on_avail  # deps task_handler

# deps graph, entity_handlers, singleton, task_handler, registry
from .graph_handlers import Associating, on_associate, on_disassociate, on_can_associate, on_can_disassociate, TraversableGraph, TraversableEdge, TraversableNode, on_enter, HasScopedContext
