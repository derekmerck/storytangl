from __future__ import annotations

from inspect import isclass
from typing import TYPE_CHECKING, Any, Optional, ClassVar, Type, Self, Union

from pydantic import Field, model_validator, field_validator

from tangl.core import ContentAddressable, Record, Entity
from tangl.core.entity import is_identifier
from tangl.core.graph.scope_selectable import ScopeSelectable
from tangl.type_hints import Typelike, Expr, Label, StringMap, UnstructuredData, UniqueLabel

# I would love to make this generic for templ_cls, but that would involve dragging the entire story architecture in here.
class BaseScriptItem(ScopeSelectable, ContentAddressable, Record):
    """Template IR record that also provides a deterministic content hash."""

    templ_cls: Optional[Typelike] = None
    # For un/structuring _payload_, this is aliased to 'obj_cls' in unstructured form
    # thus, ScriptItems must be structured by calling their class type _directly_.

    @classmethod
    def get_templ_cls_hint(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.core import Node
        return Node

    @property
    def obj_cls(self):
        # compatability
        return self.templ_cls

    template_names: Optional[Label] = None

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

    content: Optional[str] = None           # Rendered content fields
    icon: Optional[str] = None

    @property
    @is_identifier
    def qual_label(self) -> str:
        """Qualified label: parent.label for scoped templates, plain label for global."""

        scope = getattr(self, "scope", None)
        if scope and scope.parent_label:
            return f"{scope.parent_label}.{self.get_label()}"
        return self.get_label()

    @classmethod
    def _get_hashable_content(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Exclude metadata so structurally-identical templates share a hash."""

        exclude = {
            "uid",
            "seq",
            "is_dirty_",
            "is_dirty",
            "content_hash",
            "scope",
            "label",
            "template_names",
        }
        return {key: value for key, value in data.items() if key not in exclude}

    # def model_dump(self, *args, **kwargs) -> dict[str, Any]:
    #     kwargs.setdefault('exclude_unset', True)
    #     kwargs.setdefault('exclude_defaults', True)
    #     kwargs.setdefault('exclude_none', True)
    #     res = super().model_dump(*args, **kwargs)
    #     res.pop("uid", None)
    #     res.pop("seq", None)
    #     res.pop("is_dirty_", None)
    #     # Keep ``content_hash`` for provenance tracking
    #
    #     def _strip_metadata(value: Any) -> None:
    #         if isinstance(value, dict):
    #             value.pop("uid", None)
    #             value.pop("seq", None)
    #             value.pop("is_dirty_", None)
    #             for item in value.values():
    #                 _strip_metadata(item)
    #         elif isinstance(value, list):
    #             for item in value:
    #                 _strip_metadata(item)
    #
    #     _strip_metadata(res)
    #     if self.obj_cls is not None:
    #         res["obj_cls"] = self.obj_cls
    #     else:
    #         obj_cls_value = res.get("obj_cls")
    #         if isinstance(obj_cls_value, type) and obj_cls_value is not self.__class__:
    #             module = getattr(obj_cls_value, "__module__", "")
    #             qualname = getattr(obj_cls_value, "__qualname__", obj_cls_value.__name__)
    #             res["obj_cls"] = f"{module}.{qualname}" if module else qualname
    #         else:
    #             res.pop("obj_cls", None)
    #     return res

    @model_validator(mode="before")
    @classmethod
    def _lift_template_name_aliases(cls, data: Any) -> Any:
        """Preserve legacy ``templates`` aliases for template name references."""

        if not isinstance(data, dict):
            return data

        templates_value = data.get("templates")
        if templates_value is None:
            return data

        if isinstance(templates_value, dict):
            return data

        updated = dict(data)
        updated.setdefault("template_names", templates_value)
        updated.pop("templates", None)
        return updated

    @model_validator(mode="before")
    @classmethod
    def _alias_obj_cls_to_templ_cls(cls, data: Any) -> Any:
        if "obj_cls" in data:
            if 'templ_cls' in data:
                raise ValueError("Can't define both obj_cls _and_ templ_cls")
            data['templ_cls'] = data.pop("obj_cls")
        return data

    @field_validator('templ_cls', mode="after")
    @classmethod
    def _hydrate_templ_cls(cls, data):
        # try to unflatten it as the qualified name against Entity
        if data is not None:
            # None is fine, it just means use hint or override
            if isinstance(data, str):
                # strs are not fine, we want a type in here in accordance with general rules
                data = Entity.dereference_cls_name(data)
            if not (isclass(data) and (data is Entity or issubclass(data, Entity))):
                raise ValueError(f"Failed to hydrate {data} as Entity cls")
        return data

    @classmethod
    def _set_label_from_key(cls, value: dict[UniqueLabel, StringMap]) -> dict[UniqueLabel, StringMap]:
        # Use this as the validator
        if isinstance(value, dict):
            for k, v in value.items():
                v.setdefault("label", k)
        return value

    def visit(self, scope_path: str = None):

        def _visit_child_scripts(value: BaseScriptItem | dict[str, BaseScriptItem] | list[BaseScriptItem]):
            if isinstance(value, BaseScriptItem):
                yield value.visit(scope_path=scope_path)
            if isinstance(value, list):
                for v in value:
                    yield v.visit(scope_path=scope_path)
            elif isinstance(value, dict):
                for k, v in value.items():
                    yield v.visit(scope_path=scope_path)

        yield self
        for children_script_field in self._fields(child_scripts=(True, False)):
            children = getattr(self, children_script_field)
            _visit_child_scripts(children)

    def model_dump(self, **kwargs) -> StringMap:
        """
        Produce unstructured data suitable for instantiating a new object
        _or_ for serializing back into a flat script-formated document.

        Wraps Entity.model_dump() for flexibility, but discards the built-in
        self-preservation for its uid own and obj_cls.
        """
        # todo: suggests that we need a serializer for scripts that's
        #       different than the one for persistence.

        kwargs["exclude_defaults"] = True
        kwargs["by_alias"] = True
        data = super().model_dump(**kwargs)

        data.pop("obj_cls", None)  # entity init-only field

        # Keep `content_hash` for provenance tracking
        def _strip_metadata(value: Any) -> None:
            if isinstance(value, dict):
                value.pop("uid", None)         # entity field
                value.pop("is_dirty_", None)   # entity field
                value.pop("seq", None)         # record field
                for item in value.values():
                    _strip_metadata(item)
            elif isinstance(value, list):
                for item in value:
                    _strip_metadata(item)

        _strip_metadata(data)
        # todo: this won't work on nested non-reference script items
        #       need to invoke their model-dump, does it automatically
        #       call this recursively in that first call from each
        #       sub-script?  So obj_cls is correctly set for nested item?

        if self.templ_cls is not None:
            data["obj_cls"] = self.templ_cls or self.get_templ_cls_hint()

        return data

    @classmethod
    def structure(cls, data: StringMap):
        raise NotImplementedError("'structure' is ambiguous for ScriptItems, call `cls.structure_as_templ` or `self.materialize_item` instead")

    @classmethod
    def structure_as_templ(cls, data: StringMap) -> Self:
        # obj_cls of _payload_ included in data, map to templ_cls
        if 'obj_cls' in data:
            data['templ_cls'] = data.pop("obj_cls", None)
        return super().structure(data)

    def materialize_item(self, obj_cls: Optional[Type[Entity]] = None):
        # todo: - In general, we are going to call script_dispatch.materialize()
        #         here to access pre/post-processors
        #       - needs to handle recursion
        #       - needs to accept additional params from materializer, namely 'graph'
        #       - scenes shouldn't materialize all blocks, blocks should materialize
        #         deps and affordances, are blocks just affordances?
        data = self.unstructure()
        data.pop("scope_selector", None)  # template metadata field
        # obj_cls of _payload_ included in data
        if obj_cls is not None:
            # Override obj_cls
            data["obj_cls"] = obj_cls
        return super().structure(data=data)
