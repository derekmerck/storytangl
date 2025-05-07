from __future__ import annotations
from typing import Callable, Any, Literal, Type, TYPE_CHECKING, Optional

from .entity import Entity
from .registry import Registry

if TYPE_CHECKING:
    from .context_builder import ContextView

class TaskHandler(Callable, Entity):
    func: Callable
    priority: int = 0
    caller_cls: Optional[Type[Entity]] = Entity

    # todo: set defaults caller_cls and label from func fqn

    def __call__(self, *args, entity: Entity, ctx: ContextView, **kwargs):
        if not isinstance(entity, self.caller_cls):
            raise TypeError(f"{entity} is not a {self.caller_cls.__name__}")
        return self.func(*args, entity=entity, ctx=ctx, **kwargs)

Aggregator = Literal['gather', 'pipeline', 'first', 'all', 'iter']

class HandlerRegistry(Registry):

    aggregator: Aggregator = "gather"

    def register(self, caller_cls: Type[Entity] = None, priority: int = 0):

        def decorator(func: Callable):
            task = TaskHandler(
                func = func,
                caller_cls = caller_cls,
                priority = priority
            )
            self.add(task)
            return task

        return decorator

    def execute_one(self, which: str, *, entity: Entity, ctx: ContextView, **kwargs):
        handler = self.find_one(label=which)
        return handler(entity=entity, ctx=ctx, **kwargs)

    def execute_all(self, *, entity: Entity, ctx: ContextView, aggregator: Aggregator = None, **kwargs) -> Any:

        aggregator = aggregator or self.aggregator

        handlers = list(self.find_all(caller_cls=type(entity)))
        handlers.sort(key=lambda h: h.priority, reverse=True)

        match aggregator:
            # todo: ignore None or len(0) return values, but not False
            case "gather":
                return [h.__call__(entity=entity, ctx=ctx, **kwargs) for h in handlers]
            case "all":
                return all(h.__call__(entity=entity, ctx=ctx, **kwargs) for h in handlers)
            case "iter":
                return all(h.__call__(entity=entity, ctx=ctx, **kwargs) for h in handlers)
            case _:
                raise NotImplementedError(f"{self.strategy} is not implemented")

