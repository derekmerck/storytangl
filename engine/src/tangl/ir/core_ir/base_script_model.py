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
        if self.req_path_pattern is None and self.parent is not None:
            from .master_script_model import MasterScript

            if isinstance(self.parent, MasterScript):
                return "*"
        return super().get_path_pattern()

    children: dict[str, "BaseScriptItem"] | list["BaseScriptItem"] | None = Field(
        default_factory=dict,
        alias="templates",
        json_schema_extra={"visit_field": True},
    )

    @property
    def templates(self) -> dict[str, "BaseScriptItem"] | list["BaseScriptItem"] | None:
        return self.children

    @templates.setter
    def templates(self, value: dict[str, "BaseScriptItem"] | list["BaseScriptItem"] | None) -> None:
        self.children = value
