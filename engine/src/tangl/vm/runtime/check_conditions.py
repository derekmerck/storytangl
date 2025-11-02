from __future__ import annotations
from typing import TYPE_CHECKING, Self
import logging
from random import Random

from pydantic import Field

from tangl.type_hints import Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core import Node
from tangl.core.behavior import HasBehaviors
from tangl.vm.dispatch import on_validate, Namespace as NS

if TYPE_CHECKING:
    from tangl.vm.context import Context

logger = logging.getLogger(__name__)

# do we want a separate vm task decorator for 'check conditions' that gets invoked during validation?  Or just register directly with on_validate?
# on_check_conditions = partial(vm_dispatch.register, task="check_conditions")
"""
The global pipeline for testing conditions on an Entity. Handlers for 
testing conditions should decorate methods with ``@on_check_conditions(...)``.
"""

# todo: separate on_gather_exprs, on_runtime_exprs?  Is the gathering the pluggable part?
# todo: highly related to core.predicate model, consider folding together.

class HasConditions(HasBehaviors):

    conditions: list[Expr] = Field(default_factory=list)

    @classmethod
    def _eval_expr(cls, expr: Expr, ns: NS, rand: Random = None):
        if not expr:
            return
        rand = rand or Random()
        result = eval(expr, {'rand': rand, '__builtins__': safe_builtins}, ns)
        logger.debug(f"eval {expr} with {NS} = {result}")
        return result

    @on_validate()
    def check_conditions(self: Self, *, ctx: Context) -> bool | None:
        if not self.conditions:
            return
        ns = ctx.get_ns(self)
        return all([self._eval_expr(expr=expr, ns=ns, rand=ctx.rand) for expr in self.conditions])

    def check_satisfied_by(self: Self, other: Node, *, ctx: Context) -> bool | None:
        if not self.conditions:
            return
        ns = ctx.get_ns(other)
        return all([self._eval_expr(expr=expr, ns=ns, rand=ctx.rand) for expr in self.conditions])
