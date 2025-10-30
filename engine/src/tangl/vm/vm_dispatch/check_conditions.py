from __future__ import annotations
from typing import Self, TYPE_CHECKING

from pydantic import Field

from tangl.type_hints import Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.dispatch import HasBehaviors
from .vm_dispatch import on_validate

if TYPE_CHECKING:
    from tangl.vm.context import Context, NS

class HasConditions(HasBehaviors):

    conditions: list[Expr] = Field(default_factory=list)

    @classmethod
    def _eval_expr(cls, expr: Expr, ns: NS):
        return eval(expr, safe_builtins, ns)

    @on_validate()
    def _check_conditions(self: Self, *, ctx: Context) -> bool | None:
        if not self.conditions:
            return
        ns = ctx.get_ns()
        return all([self._eval_expr(expr=expr, ns=ns) for expr in self.conditions])
