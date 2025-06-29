from __future__ import annotations
import logging
from typing import Protocol

from pydantic import Field, field_validator

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.dispatch import HandlerRegistry
from .runtime_object import RuntimeObject
from .context import HasContext

logger = logging.getLogger(__name__)

class RuntimeEffect(RuntimeObject):
    # Similar to a predicate, carries a function that can update the context

    def execute(self, entity: Entity, *, ctx: StringMap):
        if self.structured_expr is not None:
            return self.exec_structured_expr(self.structured_expr, ctx=ctx)
        elif self.raw_expr is not None:
            return self.exec_raw_expr(self.raw_expr, ctx=ctx)
        elif self.handler is not None:
            return self.handler(entity, ctx)
        elif self.func is not None:
            return self.func(entity, ctx)
        return None
        # todo: copy direct ctx updates like locals back to locals?

on_apply_effects = HandlerRegistry(label="apply_effects", aggregation_strategy="pipeline")
"""
The global pipeline for effects. Handlers for applying effects
should decorate methods with ``@on_apply_effects.register(...)``.
"""
class EffectManager:

    def apply_effects(self, entity: HasEffects, ctx: StringMap = None) -> StringMap:
        return entity.apply_effects(ctx=ctx)


# Mixin with EffectHandler registry
class HasEffects(HasContext):
    """
    A handler class for managing and applying effect strategies for Entities.
    Provides functionality to execute effects using dynamic namespaces.

    KeyFeatures:
      - `apply_effects(entity)`: Applies effects attached to entity
    """

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
                elif isinstance(item, dict):
                    res.append(RuntimeEffect(**item))
                elif isinstance(item, str):
                    res.append(RuntimeEffect(raw_expr=item))
                else:
                    raise ValueError(f"Invalid effect: {item}")
            return res
        raise ValueError(f"Invalid effect definition: {data}")

    @on_apply_effects.register()
    def _execute_effects(self, *, ctx: StringMap) -> StringMap:
        for effect in self.effects:
            ctx = effect.execute(self, ctx=ctx)
        return ctx

    def apply_effects(self, ctx: StringMap = None) -> StringMap:
        ctx = ctx or self.gather_context()
        return on_apply_effects.execute_all_for(self, ctx=ctx)
