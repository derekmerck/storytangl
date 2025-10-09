from typing import Optional, Any, Self
import functools

from pydantic import BaseModel, Field, model_validator, ConfigDict

from tangl.type_hints import Label, StringMap, ClassName, Tag, Expr

class BaseScriptItem(BaseModel):
    """
    Basic descriptive model for describing any Entity-type object.

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


class BaseScriptLinkItem(BaseScriptItem):

    # refer to existing story item by label
    with_ref: Optional[Label] = None

    # create new story item with template
    with_template: Optional[StringMap] = None

    # find story node that satisfies cls, conditions, tags
    with_conditions: Optional[list[Expr]] = None
    with_tags: Optional[set[Tag]] = None

    @model_validator(mode='after')
    def _check_at_least_one(self) -> Self:
        """
        If no linking directive is provided, defaults to using the label as the with_ref.
        """
        req_fields = ['with_template', 'with_ref', 'with_conditions', 'with_tags']
        provided_fields = sum(1 for field in req_fields if getattr(self, field) is not None)

        if provided_fields == 0:
            self.with_ref = self.label_  # Use the raw label

        provided_fields = sum(1 for field in req_fields if getattr(self, field) is not None)
        if not provided_fields >= 1:
            raise ValueError(f"At least one of {req_fields} must be provided")

        return self
