from __future__ import annotations
from enum import IntEnum
from uuid import UUID
from typing import TypeVar, Iterator, Any, Callable, Union, Type, Optional

from pydantic import BaseModel, Field

from tangl.type_hints import StringMap
from .entity import Entity, HasOrder
from .collection import Registry
from .record import Record
from .selection import Selector

##############################
# CALL RECEIPT
##############################

class CallReceipt(Record):
    # Do not serialize
    caller: Entity = None
    args: tuple = None
    kwargs: dict = None
    result: Any = None
    live_ctx: ExecContext = None

    @classmethod
    def gather(cls, *receipts) -> Iterator[Any]:
        return (r.result for r in receipts if r.result is not None)

    @classmethod
    def all_true(cls, *receipts) -> bool:
        return all(cls.gather(*receipts))

    @classmethod
    def first(cls, *receipts) -> Any:
        return next(cls.gather(receipts), None)

    @classmethod
    def last(cls, *receipts) -> Any:
        results = list(cls.gather(receipts))
        if results:
            return results[-1]
        return None


##############################
# BEHAVIOR
##############################

class ExecContext(BaseModel):
    caller: Entity = None
    authorities: list[BehaviorRegistry] = Field(default_factory=list)
    results: list[CallReceipt] = Field(default_factory=list)


ET = TypeVar('ET', bound=Entity)

BehaviorT = Callable[[ET,                         # caller
                      Optional[tuple[Any, ...]],  # args
                      Optional[ExecContext],      # ctx
                      Optional[StringMap]],       # kwargs
                    Any]

class Priority(IntEnum):
    FIRST = 0
    EARLY = 20
    NORMAL = 50
    LATE = 70
    LAST = 100

class Behavior(Entity, HasOrder):
    # do not serialize

    func: BehaviorT
    binding: Union[Type[Entity], Entity] = None

    task: str = None
    priority: int = Priority.NORMAL

    def sort_key(self):
        return self.priority, *super().sort_key()

    wants_exact_caller_kind = False
    caller_kind: Type[Entity] = None  # for selector

    def wants_caller_kind(self, caller: Entity):
        if self.caller_kind is not None:
            if self.wants_exact_caller_kind:
                return caller.__class__ is self.caller_kind
            else:
                return isinstance(caller, self.caller_kind)
        return True

    def get_bound_func(self) -> BehaviorT:
        if self.binding is None:  # static or class inst that accepts func(caller, ...)
            return self.func
        elif isinstance( self.binding, type ) and issubclass(self.binding, Entity):
            return self._bind_cls_func(self.func, self.binding)
        elif isinstance( self.binding, Entity):
            return self._bind_inst_func( self.func, self.binding )

    def __call__(self, caller: ET = None, *args, ctx: ExecContext = None, **kwargs) -> CallReceipt:
        caller = caller or ctx.caller
        func = self.get_bound_func()
        result = func(caller, *args, ctx=ctx, **kwargs)

        return CallReceipt(
            origin = self,
            caller = caller,
            args = args,
            kwargs = kwargs,
            result = result,
            live_ctx = ctx,
        )

##############################
# BEHAVIOR DISPATCH
##############################

class BehaviorRegistry(Registry[Behavior]):
    members: dict[UUID, Behavior] = Field(default_factory=dict)

    def register(self):
        # deco
        def deco(func: Callable, *args, **kwargs):
            self.add(func, *args, **kwargs)
        return deco

    def add(self, item: Callable | Behavior, *args, **kwargs) -> None:
        # need to figure out binding
        if not isinstance( item, Behavior ):
            item = Behavior(func=item, *args, **kwargs)
        super().add(item)

    @staticmethod
    def _call_all(*behaviors,
                  caller: ET = None,
                  ctx: ExecContext = None,
                  args: tuple = None,
                  kwargs: dict = None) -> Iterator[CallReceipt]:
        if ctx is None:
            ctx = ExecContext(caller=caller)
        return (b(caller=caller, ctx=ctx, args=args, kwargs=kwargs) for b in behaviors)

    def call_all(self, s: Selector = None,
                 caller: Entity = None,
                 ctx: ExecContext = None,
                 args: tuple = None,
                 kwargs: dict = None) -> Iterator[CallReceipt]:
        return self.chain_call_all(self, s=s, caller=caller, ctx=ctx, args=args, kwargs=kwargs)

    @classmethod
    def chain_call_all(cls, *registries: BehaviorRegistry,
                       s: Selector = None,
                       caller: Entity = None,
                       ctx: ExecContext = None,
                       args: tuple = None,
                       kwargs: dict = None) -> Iterator[CallReceipt]:
        if ctx is None:
            ctx = ExecContext(caller=caller, authorities=list(registries))
        else:
            for r in registries:
                if r not in ctx.authorities:
                    ctx.authorities.append( r )
        behaviors = cls.chain_find_all(*ctx.authorities, s = s, sort_key=lambda x: x.sort_key())
        return cls._call_all(*behaviors, caller=caller, ctx = ctx, args = args, kwargs = kwargs)

