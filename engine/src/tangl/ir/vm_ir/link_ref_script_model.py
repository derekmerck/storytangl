from typing import Optional, Self

from pydantic import model_validator

from tangl.type_hints import StringMap, Expr, Tag, Label
from tangl.ir.core_ir import BaseScriptItem

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
