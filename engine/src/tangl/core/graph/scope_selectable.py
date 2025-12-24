from typing import Optional
from pydantic import BaseModel, Field

from tangl.type_hints import StringMap, Tag
from tangl.core.entity import Selectable


class ScopeSelectable(Selectable):
    """
    Entity with scope requirements for pattern-based matching.

    Examples:
        >>> template = ScopeSelectable(
        ...     label="guard",
        ...     req_scope_tags={"combat"},
        ...     req_scope_pattern="dungeon.*"
        ... )
        >>>
        >>> criteria = template.get_selection_criteria()
        >>> # {'has_ancestor_tags': {'combat'}, 'has_path': 'dungeon.*'}
    """
    req_ancestor_tags: set[Tag] = Field(default_factory=set, alias="ancestor_tags")
    req_path_pattern: str | None = Field(None, alias="path_pattern")

    def get_selection_criteria(self) -> StringMap:
        """Translate scope requirements to selection criteria.

        Notes:
            - `has_ancestor_tags` means the selector (e.g., a GraphItem) must have
              these tags somewhere on itself or in its ancestor chain.
            - `has_path` is an fnmatch pattern against the selector's canonical path, i.e. <Node:scene1.foo>.has_path('scene1.*') -> True
        """
        criteria: StringMap = super().get_selection_criteria()
        if self.req_ancestor_tags:
            criteria.update({"has_ancestor_tags": self.req_ancestor_tags})
        if self.req_path_pattern:
            criteria.update({"has_path": self.req_path_pattern})
        return criteria
