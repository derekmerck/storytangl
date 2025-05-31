from tangl.type_hints import StringMap, Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.entity import Entity
from .handler_registry import HandlerRegistry
from .runtime_object import RuntimeObject
from .context import context_handler

class Predicate(RuntimeObject):

    @classmethod
    def eval_structured_expr(cls, expr: StringMap, *, ctx: StringMap = None):
        raise NotImplementedError("Structured predicate evaluation not yet implemented")

    @classmethod
    def eval_raw_expr(cls, expr: Expr, *, ctx: StringMap = None):
        return eval(expr, safe_builtins, ctx)

    def evaluate(self, entity: Entity, *, ctx: StringMap = None):
        ctx_ = ctx or {} | {'self': entity}  # type: StringMap
        if self.structured_expr is not None:
            return self.eval_structured_expr(self.structured_expr, ctx=ctx_)
        elif self.raw_expr is not None:
            return self.eval_raw_expr(self.raw_expr, ctx=ctx_)
        elif self.handler is not None:
            return self.handler(entity, ctx)
        elif self.func is not None:
            return self.func(entity, ctx)
        return True

availability_handler = HandlerRegistry(default_execute_all_strategy="all_true")

class Satisfiable(Entity):

    predicate: Predicate = None

    @availability_handler.register()
    def _check_my_predicate(self, *, ctx: StringMap = None) -> bool:
        if self.predicate is not None:
            return self.predicate.evaluate(self, ctx=ctx)
        return True

    def is_satisfied(self, ctx: StringMap = None) -> bool:
        ctx = ctx or context_handler.execute_all(self)
        return availability_handler.execute_all(self, ctx=ctx)
