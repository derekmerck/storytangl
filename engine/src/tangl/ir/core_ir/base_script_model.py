from __future__ import annotations
from typing import Optional

from pydantic import Field

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

    def get_path_pattern(self) -> str:
        """Return the scope match pattern, treating root script templates as global."""
        if "req_path_pattern" in self.model_fields_set and self.req_path_pattern is None:
            return None
        if self.req_path_pattern is None and self.parent is not None:
            from .master_script_model import MasterScript

            if isinstance(self.parent, MasterScript):
                return "*"
        pattern = super().get_path_pattern()
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
