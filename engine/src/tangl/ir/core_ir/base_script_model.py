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

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(*args, **kwargs)
        res.pop("uid", None)
        res.pop("seq", None)
        res.pop("is_dirty_", None)

        def _strip_metadata(value: Any) -> None:
            if isinstance(value, dict):
                value.pop("uid", None)
                value.pop("seq", None)
                value.pop("is_dirty_", None)
                for item in value.values():
                    _strip_metadata(item)
            elif isinstance(value, list):
                for item in value:
                    _strip_metadata(item)

        _strip_metadata(res)
        if self.obj_cls is not None:
            res["obj_cls"] = self.obj_cls
        else:
            obj_cls_value = res.get("obj_cls")
            if isinstance(obj_cls_value, type) and obj_cls_value is not self.__class__:
                module = getattr(obj_cls_value, "__module__", "")
                qualname = getattr(obj_cls_value, "__qualname__", obj_cls_value.__name__)
                res["obj_cls"] = f"{module}.{qualname}" if module else qualname
            else:
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

