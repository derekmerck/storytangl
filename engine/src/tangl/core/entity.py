from __future__ import annotations
from uuid import UUID, uuid4
from typing import Optional, Self, TypeVar, Generic, Iterator, ClassVar, Type, Callable, overload, Iterable
import logging

from pydantic import BaseModel, Field, field_validator, ConfigDict
import shortuuid

from tangl.type_hints import StringMap, UniqueLabel, Tag
from tangl.utils.hasher import hashing_func
from tangl.utils.base_model_plus import BaseModelPlus
from tangl.utils.sanitize_str import sanitise_str

logger = logging.getLogger(__name__)
match_logger = logging.getLogger(__name__ + '.match')
match_logger.setLevel(logging.WARNING)

class Entity(BaseModelPlus):
    """
    Entity is the base class for all managed objects.

    Main features:
    - carry metadata with uid, convenience label and tags
    - searchable by any characteristic/attribute or "has_" method
    - compare by value, hash by id
    - provide self-casting serialization (class mro provides part of scope hierarchy)

    Entity classes can be further specialized to carry:
    - locally scoped data (a mapping of identifiers to values that can be chained into a scoped namespace)
    - shape (relationships and a relationship manager, i.e., nodes, edges, subgraphs, and a graph manager)
    - domain/class behaviors (decorated handlers, functions on entities that are managed with handler registries)
    - predicates (an evaluation behavior that determines if conditions are satisfied for a given task)

    Entities can be gathered and discovered with the `Registry` class.

    Singleton entities with a common api can be registered by unique label using the `Singleton` class.
    """
    uid: UUID = Field(default_factory=uuid4)
    label: Optional[str] = None
    tags: set[Tag] = Field(default_factory=set)
    # tag syntax can be used by the _parser_ as sugar for various attributes
    # - indicate domain memberships       domain
    # - automatically set default values  .str=100
    # - indicate relationships            @other_node.friendship=+10

    @field_validator('label', mode="after")
    @classmethod
    def _sanitize_label(cls, value):
        if isinstance(value, str):
            value = sanitise_str(value)
        return value

    def get_label(self) -> str:
        if self.label is not None:
            return self.label
        else:
            return self.short_uid()

    def matches(self, predicate: Callable[[Entity], bool] = None, **criteria) -> bool:
        # Callable predicate funcs on self were passed
        if predicate is not None and not predicate(self):
            return False
        for k, v in criteria.items():
            # Sugar to test individual attributes
            if not hasattr(self, k):
                match_logger.debug(f'False: entity {self!r} has no attribute {k}')
                # Doesn't exist
                return False
            item = getattr(self, k)
            if (k.startswith("has_") or k.startswith("is_")) and callable(item):
                if not item(v):
                    # Is it a predicate attrib that returns false, like `has_tags={a,b,c}`?
                    match_logger.debug(f'False: entity {self!r}.{k}({v}) is False')
                    return False
                match_logger.debug(f'True: entity {self!r}.{k}({v}) is True')
            elif item != v:
                match_logger.debug(f'False: entity {self!r}.{k} != {v}')
                # Is it a straight comparison and not equal?
                return False
        return True

    @classmethod
    def filter_by_criteria(cls, values, **criteria) -> Iterator[Self]:
        return filter(lambda x: x.matches(**criteria), values)

    # Any `has_` methods should not have side effects as they may be called through **criteria args
    def has_tags(self, *tags: Tag) -> bool:
        # Normalize args to set[Tag]
        if isinstance(tags, Tag):
            tags = { tags }
        else:
            tags = set(tags)
        match_logger.debug(f"Comparing query tags {set(tags)} against {self.tags}")
        return tags.issubset(self.tags)

    def is_instance(self, obj_cls: Type[Self]) -> bool:
        # helper func for matches
        return isinstance(self, obj_cls)

    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    def __repr__(self) -> str:
        s = self.label or self.short_uid()
        return f"<{self.__class__.__name__}:{s}>"

    def _id_hash(self) -> bytes:
        # For persistent id's, use either the uid or a field annotated as UniqueLabel
        return hashing_func(self.uid, self.__class__)

    # Entities are not frozen, should not be hashed or used in sets, use the uid directly if necessary
    # def __hash__(self) -> int:
    #     return hash((self.uid, self.__class__))

    def _state_hash(self) -> bytes:
        # Data thumbprint for auditing
        state_data = self.unstructure()
        logger.debug(state_data)
        return hashing_func(state_data)

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        """
        Structure a string-keyed dict of unflattened data into an object of its
        declared class type.
        """
        _data = dict(data)  # local copy
        obj_cls = _data.pop("obj_cls", cls)
        # This key _should_ be unflattened by the serializer when necessary, but if not,
        # we can try to unflatten it as the qualified name against Entity
        if isinstance(obj_cls, str):
            obj_cls = Entity.dereference_cls_name(obj_cls)
        return obj_cls(**_data)

    @classmethod
    def dereference_cls_name(cls, name: str) -> Type[Self]:
        # todo: Should memo-ize this
        if name == cls.__qualname__:
            return cls
        for _cls in cls.__subclasses__():
            if x := _cls.dereference_cls_name(name):
                return x

    def unstructure(self) -> StringMap:
        """
        Unstructure an object into a string-keyed dict of unflattened data.
        """
        # Just use field attrib 'exclude' when using Pydantic (missing from dataclass)
        # exclude = set(self._fields(serialize=False))
        # logger.debug(f"exclude={exclude}")
        data = self.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude_defaults=True,
            # exclude=exclude,
        )
        data['uid'] = self.uid
        data["obj_cls"] = self.__class__
        # The 'obj_cls' key _may_ be flattened by some serializers.  If flattened as qual name,
        # it can be unflattened with `Entity.dereference_cls_name`
        return data

    is_dirty: bool = False
    # audit indicator that the entity has been tampered with, invalidates certain debugging


