from __future__ import annotations
from typing import Literal, Optional

from pydantic import Field

from ...type_hints import Context
from ...structure import Node, Graph
from ..enums import ServiceKind
from ..handler import Handler
from ..gather import gather_handlers

Expr = str

class EffectHandler(Handler):

    trigger: Optional[Literal["before", "after"]] = "before"
    effects: list[Expr] = Field(default_factory=list)

    def apply_effects(self, caller: Node, ctx: Context):
        self.func(caller, ctx)


def apply_effects(when: Literal["before", "after"], caller, *scopes, ctx: Context):

    for h in gather_handlers(ServiceKind.EFFECTS,  caller,*scopes, ctx=ctx, trigger=when):  # type: EffectHandler
        h.apply_effects(caller, ctx)
