from typing import Optional, Any
import functools

from pydantic import BaseModel, Field, model_validator

from tangl.core import Record
from tangl.type_hints import Label, StringMap, ClassName, Expr

class BaseScriptItem(Record):
    """
    Basic intermedia representation model for describing any Entity-type object.

    Includes obj_cls, label, tags, locked, locals, conditions, effects, content, and icon
    """
    record_type: str = Field("script", alias="type")

    obj_cls: Optional[ClassName] = None      # For structuring/unstructuring
    template_names: Optional[Label] = None

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
        res = BaseModel.model_dump(self, *args, **kwargs)
        res.pop("uid", None)
        res.pop("seq", None)
        obj_cls_value = res.get("obj_cls")
        if isinstance(obj_cls_value, type):
            module = getattr(obj_cls_value, "__module__", "")
            qualname = getattr(obj_cls_value, "__qualname__", obj_cls_value.__name__)
            if module:
                res["obj_cls"] = f"{module}.{qualname}"
            else:  # pragma: no cover - defensive fallback
                res["obj_cls"] = qualname
        if self.obj_cls is None:
            res.pop("obj_cls", None)
        return res

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

