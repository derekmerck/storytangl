import logging
from uuid import UUID, uuid4
from typing import TypeVar, Generic, ClassVar, Self, Optional, Any, Iterable, Type
import functools

import shortuuid
from pydantic import BaseModel, Field, model_validator, field_serializer, field_validator, ConfigDict

from tangl.type_hints import UniqueLabel, UnstructuredData, Tag, Identifier, Hash

logger = logging.getLogger(__name__)

ObjCls = TypeVar("ObjCls", bound=Type)

def subclass_by_name(base_cls: ObjCls, cls_name: UniqueLabel) -> Optional[ObjCls]:
    if base_cls.__name__ == cls_name:
        return base_cls
    for cls_ in base_cls.__subclasses__():
        if cls_.__name__ == cls_name:
            return cls_
        if cls_ := subclass_by_name(cls_, cls_name):
            return cls_
    return None  # can't raise here b/c it is a recursive call

def dereference_obj_cls(cls: ObjCls, cls_name: str) -> ObjCls:
    obj_cls = subclass_by_name(cls, cls_name)
    if obj_cls is None:
        raise ValueError(f"Cannot dereference subclass {cls_name} in {cls.__name__}")
    return obj_cls

class Entity(BaseModel):

    obj_cls: str = Field(init_var=True, default=None)  # Consumed by metaclass if necessary
    uid: UUID = Field(default_factory=uuid4)
    label: str = None
    tags: set[Tag] = Field(default_factory=set)
    data_hash: Hash = None

    @property
    def short_uid(self):
        return shortuuid.encode(self.uid)

    @model_validator(mode="after")
    def _set_default_label(self):
        # this is considered 'unset' and won't be serialized
        if self.label is None:
            self.label = self.short_uid[0:6]
        return self

    @field_serializer("tags")
    def _convert_set_to_list(self, values: set):
        if isinstance(values, set):
            return list(values)
        return values

    def has_tags(self, *tags: str) -> bool:
        return set(tags).issubset(self.tags)

    def get_identifiers(self) -> set[Identifier]:
        # Extend this in subclasses that want to include additional findable instance names
        return { self.uid, self.label, self.data_hash }

    def has_alias(self, *aliases: Identifier) -> bool:
        identifiers = self.get_identifiers()
        identifiers = { x for x in identifiers if x }  # discard empty/falsy identifiers
        return bool( set(aliases).intersection(identifiers) )

    def matches_criteria(self, **criteria) -> bool:
        # Must match all

        def compare_values(test_value, self_value) -> bool:
            if isinstance(self_value, set):
                if isinstance(test_value, (list, set)):
                    if set(test_value).issubset(self_value):
                        return True
                else:
                    raise ValueError(f"Undefined comparison between set and {type(test_value)}")
            elif test_value == self_value:
                return True

        if not criteria:
            raise ValueError("No criteria specified, return value is undefined.")

        for criterion, value in criteria.items():
            if hasattr(self, criterion):
                if not compare_values(value, getattr(self, criterion)):
                    return False
            elif hasattr(self, f"has_{criterion}"):
                if not compare_values(value, getattr(self, f"has_{criterion}")):
                    return False
            else:
                raise ValueError(f"Untestable comparitor for {criterion} on {self.__class__}")

        return True  # all checks passed

    @classmethod
    def filter_by_criteria(cls, entities: Iterable[Self], return_first: bool = False, **criteria) -> Self | list[Self] | None:
        matches = (e for e in entities if e.matches_criteria(**criteria))
        if return_first:
            return next(matches, None)
        return list(matches)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("exclude_defaults", True)
        kwargs['by_alias'] = True  # for round-trip
        data = super().model_dump(**kwargs)
        data['uid'] = self.uid  # uid is _always_ unset initially, so we have to include it manually
        data['obj_cls'] = self.__class__.__name__  # for restructuring to the correct model type
        return data

    def unstructure(self, *args, **kwargs) -> UnstructuredData:
        return self.model_dump(*args, **kwargs)

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        this = obj_cls(**data)
        return this

    @classmethod
    def cmp_fields(cls):
        res = []
        for field_name, field_info in cls.__pydantic_fields__.items():
            extra = field_info.json_schema_extra or {}
            if extra.get('cmp', True):
                res.append(field_info.alias or field_name)
        return res

    def __eq__(self, other) -> bool:
        # Avoid recursion on links
        for field in self.cmp_fields():
            if getattr(self, field) != getattr(other, field):
                return False
        return True


VT = TypeVar("VT", bound=Entity)

class Registry(dict[UUID, VT], Generic[VT]):

    def __setitem__(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__} is not setable by key, use `add(entity)`.")

    def __getitem__(self, key: UUID | UniqueLabel) -> VT:
        if isinstance(key, UniqueLabel):
            if x := self.find_one(label=key):
                return x
        return super().__getitem__(key)

    def add(self, value: VT, allow_overwrite: bool = False):
        if not allow_overwrite and value.uid in self:
            raise ValueError(f"Cannot overwrite {value.uid} in registry. Pass `allow_overwrite=True` to force overwrite.")
        super().__setitem__(value.uid, value)

    def remove(self, value: VT):
        # this is actually more like discard since it doesn't fail if the key is missing
        self.pop(value.uid, None)

    def find(self, **criteria) -> list[VT]:
        return Entity.filter_by_criteria(self.values(), **criteria)

    def find_one(self, **criteria) -> Optional[VT]:
        return Entity.filter_by_criteria(self.values(), return_first=True, **criteria)

    def unstructure(self, *args, **kwargs) -> UnstructuredData:
        data = []
        for v in self.values():
            data.append(v.unstructure())
        return { 'obj_cls': self.__class__.__name__, 'data': data }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        this = obj_cls()
        data = data.pop('data', [])
        for v in data:
            item = Entity.structure(v)
            this.add(item)
        return this

class Singleton(Entity):

    model_config = ConfigDict(frozen=True)

    _instances: ClassVar[Registry[Self]] = Registry[Self]()

    def __hash__(self):
        return hash((self.__class__, self.label),)

    @classmethod
    def __init_subclass__(cls, isolate_registry: bool = True, **kwargs) -> None:
        if isolate_registry:
            # create a new registry for this subclass, otherwise `get_instance` refers to the super class
            cls._instances = Registry[Self]()
        super().__init_subclass__(**kwargs)

    label: UniqueLabel = Field(...)   # required now, must be unique w/in class

    @field_validator("label")
    @classmethod
    def check_unique(cls, label_value: str):
        if cls.get_instance(label_value):
            raise ValueError(f"Instance {label_value} already registered.")
        return label_value

    @model_validator(mode="after")
    def register_instance(self):
        # This will raise value error if it already exists, but we check that explicitly as well
        self._instances.add(self)

    @classmethod
    def get_instance(cls, label: str) -> VT:
        # We don't want to get by uid, want to get by label
        # todo: add a 'search_everywhere' flag to look in superclass and subclass registries
        return cls._instances.find_one(label=label)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        # singletons can structure from class and label alone
        return { 'obj_cls': self.__class__.__name__, 'label': self.label }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        label = data.pop("label")  # this will throw a key error if it's not set properly
        this = obj_cls.get_instance(label)
        return this
