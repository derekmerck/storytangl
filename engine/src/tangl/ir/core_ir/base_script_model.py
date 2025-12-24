from __future__ import annotations
from typing import Any, Optional

from pydantic import Field, model_validator

from tangl.core.factory import HierarchicalTemplate
from tangl.type_hints import Expr, Label, StringMap


class BaseScriptItem(HierarchicalTemplate):
    """core.factory.HierarchicalTemplate with some added conveniences."""

    # todo: I think this is out of spec now -- templates are just actor scripts, location scripts, block scripts, etc.
    template_names: Optional[Label] = None

    # todo: we haven't implemented this on story-node yet have we?
    locked: bool = False                      # Requires manual unlocking
    locals: Optional[StringMap] = None        # Namespace
    conditions: Optional[list[Expr]] = Field(
        None,
        description="Conditions that this item should satisfy."
    )
    effects: Optional[list[Expr]] = Field(
        None,
        description="List of effects that this item will apply."
    )

    content: Optional[str] = None   # Renderable content
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _lift_template_name_aliases(cls, data: Any) -> Any:
        """Preserve legacy ``templates`` aliases for template name references."""

        if not isinstance(data, dict):
            return data

        templates_value = data.get("templates")
        if templates_value is None:
            return data

        if isinstance(templates_value, dict):
            return data

        updated = dict(data)
        updated.setdefault("template_names", templates_value)
        updated.pop("templates", None)
        return updated
