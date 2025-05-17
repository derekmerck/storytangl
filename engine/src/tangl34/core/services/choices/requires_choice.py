from typing import Literal

from ...entity import Context

def requires_choice(when: Literal["before", "after"] = None, *scopes, ctx: Context):
    ...
