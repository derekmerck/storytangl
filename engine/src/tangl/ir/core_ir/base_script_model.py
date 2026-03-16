from __future__ import annotations
from typing import Any, Iterator, Optional
from importlib import import_module

from pydantic import Field, field_validator, model_validator

from tangl.core import Record
from tangl.type_hints import Expr, Label, StringMap, Tag, Typelike, UnstructuredData


class BaseScriptItem(Record):
    """Record-based IR script model with local traversal/scope helpers."""

    kind_: Typelike = Field(None, alias="kind", exclude_if=lambda value: value is None)
    req_ancestor_tags: set[Tag] = Field(default_factory=set, alias="ancestor_tags")
    forbid_ancestor_tags: set[Tag] = Field(default_factory=set, alias="forbid_ancestor_tags")
    req_path_pattern: str | None = Field(None, alias="path_pattern")

    parent: Optional["BaseScriptItem"] = Field(None, exclude=True)

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

    @property
    def kind(self):
        return self.kind_ or self.get_default_kind()

    @classmethod
    def get_default_kind(cls) -> Typelike:
        return None

    @field_validator("kind_", mode="after")
    @classmethod
    def _hydrate_kind(cls, value: Typelike) -> Typelike:
        if value is None or isinstance(value, type):
            return value
        if isinstance(value, str):
            from tangl.core import Entity

            resolved = Entity.dereference_cls_name(value)
            if resolved is None and "." in value:
                try:
                    module_name, class_name = value.rsplit(".", 1)
                    resolved = getattr(import_module(module_name), class_name)
                except Exception:
                    resolved = None
            if isinstance(resolved, type):
                from tangl.core import Entity as ActiveEntity

                try:
                    if not issubclass(resolved, ActiveEntity):
                        active_alias = getattr(import_module("tangl.core"), resolved.__name__, None)
                        if isinstance(active_alias, type) and issubclass(active_alias, ActiveEntity):
                            resolved = active_alias
                except TypeError:
                    pass
                return resolved
        return value

    @classmethod
    def _visit_fields(cls) -> list[str]:
        fields: list[str] = []
        for field_name, field_info in cls.model_fields.items():
            extra = field_info.json_schema_extra or {}
            if extra.get("visit_field") in (True, False):
                fields.append(field_name)
        return fields

    def ancestors(self) -> Iterator["BaseScriptItem"]:
        current = self.parent
        while current is not None:
            yield current
            current = current.parent

    @property
    def path(self) -> str:
        labels = [
            part.get_label() if hasattr(part, "get_label") else part.label
            for part in reversed([self, *list(self.ancestors())])
        ]
        return ".".join(label for label in labels if label)

    def _base_path_pattern(self) -> str | None:
        if self.req_path_pattern is not None:
            if self.req_path_pattern.startswith("~"):
                postfix = self.req_path_pattern[1:]
            else:
                return self.req_path_pattern
        else:
            postfix = "*"

        if self.parent is None:
            if postfix == "*":
                return "*"
            prefix = "*"
        else:
            prefix = self.parent.path

        return f"{prefix}.{postfix}"

    def get_path_pattern(self) -> str:
        """Return the scope match pattern, treating root script templates as global."""
        if "req_path_pattern" in self.model_fields_set and self.req_path_pattern is None:
            return None
        if self.req_path_pattern is None and self.parent is not None:
            from .master_script_model import MasterScript

            if isinstance(self.parent, MasterScript):
                return "*"
        pattern = self._base_path_pattern()
        if self.req_path_pattern is None:
            from .master_script_model import MasterScript

            story_label = None
            for ancestor in self.ancestors():
                if isinstance(ancestor, MasterScript):
                    story_label = ancestor.label
                    break
            if story_label:
                prefix = f"{story_label}."
                if pattern.startswith(prefix):
                    pattern = pattern[len(prefix):]
            if (
                self.parent is not None
                and self.parent.__class__.__name__.endswith("BlockScript")
                and pattern.endswith(".*")
            ):
                pattern = pattern[:-2]
        return pattern

    def get_selection_criteria(self) -> StringMap:
        criteria = dict(super().get_selection_criteria())

        path_pattern = self.get_path_pattern()
        if path_pattern is not None:
            criteria["has_path"] = path_pattern
        if self.req_ancestor_tags:
            criteria["has_ancestor_tags"] = set(self.req_ancestor_tags)
        if self.forbid_ancestor_tags:
            criteria["has_ancestor_tags__not"] = set(self.forbid_ancestor_tags)
        return criteria

    def scope_specificity(self) -> int:
        path_pattern = self.get_path_pattern()
        if not path_pattern:
            return 0
        return -len(path_pattern.split("."))

    @classmethod
    def _pattern_specificity(cls, path_pattern: str, selector: Any) -> int:
        ancestors = getattr(selector, "ancestors", None)
        if not callable(ancestors):
            return 0
        for index, ancestor in enumerate(ancestors()):
            has_path = getattr(ancestor, "has_path", None)
            if not callable(has_path) or not has_path(path_pattern):
                return index
        return 1 << 20

    def scope_rank(self, selector: Any = None) -> tuple[int, int, int, int, int, int]:
        pattern = self.get_path_pattern() or "*"
        if selector is not None:
            specificity = self._pattern_specificity(pattern, selector)
        else:
            segments = pattern.split(".")
            specificity = -sum(1 for segment in segments if "*" not in segment)

        exact = 0 if ("*" not in pattern and selector and getattr(selector, "path", None) == pattern) else 1
        literal_segments = sum(
            1
            for segment in pattern.split(".")
            if segment not in ("*", "**") and "*" not in segment
        )
        star_count = pattern.count("*") - 2 * pattern.count("**")
        doublestar_count = pattern.count("**")

        return (
            exact,
            specificity,
            -literal_segments,
            doublestar_count,
            star_count,
            -len(pattern.split(".")),
        )

    def visit(self) -> Iterator["BaseScriptItem"]:
        yield self
        for visit_field in self._visit_fields():
            value = getattr(self, visit_field)
            if isinstance(value, BaseScriptItem):
                yield from value.visit()
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, BaseScriptItem):
                        yield from child.visit()
            elif isinstance(value, dict):
                for child in value.values():
                    if isinstance(child, BaseScriptItem):
                        yield from child.visit()

    def unstructure_for_materialize(self) -> UnstructuredData:
        visit_fields = set(self._visit_fields())
        data = self.model_dump(
            by_alias=True,
            exclude_unset=False,
            exclude_defaults=True,
            exclude_none=True,
            exclude=visit_fields | {"parent"},
        )
        data["kind"] = self.kind
        return data

    def unstructure_as_template(self) -> UnstructuredData:
        data = self.model_dump(
            by_alias=True,
            exclude_unset=True,
            exclude_defaults=True,
            exclude_none=True,
            exclude={"uid", "seq", "parent"},
        )
        if "kind_" not in self.model_fields_set:
            data.pop("kind", None)
        return data

    def model_dump(self, **kwargs) -> UnstructuredData:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    @model_validator(mode="after")
    def _set_label_and_parent_on_children(self) -> "BaseScriptItem":
        for field_name in self._visit_fields():
            value = getattr(self, field_name)
            if value is None:
                continue

            if isinstance(value, BaseScriptItem):
                value.force_set("parent", self)
            elif isinstance(value, dict):
                for key, child in value.items():
                    if not isinstance(child, BaseScriptItem):
                        continue
                    if child.label is None:
                        child.force_set("label", str(key))
                    child.force_set("parent", self)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, BaseScriptItem):
                        child.force_set("parent", self)
            else:
                raise ValueError(f"Traversal found unexpected type {type(value)}")

        return self

    children: dict[str, BaseScriptItem] | list[BaseScriptItem] = Field(
        None,
        alias="templates",
        json_schema_extra={"visit_field": True},
    )

    @property
    def templates(self) -> dict[str, BaseScriptItem] | list[BaseScriptItem]:
        return self.children

    @templates.setter
    def templates(self, value: dict[str, BaseScriptItem] | list[BaseScriptItem]) -> None:
        self.children = value
