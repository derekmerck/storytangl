from __future__ import annotations
from typing import Self, TYPE_CHECKING
from functools import partial

from pydantic import Field

from tangl.type_hints import Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core import Node
from tangl.core.behavior import HasBehaviors, HandlerPriority as Prio
from tangl.vm.resolution_phase import ResolutionPhase as P
from .vm_dispatch import vm_dispatch

on_validate = partial(vm_dispatch.register, task=P.VALIDATE)

if TYPE_CHECKING:
    from tangl.vm.context import Context, NS

@on_validate(priority=Prio.EARLY)
def validate_cursor(caller: Node, **kwargs):
    """Basic validation: cursor exists and is a :class:`~tangl.core.graph.Node`."""
    ok = caller is not None and isinstance(caller, Node)
    return ok


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
