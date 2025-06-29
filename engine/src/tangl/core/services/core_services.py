from collections import namedtuple
from dataclasses import dataclass, field

from tangl.core.entity.graph import GraphManager
from .context import ContextManager
from .predicate import PredicateManager
from .rendering import RenderManager
from .effect import EffectManager

# Bundle of interface contracts between core logic and integrated component

@dataclass
class CoreServices:
    graph   : GraphManager = field(default_factory=GraphManager)
    ctx     : ContextManager = field(default_factory=ContextManager)
    pred    : PredicateManager = field(default_factory=PredicateManager)
    effect  : EffectManager = field(default_factory=EffectManager)
    render  : RenderManager = field(default_factory=RenderManager)
