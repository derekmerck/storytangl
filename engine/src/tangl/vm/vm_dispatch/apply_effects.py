from __future__ import annotations
from typing import Self, TYPE_CHECKING

from pydantic import Field

from tangl.type_hints import Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.dispatch import HasBehaviors
from .vm_dispatch import on_update

if TYPE_CHECKING:
    from tangl.vm.context import Context, NS

class HasEffects(HasBehaviors):

    effects: list[Expr] = Field(default_factory=list)

    @classmethod
    def _exec_expr(cls, expr: Expr, ns: NS):
        exec(expr, safe_builtins, ns)

    @on_update()
    def _apply_effects(self: Self, *, ctx: Context) -> None:
        if not self.effects:
            return
        ns = ctx.get_ns()
        for effect in self.effects:
            self._exec_expr(expr=effect, ns=ns)
