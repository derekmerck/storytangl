# tangl/core/factory/hierarchical_template.py
from __future__ import annotations
from typing import TypeVar, Generic, Self, Iterator, Optional
import logging

from pydantic import Field, FieldValidationInfo, model_validator

from tangl.type_hints import UnstructuredData, StringMap, Tag
from tangl.core.entity import Selectable
from tangl.core.graph import GraphItem
from .template import Template

logger = logging.getLogger(__name__)


# todo: this gets moved into `core.graph`, can be tested independently of
#       template with GraphItem selectors
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


GIT = TypeVar('GIT', bound=GraphItem)

class HierarchicalTemplate(ScopeSelectable,
                           Template[GIT],   # type: ignore[type-arg]
                           Generic[GIT]):
    """
    Template DAG with parent/child relationships and auto-computed paths.

    Key features:
    - Auto-sets parent references on children
    - Computes path property from ancestor chain
    - visit() for depth-first tree traversal
    - Scope pattern generation from hierarchy

    Examples:
        >>> class SceneTemplate(HierarchicalTemplate):
        ...     blocks: dict = Field(
        ...         default_factory=dict,
        ...         json_schema_extra={'visit_field': True}
        ...     )
        >>>
        >>> scene = SceneTemplate(
        ...     label="scene1",
        ...     blocks={
        ...         "start": HierarchicalTemplate(label="start"),
        ...         "end": HierarchicalTemplate(label="end")
        ...     }
        ... )
        >>>
        >>> scene.path
        'scene1'
        >>> scene.blocks["start"].path
        'scene1.start'
        >>>
        >>> list(t.get_label() for t in scene.visit())
        ['scene1', 'start', 'end']
    """
    parent: Optional[Self] = Field(None, exclude=True)
    children: Optional[dict[str, Template]|list[Template]] = Field(default_factory=list, json_schema_extra={'visit_field': True})
    # Default field to hold generic children, subclasses are encouraged
    # to name and type-annotate their own children fields.  Remember to
    # tag it as a 'visit_field' to enable hierarchical handling.

    def ancestors(self) -> Iterator[Self]:
        """Yield ancestors from parent to root."""
        current = self.parent
        while current:
            yield current
            current = current.parent

    @property
    def path(self):
        """
        Hierarchical path computed from ancestors.

        Examples:
            root → "root"
            root.a → "root.a"
            root.a.b → "root.a.b"
        """
        # Build path from root to self
        reversed_ancestors = reversed([self] + list(self.ancestors()))
        return '.'.join([a.get_label() for a in reversed_ancestors])

    # Not sure about this -- if we set label here, it won't be tracked as
    # Unset and we need to note that manually somehow.  Maybe better to do
    # it in an 'after' handler?
    # @field_validator("*", mode="before")
    # @classmethod
    # def _set_label_from_key(cls, value: dict[UniqueLabel, StringMap], info: FieldValidationInfo) -> dict[UniqueLabel, StringMap]:
    #     # Get field metadata
    #     field_name = info.field_name
    #     if not field_name:
    #         return value
    #
    #     field_info = cls.model_fields.get(field_name)
    #     if not field_info:
    #         return value
    #
    #     extra = field_info.json_schema_extra or {}
    #
    #     # Only process visit fields
    #     if not extra.get("visit_field"):
    #         return value
    #
    #     # Set label from key for dict values
    #     if isinstance(value, dict):
    #         for k, v in value.items():
    #             if isinstance(v, dict):
    #                 v.setdefault("label", k)
    #
    #     return value

    @model_validator(mode="after")
    def _set_label_and_parent_on_children(self):
        # This sets up 'path' on every child, for dict children
        # It also sets the correct label on v from the key
        # Setting it here will leave it as Unset, I think.
        # Uses update_attrs b/c that bypasses frozen
        for field in self._fields(visit_field=(True, False)):
            value = getattr(self, field)
            if isinstance(value, Template):
                # single child
                value.update_attrs(parent=self)
            elif isinstance(value, dict):
                # dict of children by label
                for k, v in value.items():
                    if v.label is None:
                        logger.debug(f"Updating label {k}")
                        v.update_attrs(label=k)
                    v.update_attrs(parent=self)
            elif isinstance(value, list):
                # list of children
                for v in value:
                    v.update_attrs(parent=self)
            else:
                raise ValueError(f"Unexpected type {type(value)}")
        return self

    def visit(self) -> Iterator[Self]:
        """Depth-first traversal of template tree (preorder).

        Yields:
            All templates in tree, starting with self.
        """
        yield self

        for visit_field in self._fields(visit_field=(True, False)):
            value = getattr(self, visit_field)
            if isinstance(value, Template):
                yield from value.visit()
            elif isinstance(value, list):
                for v in value:
                    yield from v.visit()
            elif isinstance(value, dict):
                for v in value.values():
                    yield from v.visit()

    # todo: actually have to decide how to represent 'valid in scope'
    #       default could just be my pattern is self.parent.path*
    #       but may want to explicitly set something like "*.village.*"
    #       (anywhere in any village)

    def get_path_pattern(self):
        """
         Generate default fnmatch pattern for scope matching.

         Returns pattern that matches anything under parent path.

         Examples:
             scene1.block1 → "scene1.*"
             root.a.b → "root.a.*"
         """
        if self.parent is None:
            # Global template
            return "*"

        # Pattern matches anything under the parent path
        parent_path = self.parent.path
        return f"{parent_path}.*"

    def get_selection_criteria(self) -> StringMap:
        """Selection metadata derived from hierarchy.

        By convention, a nested template is valid anywhere under its *parent* path.
        Root templates are globally scoped.
        """
        criteria = super().get_selection_criteria()

        if "has_path" not in criteria and self.parent is not None:
            # Default scope matching: global or anywhere under the parent path.
            criteria["has_path"] = self.get_path_pattern()

        return criteria

    def unstructure_for_materialize(self) -> UnstructuredData:
        """
        This is intentionally *local* and non-recursive: it only creates the
        UnstructuredData for this _template_ and none of its children.  Any
        additional wiring (deps, actions, media, etc.) should happen in
        higher-level orchestration/dispatch.
        """
        # call model dump for unstructured data suitable to pass to Entity.structure
        visit_fields = set(self._fields(visit_field=(True, False)))
        # Don't need any child templates, materializer will deal with them
        data = super().model_dump(by_alias=True,
                                  exclude_unset=False,
                                  # Would want to preserve label on dict-children IF we were including them
                                  exclude_defaults=True,
                                  exclude_none=True,
                                  exclude=visit_fields)
        # Ensure obj_cls is present
        if "obj_cls" not in data:
            data["obj_cls"] = self.obj_cls
        return data

