from __future__ import annotations
from typing import Literal, Optional
import random
import logging

from tangl.utils.safe_builtins import safe_builtins
from ..type_hints import Expr, StringMap
from .enums import ServiceKind
from .base import handler, HasHandlers

logger = logging.getLogger(__name__)

class HasEffects(HasHandlers):
    """
    A handler class for managing and applying effect strategies for Entities.
    Provides functionality to execute effects using dynamic namespaces.

    KeyFeatures:
      - `apply_effects(entity)`: Applies effects attached to entity
    """
    effects: list[Expr] = None

    @classmethod
    def exec_expr(cls, expr: Expr, *, ctx) -> StringMap:
        """
        Execute an effect expression within the given namespace.

        :param expr: The effect expression to be executed.
        :param ctx: A dict of local variables to be used in the expression.
        :return dict: StringMap with updated context
        """
        if not expr:
            return
        logger.debug(f"exec {expr} with {ctx}")
        try:
            exec( expr, {'random': random, '__builtins__': safe_builtins}, ctx )
        except (SyntaxError, TypeError, KeyError, AttributeError, NameError):
            logger.critical(f"Failed to apply expr: '{expr}'")
            raise
        return ctx

    @handler(ServiceKind.EFFECT)
    def _apply_my_effects(self, caller, ctx):
        for expr in self.effects:
            self.exec_expr(expr, ctx=ctx)

    @staticmethod
    def effect_handler(priority=10, caller_criteria=None):
        return handler(ServiceKind.EFFECT, priority=priority, caller_criteria=caller_criteria)

    @classmethod
    def apply_effects(cls, trigger: Literal["before", "after"], caller, *objects, ctx):
        # If you want to apply caller's effects on another object/scope, provide a different context
        logger.debug("applying effects")
        # todo: gather handlers should take a criteria filter?  Or put phase into the ctx and add a predicate for it?
        for h in cls.gather_handlers(ServiceKind.EFFECT, caller, *objects, ctx=ctx):
            logger.debug(f"Calling: {h!r}")
            h.func(caller, ctx)
