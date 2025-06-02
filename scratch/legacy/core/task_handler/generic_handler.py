from __future__ import annotations
from typing import ClassVar, Type, Literal
from typing import Callable, Any
from uuid import UUID
from collections import defaultdict, ChainMap

from pydantic import BaseModel

POST_PROCESSORS = Literal['all', 'any', 'first', 'last', 'flatten', 'iterator', 'pipeline']
StrategyFunc = Callable
DomaidId = str

class StrategyRegistry(defaultdict[str, set[StrategyFunc]], Singleton):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_factory', set)
        super().__init__(*args, **kwargs)

    def register(self, name: str, priority: int) -> StrategyFunc:

        def annotate_and_add_strategy(func: StrategyFunc) -> Callable[[], Any]:
            setattr(func, "task_priority", priority)
            self[name].add(func)
            return func

        return annotate_and_add_strategy

    def __getitem__(self, key: str, default = None) -> list[Callable]:
        if key in self:
            value = sorted( self[key], key=lambda func: func.task_priority )
            return value
        return default

strategies = StrategyRegistry()

class GenericHandler:

    @classmethod
    def get_strategies_from_mro(cls, task_name: str, obj_cls: Type[Entity]) -> list[StrategyFunc]:
        ...

    @classmethod
    def get_strategies_from_registries(cls, task_name: str, *registries: StrategyRegistry):
        result = []
        for registry in registries:
            result.extend(registry.get(task_name, []))
        return result

    @classmethod
    def gather_strategies(cls, task_name: str, obj_cls: type[Entity], strategy_domains: list[DomaidId] = None) -> list[Callable]:
        result = set()
        result.union(cls.get_strategies_from_mro(task_name, obj_cls))
        # todo: include any domain registries associated with this entity, entity.get_domain_strategies()?
        result.union(cls.get_strategies_from_registries(task_name, strategies))
        return sorted(result, key=lambda func: func.task_priority)

    @classmethod
    def do_task(cls, task_name: str, entity: Entity, post_processor: POST_PROCESSORS = None, **kwargs) -> Any:
        funcs = cls.gather_strategies(task_name, type(entity))
        results = []
        for func in funcs:
            result = func(entity, **kwargs)
            if result is None:
                continue
            match post_processor:
                case 'all' if not result:
                    return False
                case 'any' if result:
                    return True
                case 'first':
                    return result
            results.append(result)
            if post_processor == 'pipeline':
                kwargs['pipe'] = result

        match post_processor:
            case "all" if results:
                return True   # make sure there is at least one entry
            case "any":
                return False  # would have returned true if any passed
            case "last" | "pipeline":
                return results[-1]
            case "flatten":
                if all( [isinstance(x, set) for x in results] ):
                    return { xx for x in results for xx in x }
                elif all( [isinstance(x, list) for x in results] ):
                    return [ xx for x in results for xx in x ]
                elif all( [isinstance(x, dict) for x in results] ):
                    return ChainMap(*reversed(results))

        # default is return all entries
        return results

class GetIdentifiersHandler(GenericHandler):

    @classmethod
    def do_get_identifiers(cls, inst: Entity, **kwargs) -> set[str | UUID]:
        return super().do_task("get_identifiers", inst, processor="flatten", **kwargs)

class MyTaskHandler(GenericHandler):

    @classmethod
    def do_my_task(cls, inst: Entity, **kwargs) -> Any:
        return super().do_task('my_task', inst, processor="first", **kwargs)

def task_priority(value: int) -> Callable:
    def set_task_priority(func: Callable) -> Callable:
        setattr(func, 'task_priority', value)
        return func

    return set_task_priority

class Entity(BaseModel):
    uid: UUID

    get_identifiers_handler: ClassVar[Type[GetIdentifiersHandler]] = GetIdentifiersHandler
    my_task_handler: ClassVar[Type[MyTaskHandler]] = MyTaskHandler  # MyTask will return True

    @task_priority(0)
    def _my_task_return_true(self, **kwargs) -> bool:
        return True

    @task_priority(10)
    def _my_task_return_false(self, **kwargs) -> bool:
        return False

    def _get_identifiers(self) -> set[str | UUID]:
        return {self.uid}


class MyOtherTaskHandler(GenericHandler):

    @classmethod
    def do_my_task(cls, self: Entity, **kwargs) -> Any:
        return super().do_task('my_task', self, processor="last", **kwargs)


class NamedEntity(Entity):
    label: str

    my_task_handler: ClassVar = MyOtherTaskHandler  # my_task() will return False

    def _get_identifiers(self) -> set[str | UUID]:  # identifiers will return uid and label
        return {self.label}


