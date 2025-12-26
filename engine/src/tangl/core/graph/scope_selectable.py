from __future__ import annotations
from fnmatch import fnmatch

from pydantic import Field

from tangl.type_hints import StringMap, Tag
from tangl.core.entity import Selectable, is_identifier
from .graph import GraphItem

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

    @is_identifier
    def get_scope_identifier(self) -> set[str] | None:
        identifiers: set[str] = set()
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
        if self.req_path_pattern:
            criteria.update({"has_path": self.req_path_pattern})
        if self.req_ancestor_tags:
            criteria.update({"has_ancestor_tags": self.req_ancestor_tags})
        if self.forbid_ancestor_tags:
            criteria.update({"has_ancestor_tags__not": self.forbid_ancestor_tags})
        return criteria

    # Use to sort on path specificity -- more specific sorts earlier
    # Could make this default, but still need to give a sort_key to find
    def scope_specificity(self, selector: GraphItem | None = None) -> int:
        path_pattern = self.get_path_pattern()
        if not path_pattern:
            return 0
        specificity = len(path_pattern.split("."))
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
        if selector is not None:
            specificity = self._pattern_specificity(pattern, selector)
        else:
            segments = pattern.split(".")
            specificity = -sum(1 for seg in segments if "*" not in seg)
        exact = 0 if ("*" not in pattern and selector and selector.path == pattern) else 1
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
            specificity,  # closer ancestor is better
            -literal_segments,
            doublestar_count,  # fewer ** is better
            star_count,  # fewer * is better
            -len(pattern.split(".")),  # longer patterns as last-resort
        )

    # If you want a total ordering given a generic/root selector
    # def __lt__(self, other):
    #     return self.scope_rank() < other.scope_rank()
