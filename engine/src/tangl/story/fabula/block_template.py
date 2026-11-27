"""World-owned declarations for a compiled Block."""
from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.core import EntityTemplate
from tangl.core.template import TemplateGroup

from ..episode import Action, Block


class BlockTemplate(TemplateGroup):
    """A Block payload and the Action occurrences authored on it."""

    payload: Block = Field(exclude=True, json_schema_extra={"unstructurable": True})
    action_specs: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    action_templates: dict[str, list[EntityTemplate[Action]]] = Field(
        default_factory=dict, json_schema_extra={"unstructurable": True},
    )

    def get_hashable_content(self) -> dict[str, Any]:
        return {
            **super().get_hashable_content(),
            "action_specs": self.action_specs,
            "action_templates": {
                field: [item.unstructure() for item in templates]
                for field, templates in self.action_templates.items()
            },
        }
