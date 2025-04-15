from __future__ import annotations
from typing import Any, Optional, Self, Mapping
import logging
from random import random

from tangl.type_hints import Expr, StringMap
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.graph import Node
from tangl.core.handlers import TaskPipeline, PipelineStrategy
from .has_context import HasContext

logger = logging.getLogger(__name__)

# todo: separate on_gather_exprs, on_runtime_exprs?  Is the gathering the pluggable part?

on_apply_effects = TaskPipeline[HasContext, Any](
    label="on_apply_effects",
    pipeline_strategy=PipelineStrategy.GATHER)
"""
The global pipeline for applying effects carried by an Entity. Handlers for 
applying effects should decorate methods with ``@on_apply_effects.register(...)``.
"""

class HasEffects(HasContext):
    """
    A handler class for managing and applying effect strategies for Entities.
    Provides functionality to execute effects using dynamic namespaces.

    KeyFeatures:
      - `apply_effects(entity)`: Applies effects attached to entity
    """
    effects: list[Expr] = None

    @classmethod
    def exec_expr(cls, expr: Expr, **context) -> StringMap:
        """
        Execute an effect expression within the given namespace.

        :param expr: The effect expression to be executed.
        :param context: A dict of variables to be used in the expression.
        :return dict: StringMap with updated context
        """
        if not expr:
            return
        logger.debug(f"exec {expr} with {context}")
        try:
            exec( expr, {'random': random, '__builtins__': safe_builtins}, context )
        except (SyntaxError, TypeError, KeyError, AttributeError, NameError):
            logger.critical(f"Failed to apply expr: '{expr}'")
            raise
        return context

    @classmethod
    def apply_all_effects(cls, effects: list[Expr], **context) -> StringMap:
        for e in effects:
            context = cls.exec_expr(e, **context)
        return context

    @on_apply_effects.register()
    def _apply_my_effects(self, **context):
        return self.apply_all_effects(self.effects, **context)

    @classmethod
    def _update_locals(cls, entity: Self, updated_context: dict = None):
        # Updates to entity.locals need to be handled explicitly
        entity_locals = list(entity.locals.keys())
        for k in entity_locals:
            logger.debug(f"checking local: {k}, {entity.locals[k]}=={updated_context[k]}")
            if k in updated_context and entity.locals[k] != updated_context[k]:
                entity.locals[k] = updated_context[k]

    def apply_effects(self, **context) -> bool:
        context = context or self.gather_context()
        updated_context = on_apply_effects.execute(self, **context)
        self._update_locals(self, updated_context)
        return True

    def apply_effects_to(self, entity: Self) -> bool:
        context = entity.gather_context()
        updated_context = on_apply_effects.execute(self, **context)
        self._update_locals(entity, updated_context)
        return True
