import logging

from pydantic import Field, field_validator

from tangl.type_hints import StringMap, Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.entity import Entity
from .handler_registry import HandlerRegistry
from .runtime_object import RuntimeObject
from .context import context_handler

logger = logging.getLogger(__name__)

class RuntimeEffect(RuntimeObject):
    # Similar to a predicate, carries a function that can update the context

    def execute(self, entity: Entity, *, ctx: StringMap):
        ctx_ = ctx or {} | {'self': entity}  # type: StringMap
        if self.structured_expr is not None:
            return self.exec_structured_expr(self.structured_expr, ctx=ctx_)
        elif self.raw_expr is not None:
            return self.exec_raw_expr(self.raw_expr, ctx=ctx_)
        elif self.handler is not None:
            return self.handler(entity, ctx)
        elif self.func is not None:
            return self.func(entity, ctx)
        return None
        # todo: copy direct ctx updates like locals back to locals?

effect_handler = HandlerRegistry(label="effect_handler", default_aggregation_strategy="pipeline")

# Mixin with EffectHandler registry
class HasEffects(Entity):

    effects: list[RuntimeEffect] = Field(default_factory=list)

    @field_validator("effects", mode="before")
    @classmethod
    def _convert_effects(cls, data):
        if data is None:
            return []
        if isinstance(data, list):
            logger.debug(f"convert effects: {data}")
            res = []
            for item in data:
                if isinstance(item, RuntimeEffect):
                    res.append(item)
                elif isinstance(item, str):
                    res.append(RuntimeEffect(raw_expr=item))
                else:
                    raise ValueError(f"Invalid effect: {item}")
            return res
        raise ValueError(f"Invalid effect definition: {data}")

    @effect_handler.register()
    def _execute_effects(self, ctx: StringMap):
        for effect in self.effects:
            ctx = effect.execute(self, ctx=ctx)
        return ctx

    def apply_effects(self, *, ctx: StringMap) -> bool:
        return effect_handler.execute_all(self, ctx=ctx)
