from __future__ import annotations
from typing import Self, TYPE_CHECKING
from functools import partial

from pydantic import Field

from tangl.type_hints import Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.behavior import HasBehaviors
from tangl.vm.frame import ResolutionPhase as P
from .vm_dispatch import vm_dispatch

if TYPE_CHECKING:
    from tangl.vm.context import Context, NS

on_update = partial(vm_dispatch.register, task=P.UPDATE)
on_finalize = partial(vm_dispatch.register, task=P.FINALIZE)


@on_update()
def update_noop(*args, **kwargs):
    pass

@on_finalize()
def finalize_noop(*args, **kwargs):
    # collapse-to-patch can go here later
    pass

class HasEffects(HasBehaviors):

    entry_effects: list[Expr] = Field(default_factory=list, alias="effects")
    final_effects: list[Expr] = Field(default_factory=list)

    @classmethod
    def _exec_expr(cls, expr: Expr, ns: NS):
        exec(expr, safe_builtins, ns)

    @on_update()
    def _apply_entry_effects(self: Self, *, ctx: Context) -> None:
        if not self.entry_effects:
            return
        ns = ctx.get_ns()
        for effect in self.entry_effects:
            self._exec_expr(expr=effect, ns=ns)

    @on_finalize()
    def _apply_final_effects(self: Self, *, ctx: Context) -> None:
        if not self.final_effects:
            return
        ns = ctx.get_ns()
        for effect in self.final_effects:
            self._exec_expr(expr=effect, ns=ns)
