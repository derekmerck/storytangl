from __future__ import annotations

from pydantic import Field

from ...entity import Context
from ..handler import HasHandlers

Expr = str

class HasEffects(HasHandlers):

    effects: list[Expr] = Field(default_factory=list)

    def apply_effects(self, ctx: Context):
        ...

    def gather_handlers(self):
        return EffectHandler(self._apply_effects)