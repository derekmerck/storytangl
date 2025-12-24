from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tangl.type_hints import StringMap, Tag
from tangl.core.entity import Selectable, is_identifier

# todo: I find it irritating that this bad idea keeps creeping back in.
#       just use has_path or has_ancestor_tags or provide the requirement node
#       as the selector.
class ScopeSelector(BaseModel):
    """Scope selector metadata for template lookups."""

    model_config = ConfigDict(extra="allow")

    source_label: str | None = None
    parent_label: str | None = None
    ancestor_labels: set[str] = Field(default_factory=set)
    ancestor_tags: set[Tag] = Field(default_factory=set)

    def is_global(self) -> bool:
        return not (
            self.source_label
            or self.parent_label
            or self.ancestor_labels
            or self.ancestor_tags
        )


class ScopeSelectable(Selectable):
    """
    Entity with scope requirements for pattern-based matching.

    Examples:
        >>> template = ScopeSelectable(
        ...     label="guard",
        ...     ancestor_tags={"combat"},
        ...     path_pattern="dungeon.*"
        ... )
        >>>
        >>> criteria = template.get_selection_criteria()
        >>> # {'has_ancestor_tags': {'combat'}, 'has_path': 'dungeon.*'}
    """
    # todo: we don't want this.  We want templates to infer their valid scope
    #       and nodes be able to state their location/path.  Nodes don't need
    #       scope, they have locality.
    scope: ScopeSelector | None = Field(default_factory=ScopeSelector)
    req_ancestor_tags: set[Tag] = Field(default_factory=set, alias="ancestor_tags")
    req_path_pattern: str | None = Field(None, alias="path_pattern")

    @model_validator(mode="before")
    @classmethod
    def _coerce_scope(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        scope_data = data.get("scope")
        if scope_data is None:
            return data
        if isinstance(scope_data, ScopeSelector):
            return data

        updated = dict(data)
        updated["scope"] = ScopeSelector.model_validate(scope_data)
        return updated

    @is_identifier
    def get_scope_identifier(self) -> set[str] | None:
        identifiers: set[str] = set()
        if self.scope is not None and self.scope.parent_label and self.label:
            identifiers.add(f"{self.scope.parent_label}.{self.label}")
        if self.req_path_pattern and self.label:
            pattern = self.req_path_pattern
            if pattern.startswith("~"):
                pattern = pattern[1:]
            if pattern.endswith(".*"):
                identifiers.add(f"{pattern[:-2]}.{self.label}")
        return identifiers or None

    def get_selection_criteria(self) -> StringMap:
        """Translate scope requirements to selection criteria.

        Notes:
            - `has_ancestor_tags` means the selector (e.g., a GraphItem) must have
              these tags somewhere on itself or in its ancestor chain.
            - `has_path` is an fnmatch pattern against the selector's canonical path, i.e. <Node:scene1.foo>.has_path('scene1.*') -> True
        """
        criteria: StringMap = super().get_selection_criteria()
        if self.scope is not None:
            if self.scope.source_label:
                criteria.setdefault("label", self.scope.source_label)
            if self.scope.parent_label:
                parent_label = self.scope.parent_label

                def _matches_parent(selector: object) -> bool:
                    label = getattr(selector, "label", None)
                    if label == parent_label:
                        return True
                    has_parent_label = getattr(selector, "has_parent_label", None)
                    if callable(has_parent_label):
                        return has_parent_label(parent_label)
                    return False

                criteria.setdefault("predicate", _matches_parent)
            if self.scope.ancestor_tags:
                criteria.setdefault("has_ancestor_tags", self.scope.ancestor_tags)
        if self.req_ancestor_tags:
            criteria.update({"has_ancestor_tags": self.req_ancestor_tags})
        if self.req_path_pattern:
            criteria.update({"has_path": self.req_path_pattern})
        return criteria
