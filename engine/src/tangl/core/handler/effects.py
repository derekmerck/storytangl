from pydantic import Field

from tangl.type_hints import StringMap, Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.entity import Entity
from .handler_registry import HandlerRegistry
from .runtime_object import RuntimeObject
from .context import context_handler

class RuntimeEffect(RuntimeObject):
    # Similar to a predicate, carries a function that can update the context

    @classmethod
    def exec_structured_expr(cls, expr: StringMap, *, ctx: StringMap = None):
        raise NotImplementedError("Structured predicate evaluation not yet implemented")

    @classmethod
    def exec_raw_expr(cls, expr: Expr, *, ctx: StringMap = None):
        return exec(expr, safe_builtins, ctx)
        # todo: copy direct ctx updates like locals back to locals?

    def execute(self, entity: Entity, *, ctx: StringMap = None):
        ctx_ = ctx or {} | {'self': entity}  # type: StringMap
        if self.structured_expr is not None:
            return self.exec_structured_expr(self.structured_expr, ctx=ctx_)
        elif self.raw_expr is not None:
            return self.exec_raw_expr(self.raw_expr, ctx=ctx_)
        elif self.handler is not None:
            return self.handler(entity, ctx)
        elif self.func is not None:
            return self.func(entity, ctx)
        return True

effect_handler = HandlerRegistry(default_execute_all_strategy="pipe")

# Mixin with EffectHandler registry
class HasEffects(Entity):

    effects: list[RuntimeEffect] = Field(default_factory=list)

    @effect_handler.register()
    def _execute_effects(self, *, ctx: StringMap):
        for effect in self.effects:
            ctx = effect.execute(self, ctx=ctx)
        return ctx

    def apply_effects(self, *, ctx: StringMap) -> bool:
        ctx = ctx or context_handler.execute_all(self)
        return effect_handler.execute_all(self, ctx=ctx)
