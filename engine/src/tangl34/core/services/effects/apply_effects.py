from __future__ import annotations
from typing import Literal, Optional

from pydantic import Field

from .. import Handler
from ...entity import Context
from ..enums import ServiceKind
from ..gather import gather_handlers

Expr = str

class EffectHandler(Handler):

    when: Optional[Literal["before", "after"]] = None
    effects: list[Expr] = Field(default_factory=list)


def apply_effects(when: Literal["before", "after"] = None, *scopes, ctx: Context):

    for h in gather_handlers(ServiceKind.EFFECTS, when=when):
        h.apply_effects(ctx)
