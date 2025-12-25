from __future__ import annotations
from fnmatch import fnmatch

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tangl.type_hints import StringMap, Tag
from tangl.core.entity import Selectable, is_identifier
from .graph import GraphItem

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
    forbid_ancestor_tags: set[Tag] = Field(default_factory=set, alias="forbid_ancestor_tags")
    req_path_pattern: str | None = Field(None, alias="path_pattern")

    def get_path_pattern(self) -> str:
        if self.req_path_pattern is not None:
            return self.req_path_pattern
        # attachment point for subclasses to define default scope patterns
        if hasattr(self, "_get_default_path_pattern"):
            return self._get_default_path_pattern()
        return "*"

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
        if self.req_path_pattern:
            criteria.update({"has_path": self.req_path_pattern})
        if self.req_ancestor_tags:
            criteria.update({"has_ancestor_tags": self.req_ancestor_tags})
        if self.forbid_ancestor_tags:
            criteria.update({"has_ancestor_tags__not": self.forbid_ancestor_tags})
        return criteria

    # Use to sort on path specificity -- more specific sorts earlier
    # Could make this default, but still need to give a sort_key to find
    def scope_specificity(self) -> int:
        path_pattern = self.get_path_pattern()
        if not path_pattern:
            return 0
        specificity = len(path_pattern.split("."))
        scope = getattr(self, "scope", None)
        if scope is not None and hasattr(scope, "is_global") and not scope.is_global():
            specificity += 1
        return -specificity

    @classmethod
    def _pattern_specificity(cls, path_pattern, selector: GraphItem) -> int:
        for i, p in enumerate(selector.ancestors()):
            if not p.has_path(path_pattern):
                return i
        return 1 << 20  # matched all the way to global, return large

    # todo: deprecate "scope specificity" as sort key and use this with selector
    def scope_rank(self, selector: GraphItem = None) -> tuple:
        """Compute scope ranking tuple for sorting templates.

        Returns tuple prioritizing:
        1. Exact matches (no wildcards)
        2. Closer ancestors (when selector provided)
        3. More literal segments
        4. Fewer wildcards
        5. Longer patterns
        """
        pattern = self.get_path_pattern() or "*"
        scope_distance = 1 << 20

        if selector is not None and self.scope is not None and self.scope.parent_label:
            parent_label = self.scope.parent_label
            if getattr(selector, "label", None) == parent_label:
                scope_distance = 0
            else:
                for index, ancestor in enumerate(selector.ancestors(), start=1):
                    if getattr(ancestor, "label", None) == parent_label:
                        scope_distance = index
                        break

        if selector is not None:
            specificity = -self._pattern_specificity(pattern, selector)
        else:
            segments = pattern.split(".")
            specificity = sum(1 for seg in segments if "*" not in seg)
        exact = 1 if ("*" not in pattern and selector and selector.path == pattern) else 0
        literal_segments = sum(
            1
            for seg in pattern.split(".")
            if seg not in ("*", "**") and "*" not in seg
        )
        star_count = pattern.count("*") - 2 * pattern.count("**")  # crude, but works
        doublestar_count = pattern.count("**")

        # can't use seq as final tie-breaker b/c no seq mixin, but could add if req
        return (
            exact,
            scope_distance,
            -specificity,  # closer ancestor is better
            literal_segments,
            -doublestar_count,  # fewer ** is better
            -star_count,  # fewer * is better
            len(pattern.split(".")),  # longer patterns as last-resort
        )

    # If you want a total ordering given a generic/root selector
    # def __lt__(self, other):
    #     return self.scope_rank() < other.scope_rank()
