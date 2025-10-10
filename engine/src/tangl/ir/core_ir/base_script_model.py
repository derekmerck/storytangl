from typing import Optional, Any
import functools

from pydantic import BaseModel, Field, ConfigDict

from tangl.type_hints import Label, StringMap, ClassName, Tag, Expr

class BaseScriptItem(BaseModel):
    """
    Basic intermedia representation model for describing any Entity-type object.

    Includes obj_cls, label, tags, locked, locals, conditions, effects, content, and icon
    """
    model_config = ConfigDict(frozen=True)   # Once a script is created, it should be immutable

    obj_cls: Optional[ClassName] = None      # For structuring/unstructuring
    template_names: Optional[Label] = Field(None, alias='templates')

    label: Optional[Label] = None            # May derive from key
    tags: Optional[set[Tag]] = None          # Iterable of strings

    locked: bool = False                     # Requires manual unlocking

    locals: Optional[StringMap] = None       # Namespace

    conditions: Optional[list[Expr]] = Field(
        None,
        description="Conditions that this item should satisfy."
    )
    effects: Optional[list[Expr]] = Field(
        None,
        description="List of effects that this item will apply."
    )

    content: Optional[str] = None           # Rendered content fields
    icon: Optional[str] = None

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(**kwargs)
        return res

