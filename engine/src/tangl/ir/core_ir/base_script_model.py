from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field, model_validator

from tangl.core import ContentAddressable, Record
from tangl.core.entity import Selectable
from tangl.type_hints import ClassName, Expr, Label, StringMap


if TYPE_CHECKING:
    from tangl.ir.story_ir.story_script_models import ScopeSelector


class BaseScriptItem(Selectable, Record, ContentAddressable):
    """Template IR record that also provides a deterministic content hash."""

    obj_cls: Optional[ClassName] = None      # For structuring/unstructuring
    template_names: Optional[Label] = None

    locked: bool = False                     # Requires manual unlocking

    locals: Optional[StringMap] = None       # Namespace

    scope: ScopeSelector | None = Field(
        None,
        description="Where this template is valid (``None`` makes it global).",
    )

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

    def get_selection_criteria(self) -> dict[str, Any]:
        """Translate template scope into node-matchable predicates."""

        criteria: dict[str, Any] = {}

        scope = getattr(self, "scope", None)
        if scope is None or scope.is_global():
            return criteria

        if scope.parent_label:
            criteria["has_parent_label"] = scope.parent_label

        if scope.ancestor_labels:
            criteria["has_ancestor_labels"] = scope.ancestor_labels

        if scope.ancestor_tags:
            criteria["has_ancestor_tags"] = scope.ancestor_tags

        if scope.source_label:
            criteria["label"] = scope.source_label

        return criteria

    @classmethod
    def _get_hashable_content(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Exclude metadata so structurally-identical templates share a hash."""

        exclude = {
            "uid",
            "seq",
            "is_dirty_",
            "is_dirty",
            "content_hash",
            "scope",
            "label",
            "template_names",
        }
        return {key: value for key, value in data.items() if key not in exclude}

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(*args, **kwargs)
        res.pop("uid", None)
        res.pop("seq", None)
        res.pop("is_dirty_", None)
        # Keep ``content_hash`` for provenance tracking

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

