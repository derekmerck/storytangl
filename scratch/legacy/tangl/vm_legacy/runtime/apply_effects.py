from __future__ import annotations
from typing import TYPE_CHECKING, Any, Self
import logging
from random import random
from functools import partial
from random import Random

from pydantic import Field

from tangl.type_hints import Expr, StringMap
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.graph import Node
from tangl.core.behavior import HasBehaviors
from tangl.vm.dispatch import vm_dispatch, on_update, on_finalize, Namespace as NS
from tangl.story.runtime.effect_helpers import bind_effect_helpers

if TYPE_CHECKING:
    from tangl.vm.context import Context


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# todo: separate on_gather_exprs, on_runtime_exprs?  Is the gathering the pluggable part?
# on_apply_effects = partial(vm_dispatch.register, task="on_update_effects")
# on_apply_final_effects = partial(vm_dispatch.register, task="on_final_effects")
"""
The global pipeline for applying effects carried by an Entity. Handlers for 
applying effects should decorate methods with ``@on_apply_effects.register(...)``.
"""

class HasEffects(HasBehaviors):
    """
    A handler class for managing and applying effect strategies for Entities.
    Provides functionality to execute effects using dynamic namespaces.

    Tries to inject ctx.rand if available.

    KeyFeatures:
      - `apply_effects(entity)`: Applies effects attached to entity
    """

    entry_effects: list[Expr] = Field(default_factory=list, alias="effects")
    final_effects: list[Expr] = Field(default_factory=list)

    @classmethod
    def _update_locals(cls, entity: Node, updated_context: dict = None):
        # Updates to entity.locals may need to be handled explicitly
        entity_locals = list(entity.locals.keys())
        for k in entity_locals:
            logger.debug(f"checking local: {k}, {entity.locals[k]}=={updated_context[k]}")
            if k in updated_context and entity.locals[k] != updated_context[k]:
                entity.locals[k] = updated_context[k]

    @classmethod
    def _exec_expr(cls, expr: Expr, ns: NS, rand: Random = None) -> StringMap:
        """
        Execute an effect expression within the given namespace.

        :param expr: The effect expression to be executed.
        :param ns: Namespace mapping containing variables used in the expression.
        :return dict: StringMap with updated context
        """
        rand = rand or Random()
        if not expr:
            return
        logger.debug(f"exec {expr} with {ns}")
        builtins = {**safe_builtins, **bind_effect_helpers(graph=ns.get("graph"))}
        try:
            exec(expr, {'rand': rand, '__builtins__': builtins}, ns)
        except (SyntaxError, TypeError, KeyError, AttributeError, NameError):
            logger.critical(f"Failed to apply expr: '{expr}'")
            raise
        return ns

    @on_update()
    def apply_entry_effects(self: Self, *, ctx: Context) -> None:
        if not self.entry_effects:
            return
        ns = ctx.get_ns(self)
        rand = getattr(ctx, "rand", Random())
        for effect in self.entry_effects:
            self._exec_expr(expr=effect, ns=ns, rand=rand)
        # self._update_locals(self, ns)

    @on_finalize()
    def apply_final_effects(self: Self, *, ctx: Context) -> None:
        if not self.final_effects:
            return
        ns = ctx.get_ns(self)
        rand = getattr(ctx, "rand", Random())
        for effect in self.final_effects:
            self._exec_expr(expr=effect, ns=ns, rand=rand)
        # self._update_locals(self, ns)

    def apply_effects_to(self, other: Node, *, ctx: Context) -> bool:
        if not self.entry_effects:
            return
        ns = ctx.get_ns(other)
        rand = getattr(ctx, "rand", Random())
        for effect in self.entry_effects:
            self._exec_expr(expr=effect, ns=ns, rand=rand)
        # self._update_locals(other, ns)