VT = TypeVar("VT", bound=Entity)  # registry value type
FT = TypeVar("FT", bound=Entity)  # find type within registry

class Registry(Entity, Generic[VT]):
    data: dict[UUID, VT] = Field(default_factory=dict,
                                 json_schema_extra={'compare': False})

    def add(self, entity: VT):
        self.data[entity.uid] = entity

    def get(self, key: UUID) -> Optional[VT]:
        if isinstance(key, str):
            raise ValueError(
                f"Use find_one(label='{key}') instead of get('{key}') to get-by-label"
            )
        return self.data.get(key)

    def remove(self, key: VT | UUID):
        if isinstance(key, Entity):
            key = key.uid
        if not isinstance(key, UUID):
            raise ValueError(f"Wrong type for remove key {key}")
        self.data.pop(key)

    def keys(self) -> Iterator[UUID]:
        return iter(self.data.keys())

    def values(self) -> Iterator[VT]:
        return iter(self.data.values())

    def __bool__(self) -> bool:
        return bool(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def clear(self) -> None:
        self.data.clear()

    @overload
    def find_all(self, *, is_instance: FT, **criteria) -> Iterator[FT]:
        ...

    @overload
    def find_all(self, **criteria) -> Iterator[VT]:
        ...

    def find_all(self, **criteria):
        return Entity.filter_by_criteria(self.values(), **criteria)

    def find_one(self, **criteria) -> Optional[VT]:
        return next(self.find_all(**criteria), None)

    def __contains__(self, key: UUID | str | VT) -> bool:
        if isinstance(key, UUID):
            return key in self.data
        elif isinstance(key, Entity):
            return key in self.data.values()
        elif isinstance(key, str):
            return key in self.all_labels()
        raise ValueError(f"Unexpected key type for contains {type(key)}")

    def all_labels(self) -> list[str]:
        return [x.get_label() for x in self.data.values() if x.get_label() is not None]

    def all_tags(self) -> set[str]:
        tags = set()
        for x in self.data.values():
            tags.update(x.tags)
        return tags

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        _data = data.pop("_data", {})
        obj = super().structure(data)  # type: Self
        for v in _data:
            _obj = Entity.structure(v)
            obj.add(_obj)
        return obj

    def unstructure(self) -> StringMap:
        data = super().unstructure()
        data["_data"] = []
        for v in self.data.values():
            data['_data'].append(v.unstructure())
        return data

class Singleton(Entity):
    # can ignore uid in comparison, but label must be unique within class

    model_config = ConfigDict(frozen=True)

    label: UniqueLabel
    _instances: ClassVar[Registry[Self]] = Registry()

    def __init_subclass__(cls, **kwargs):
        cls._instances = Registry()  # keep an instance registry per subclass
        super().__init_subclass__()

    def __init__(self, *, label: str, **kwargs):
        if self.get_instance(label) is not None:
            raise ValueError(f"Singleton with label {label} already exists")
        super().__init__(label=label, **kwargs)
        self._instances.add(self)

    @classmethod
    def get_instance(cls, key: UUID | UniqueLabel) -> Optional[Self]:
        if isinstance(key, UUID):
            return cls._instances.get(key)
        elif isinstance(key, UniqueLabel):
            return cls.find_instance(label=key)
        raise ValueError(f"Unexpected key type for get instance {key}")

    @classmethod
    def find_instance(cls, **criteria) -> Optional[Self]:
        return cls._instances.find_one(**criteria)

    @classmethod
    def clear_instances(cls) -> None:
        cls._instances.clear()

    @classmethod
    def all_instances(cls) -> Iterator[Self]:
        return cls._instances.values()

    @classmethod
    def all_instance_labels(cls) -> list[str]:
        return cls._instances.all_labels()

    def _id_hash(self) -> bytes:
        # For persistent id's, either the uid or a field annotated as UniqueLabel
        return hashing_func(self.__class__, self.label)

    def __hash__(self) -> int:
        return hash((self.__class__, self.label))

    @classmethod
    def structure(cls, data: dict) -> Self:
        obj_cls, label = data['obj_cls'], data['label']
        return obj_cls.get_instance(label)

    def unstructure(self) -> StringMap:
        return {'obj_cls': self.__class__, 'label': self.label}

    def __reduce__(self) -> tuple:
        return self.__class__.get_instance, (self.label,)


class Conditional(BaseModel):
    predicate: Optional[Predicate] = None

    def available(self, ns: StringMap) -> bool:
        return self.predicate is None or self.predicate(ns) is True
