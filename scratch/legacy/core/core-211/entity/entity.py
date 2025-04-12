from __future__ import annotations
import inspect
from inspect import Parameter
from uuid import UUID, uuid4
from typing import Optional, Any, TypeVar, Type, Iterable, Literal
import functools
from functools import lru_cache
import logging
import re

from pydantic import BaseModel, Field, field_serializer, field_validator

from tangl.type_hints import Tags, Typelike
# from .self_casting import SelfCastingMetaclass

logger = logging.getLogger("tangl.entity")
logger.setLevel(logging.WARNING)

from tangl.utils.inheritance_aware import InheritanceAware
from .smart_new import SmartNewMetaclass, SmartNewHandler

class Entity(InheritanceAware, BaseModel, metaclass=SmartNewMetaclass):
    """
    Base class for all Managed Objects. Serves as the foundational class for all objects within the framework, leveraging Pydantic for data validation and serialization.

    Uses "SelfCastingMetaclass", which consumes an "obj_cls" parameter on `__new__` and attempts to dynamically cast itself to the correct subclass.

    Attributes:
      - `uid`: Provides a unique identifier for instances, crucial for tracking objects within the graph and serialization processes.
      - `label`: Acts as a public name or a truncated `uid` if a name isn't specified, supporting both unique and context-specific identification needs.
      - `tags`: A flexible mechanism to classify and filter entities based on characteristics or roles.

    Methods:
      - `has_tags`: Facilitates querying based on tags, enhancing searchability and categorization.
      - `model_dump`: Custom serialization logic that ensures compatibility with stateless service requirements by focusing on essential attributes.
      - `get_all_subclasses` & `get_subclass_by_name`: Enable dynamic type discovery and instantiation, supporting extensibility and modular design.
    """

    uid_: UUID = Field(default_factory=uuid4, alias="uid")
    @property
    def uid(self) -> UUID:
        return self.uid_

    label_: Optional[str] = Field(None, alias="label")
    # only singleton labels are guaranteed to be unique
    @property
    def label(self) -> str:
        # permit overriding label with a computed value
        if self.label_:
            return self.label_
        return str(self.uid)[0:6]

    tags: Tags = Field(default_factory=set)

    @field_validator('tags', 'with_tags', mode='before', check_fields=False)
    @classmethod
    def _handle_none_tags(cls, data):
        if data is None:
            data = set()
        return data

    @field_serializer('tags', 'with_tags', check_fields=False)
    def _set_to_list(self, data) -> list[str]:
        if data:
            return list(data)

    def has_tags(self, *tags: str) -> bool:
        return set(tags).issubset(self.tags)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(**kwargs)
        if self.uid_ is not None:
            res['uid'] = self.uid_       # Ignoring unset skips this otherwise
        res['obj_cls'] = self.__class__  # Always include this for restructuring
        return res

    @classmethod
    def public_field_names(cls):
        field_names = [ f.alias if f.alias else k for k, f in cls.model_fields.items() ]
        return field_names

    @classmethod
    def _cmp_fields(cls):
        return [ k for k, v in cls.model_fields.items()
                 if not v.json_schema_extra or v.json_schema_extra.get("cmp", True) ]

    def __eq__(self, other) -> bool:
        # There is no built-in way to exclude fields from comparison with pydantic, but this
        # seems to work
        # Other approaches include unlinking graph and then relinking it after comparison
        # or comparing model_dumps with excluded fields
        if not isinstance(other, self.__class__):
            return False
        for field in self._cmp_fields():
            if getattr(self, field, None) != getattr(other, field, None):
                return False
        return True

    # Introspection
    #
    # @classmethod
    # @lru_cache(maxsize=None)
    # def get_all_subclasses(cls) -> set[Type[Entity]]:
    #     """
    #     Recursively get all subclasses of the class.
    #     """
    #     subclasses = set(cls.__subclasses__())
    #     for subclass in subclasses.copy():
    #         subclasses.update(subclass.get_all_subclasses())
    #     subclasses.add( cls )
    #     return subclasses
    #
    # @classmethod
    # def __pydantic_init_subclass__(cls, **kwargs):
    #     # Reset our cached subclass lookup tables
    #     cls.get_all_subclasses.cache_clear()
    #     super().__pydantic_init_subclass__(**kwargs)
    #
    # @classmethod
    # def get_subclass_by_name(cls, cls_name: str) -> Type[Entity]:
    #     """
    #     Get a subclass by its name, searching recursively through all subclasses.
    #     """
    #     subclasses_by_name_map = {subclass.__name__: subclass for subclass in cls.get_all_subclasses()}
    #     return subclasses_by_name_map[cls_name]
    #
    # @classmethod
    # def get_all_superclasses(cls, this_cls: Type = None, ignore: Iterable[Type] = None) -> set[Type[Entity]]:
    #     """
    #     Recursively get all superclasses of the class.
    #     """
    #     classes_to_ignore = [object, BaseModel]
    #     if ignore:
    #          classes_to_ignore.extend( ignore )
    #
    #     this_cls = this_cls or cls
    #     superclasses = set(this_cls.__bases__)
    #     for superclass in superclasses.copy():
    #         superclasses.update(cls.get_all_superclasses(superclass))
    #     superclasses.add(cls)
    #     superclasses = { *filter(lambda x: x not in classes_to_ignore, superclasses) }
    #     return superclasses

    @classmethod
    def get_all_superclass_source(cls,
                                  include_handlers: bool = True,
                                  ignore: Iterable[Type] = None,
                                  docs_only: Iterable[Type] | Literal["all"] = None,
                                  include_base_entity_handler: bool = False,
                                  as_yaml: bool = True) -> dict[str, str] | str:

        from .base_handler import BaseEntityHandler
        # docs_only = docs_only or [Entity, BaseEntityHandler]

        classes_to_ignore = []
        if not include_base_entity_handler:
            classes_to_ignore.append( BaseEntityHandler )
        if ignore:
             classes_to_ignore.extend( ignore )

        superclasses = cls.get_all_superclasses(ignore=ignore)
        if include_handlers:
            handlers = set()
            if include_base_entity_handler:
                handlers.add(BaseEntityHandler)
            for scls in superclasses:
                module = inspect.getmodule(scls)
                cls_handlers = {
                    getattr(module, name) for name in dir(module)
                    if any(
                        [name.endswith(suffix) and inspect.isclass(getattr(module, name))
                         for suffix in ["Handler", "Manager", "Registry"]]
                    )
                }
                cls_handlers = list(filter(lambda x: x.__name__ in inspect.getsource(scls), cls_handlers))
                handlers.update(cls_handlers)
            superclasses.update(handlers)
            superclasses = {*filter(lambda x: x not in classes_to_ignore, superclasses)}

        def _get_source(k: Type):
            res = inspect.getsource(k)
            res = res.splitlines()
            res = list(filter(lambda v: bool(v) and not re.match(r"^ *#", v), res ))
            res = list(filter(lambda v: bool(v) and not re.match(r"^ *logger\.debug", v), res ))
            res = "\n".join(res)
            return res

        def _get_doc(k: Type):
            return inspect.getdoc(k)

        names = ", ".join([scls.__name__ for scls in superclasses])
        header = f"Source or doc for {names}\n"

        res = { k.__name__: _get_doc(k) if (docs_only == "all" or k in docs_only)
                                        else _get_source(k) for k in superclasses }

        if as_yaml:
            import yaml
            res = yaml.safe_dump(res, default_style="|", sort_keys=False)
            res = "# " + header + res
        else:
            res = { "#": header, **res }

        return res

    # todo: need some function like this but need to evoke the graph factory for Node,
    #       we need to also dump children like Look, Voice recursively
    # def evolve(self, **kwargs):
    #     base_kwargs = self.model_dump(
    #         exclude={'uid', 'label', 'parent_uid', 'children_uids'},
    #         exclude_none=True,
    #         exclude_unset=True,
    #         exclude_defaults=True)
    #     kwargs = base_kwargs | kwargs
    #     cls = self.__class__
    #     res = cls(**kwargs)
    #     # merge tags back in
    #     res.tags |= self.tags
    #     return res

    # @SmartNewHandler.normalize_class_strategy
    # def _dereference_obj_cls(base_cls, obj_cls: Typelike, **kwargs):
    #     logger.debug(f"dereferencing {base_cls}, {obj_cls}")
    #     if not obj_cls or obj_cls is base_cls:
    #         # Nothing to do
    #         return
    #
    #     if isinstance(obj_cls, str):
    #         # Cast to class type
    #         obj_cls = base_cls.get_subclass_by_name(obj_cls)
    #
    #     if obj_cls is base_cls:
    #         # Nothing to do
    #         return
    #
    #     if not inspect.isclass(obj_cls) or not issubclass(obj_cls, base_cls):
    #         # Make sure it's a subclass
    #         logger.error(str(base_cls.get_all_subclasses()))
    #         raise TypeError(f"Unable to determine entity-type for {obj_cls} given base_cls {base_cls}")
    #
    #     return obj_cls
    # # Do this _early_
    # _dereference_obj_cls.strategy_priority = 10

    @SmartNewHandler.normalize_class_strategy
    def _dereference_obj_cls(cls, obj_cls: Typelike, **kwargs):
        return cls.dereference_obj_cls(obj_cls, **kwargs)
    # Do this _early_
    _dereference_obj_cls.strategy_priority = 10

    def repr_data(self):
        data = super().model_dump(
            by_alias=True, exclude_unset=True, exclude_none=True, exclude_defaults=True,
            exclude={'parent_id', 'children_ids'}
        )
        return data

    # def __repr__(self):
    #     data = self.repr_data()
    #     ordered_data = []
    #     ordered_data.append(('uid', str(self.uid.hex)[0:6]),)
    #     ordered_data += data.items()
    #     if hasattr(self, "parent_id"):
    #         if self.parent:
    #             ordered_data.append(('parent', self.parent.label),)
    #         # if self.children:
    #         #     children_reprs = [repr(c) for c in self.children]  # todo: want to skip parent on these
    #         #     ordered_data.append(('children', children_reprs),)
    #     return Entity.make_repr(self.__class__, ordered_data)


EntityType = TypeVar("EntityType", bound=Entity)
