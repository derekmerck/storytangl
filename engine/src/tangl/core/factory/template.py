# tangl/core/factory/template.py
from __future__ import annotations
from typing import TypeVar, Generic, Self, Iterator, Optional, Type, get_origin, get_args
from uuid import UUID, uuid4
from inspect import isclass
import logging

from pydantic import Field, field_validator, FieldValidationInfo, model_validator

from tangl.type_hints import Typelike, UnstructuredData, StringMap, Tag
from tangl.core.entity import Entity, Selectable
from tangl.core import Registry
from tangl.core.record import Record, ContentAddressable
from tangl.core.graph import GraphItem

logger = logging.getLogger(__name__)


ET = TypeVar('ET', bound=Entity)

class Template(Selectable, ContentAddressable, Record, Generic[ET]):
    """
     Semi-structured template for creating entities on demand.

     Key features:
     - Holds obj_cls as a field (unlike Entity which uses it only for structure())
     - Excludes instance metadata (uid, seq, is_dirty) from serialization
     - Provides separate paths for script serialization vs entity materialization

     Examples:
         >>> from tangl.core.graph import Node
         >>> template = Template[Node](label="guard", obj_cls=Node)
         >>>
         >>> # Serialize back to script
         >>> script_data = template.unstructure_as_template()
         >>>
         >>> # Materialize entity
         >>> entity_data = template.unstructure_for_materialize()
         >>> node = Node.structure(entity_data)
     """

    # todo: maybe use serialize=False for these fields, not exclude, which will remove it from comparison and hashing

    # Mark record metadata as excluded for serialization
    uid: UUID = Field(default_factory=uuid4, exclude=True)
    is_dirty_: bool = Field(default=False, exclude=True)
    seq: int = Field(init=False, exclude=True)  # injected by Record/HasSeq

    # obj_cls is a field (not just init param like Entity)
    obj_cls_: Typelike = Field(None, alias="obj_cls")

    @field_validator("obj_cls_", mode="after")
    @classmethod
    def _hydrate_obj_cls(cls, data):
        """Hydrate string obj_cls to Python type."""
        if data is None:
            return None

        # Hydrate string to type
        if isinstance(data, str):
            resolved = Entity.dereference_cls_name(data)
            if resolved:
                data = resolved

        # Validate that it is a class and Entity subclass (or None)
        if not (data is Entity or (isclass(data) and issubclass(data, Entity))):
            raise ValueError(f"obj_cls must be Entity or subclass, got {data}")

        return data

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        return cls.get_generic_type_for(Template, default=Entity)

    @property
    def obj_cls(self) -> Type[Entity]:
        """Get obj_cls with fallback to default."""
        return self.obj_cls_ or self.get_default_obj_cls()

    def is_instance(self, obj_cls: Type[Entity]) -> bool:
        # Check against the _latent_ type, not the Template class
        # Templ[MyActor].is_instance(Actor) -> True
        # This enables Template.match(is_instance=Actor)
        return issubclass(self.obj_cls, obj_cls)

    # Inherits label, tags as is

    # todo: could provide helper function that creates Templates automatically from an Entity class

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        """
        Structure data as template.

        For clarity, prefer explicit structure_as_template() or materialize().
        """
        # todo: should just raise or issue warning?
        return cls.structure_as_template(data)

    @classmethod
    def structure_as_template(cls, data: StringMap) -> Self:
        """
        Load template from script data.

        Args:
            data: Unstructured script data with obj_cls

        Returns:
            Template instance
        """
        # Don't pop obj_cls - it's a field
        # Pydantic will validate and hydrate it
        return cls.model_validate(data)

    def materialize(self, **kwargs) -> ET:
        """
        Create entity from template.

        Args:
            **kwargs: Override template fields (use sparingly - overrides beat template data)

        Returns:
            Entity instance of type ET

        Examples:
            >>> template = Template[Node](label="guard", tags={"npc"})
            >>> node = template.materialize(obj_cls=SpecialNode, label="special_guard")  # Override class and label

        Warning:
            kwargs override template data. Use for runtime customization only.
        """
        data = self.unstructure_for_materialize()
        data.update(kwargs)

        # We don't want to call structure on the payload object cls
        # directly -- it may have been changed during the unstructure
        # for materialize call or via the kwargs.  So just let
        # Entity.structure() do its thing.
        return Entity.structure(data)

    def unstructure(self) -> UnstructuredData:
        """
        Unstructure for serialization.

        For clarity, prefer explicit unstructure_as_template() or
        unstructure_for_materialize().
        """
        # todo: should just raise or issue warning?
        return self.unstructure_as_template()

    # unstructure is the same in these cases?
    def unstructure_as_template(self) -> UnstructuredData:
        """
        Serialize template back to script format.

        Returns:
          Script data suitable for round-trip serialization
        """
        return super().model_dump(by_alias=True,
                                  exclude_unset=True,
                                  exclude_defaults=True,
                                  exclude_none=True)

    def unstructure_for_materialize(self) -> UnstructuredData:
        # call model dump for unstructured data suitable to pass to Entity.structure
        data = super().model_dump(by_alias=True,
                                  exclude_unset=False,
                                  # dict-children may be path-less templates
                                  exclude_defaults=True,
                                  exclude_none=True)
        # Ensure obj_cls is present and correct; if it's None, super().model_dump
        # will include the wrong templ.__class__
        data["obj_cls"] = self.obj_cls
        return data


# todo: this gets moved into `core.graph`, can be tested independently of
#       template with GraphItem selectors
class ScopeSelectable(Selectable):
    """
    Template with scope requirements for pattern-based matching.

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

class HierarchicalTemplate(ScopeSelectable, Template[GIT], Generic[GIT]):
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
        >>> list(t.label for t in scene.visit())
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
        visit_fields = self._fields(visit_field=(True, False))
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


class Factory(Registry[Template]):
    """
    Registry of templates with materialization support.

    Examples:
        >>> # Create factory from root template
        >>> factory = Factory.from_root_templ(root_script)
        >>>
        >>> # Find templates
        >>> start_block = factory.find_one(
        ...     has_path="scene1.start",
        ...     has_tags="start"
        ... )
        >>>
        >>> # Materialize entity
        >>> node = Factory.materialize_templ(start_block)
    """

    @classmethod
    def from_root_templ(cls, root_templ: HierarchicalTemplate) -> Factory:
        """
        Create factory by flattening hierarchical template.

        Each registered template retains its hierarchical `path` and the derived
        scope metadata is tested by `get_selection_criteria()` when matched
        against a selector.

        Args:
            root_templ: Root of template hierarchy

        Returns:
            Factory with all templates registered
        """
        factory = cls(label=f"{root_templ.get_label()}_factory")

        # Visit entire tree and register
        for templ in root_templ.visit():
            factory.add(templ)

        return factory

    # todo: this is maybe redundant unless it holds materialize dispatch
    @classmethod
    def materialize_templ(cls, templ: Template[ET], **kwargs) -> ET:
        """
        Create entity from template.

        Args:
            templ: Template to materialize
            kwargs: attrib overrides to be passed into instantiation

        Returns:
            Entity instance

        Note:
            This creates only the single entity - does NOT materialize
            children for graph items.
        """
        return templ.materialize(**kwargs)

        # Future -- use factory dispatch and provide hooks
        # factory.dispatch.do_materialize(self, ctx=params)
        # - calls: do_get_cls, do_materialize, do_init

