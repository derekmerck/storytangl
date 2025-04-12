from typing import Optional, Any
import functools

from pydantic import BaseModel, Field

from tangl.type_hints import Label, Tags, Locals, ClassName, Strings

class BaseScriptItem(BaseModel, extra='allow' ):

    obj_cls: Optional[ClassName] = None   # For structuring/unstructuring

    label: Optional[Label] = None         # May derive from key
    tags: Optional[Tags] = None           # Iterable of strings

    locked: bool = False        # Requires manual unlocking

    locals: Optional[Locals] = None       # Namespace

    conditions: Optional[Strings] = Field(
        None,
        description="Conditions that must be satisfied for the action to be available."
    )
    effects: Optional[Strings] = Field(
        None,
        description="List of effects that result from the action."
    )

    text: Optional[str] = None           # Rendered fields
    icon: Optional[str] = None

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(**kwargs)
        return res
