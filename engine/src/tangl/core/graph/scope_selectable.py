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
    req_path_pattern: str = Field(None, alias="path_pattern")

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

#
#
# class ScopeSelector(BaseModel):
#     """Declare where a template is valid within a story hierarchy."""
#
#     source_label: Optional[str] = Field(
#         None,
#         description="Exact block or scene label where the template is valid.",
#     )
#     parent_label: Optional[str] = Field(
#         None,
#         description="Direct parent label constraint.",
#     )
#     ancestor_tags: Optional[set[str]] = Field(
#         None,
#         description="Template is valid if any ancestor has these tags.",
#     )
#     ancestor_labels: Optional[set[str]] = Field(
#         None,
#         description="Template is valid if any ancestor has these labels.",
#     )
#
#     def is_global(self) -> bool:
#         """Return ``True`` when no scope constraints are declared."""
#
#         return all(
#             getattr(self, field_name) is None
#             for field_name in (
#                 "source_label",
#                 "parent_label",
#                 "ancestor_tags",
#                 "ancestor_labels",
#             )
#         )
#
# class ScopeSelectable(Selectable):
#
#     req_scope_tags: set[Tag] = Field(default_factory=set, alias="scope_tags")
#     req_scope_path: str = Field(None, alias="scope_path")
#
#     def get_selection_criteria(self) -> StringMap:
#         """Translate template scope into node-matchable predicates."""
#
#         criteria: StringMap = super().get_selection_criteria()
#         if self.req_scope_tags:
#             criteria.update({'has_ancestor_tags': self.req_scope_tags})
#         if self.req_scope_path:
#             criteria.update({'has_path': self.req_scope_path})
#         return criteria
#
#     scope: ScopeSelector | None = Field(
#         None,
#         description="Where this template is valid (``None`` makes it global).",
#     )
#     #
#     # def get_selection_criteria(self) -> StringMap:
#     #     """Translate template scope into node-matchable predicates."""
#     #
#     #     criteria: StringMap = {}
#     #
#     #     scope = getattr(self, "scope", None)
#     #     if scope is None or scope.is_global():
#     #         return criteria
#     #
#     #     if scope.parent_label:
#     #         criteria["has_parent_label"] = scope.parent_label
#     #
#     #     if scope.ancestor_labels:
#     #         criteria["has_path"] = ".".join(scope.ancestor_labels)
#     #
#     #     if scope.ancestor_tags:
#     #         criteria["has_ancestor_tags"] = scope.ancestor_tags
#     #
#     #     if scope.source_label:
#     #         criteria["label"] = scope.source_label
#     #
#     #     return criteria
#
#     def has_scope(self, scope: Optional["ScopeSelector"]) -> bool:
#         """Return ``True`` when this item is valid for the given scope selector."""
#
#         if scope is None or scope.is_global():
#             return True
#
#         candidate = getattr(self, "scope", None)
#         if candidate is None:
#             return False
#
#         if scope.source_label is not None and candidate.source_label != scope.source_label:
#             return False
#
#         if scope.parent_label is not None and candidate.parent_label != scope.parent_label:
#             return False
#
#         if scope.ancestor_labels is not None:
#             candidate_labels = candidate.ancestor_labels or set()
#             if not scope.ancestor_labels.issubset(candidate_labels):
#                 return False
#
#         if scope.ancestor_tags is not None:
#             candidate_tags = candidate.ancestor_tags or set()
#             if not scope.ancestor_tags.issubset(candidate_tags):
#                 return False
#
#         return True
