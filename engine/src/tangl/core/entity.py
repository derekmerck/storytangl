import dataclasses
from uuid import UUID, uuid4
from typing import Optional, Self, TypeVar, Generic, Iterator, ClassVar, Type, Callable, overload
import logging

from pydantic import BaseModel, Field
import shortuuid

from tangl.type_hints import StringMap, UniqueLabel, Tag, Predicate
from tangl.utils.hasher import hashing_func

logger = logging.getLogger(__name__)
match_logger = logging.getLogger(__name__ + '.match')
match_logger.setLevel(logging.WARNING)

class Entity(BaseModel):
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

    def get_label(self) -> str:
        if self.label is not None:
            return self.label
        else:
            return self.uid.hex

    def matches(self, *predicates: Callable[[Self], bool], **criteria) -> bool:
        # Callable predicate funcs on self were passed
        if not all([ p(self) for p in predicates ]):
            return False
        for k, v in criteria.items():
            # Sugar to test individual attributes
            if not hasattr(self, k):
                match_logger.debug(f'False: entity {self} has no attribute {k}')
                # Doesn't exist
                return False
            item = getattr(self, k)
            if (k.startswith("has_") or k.startswith("is_")) and callable(item):
                if not item(v):
                    # Is it a predicate attrib that returns false, like `has_tags={a,b,c}`?
                    match_logger.debug(f'False: entity {self}.{k}({v}) is False')
                    return False
            elif item != v:
                match_logger.debug(f'False: entity {self}.{k} != {v}')
                # Is it a straight comparison and not equal?
                return False
        return True

    # Any has methods should not have side effects as they may be called through **criteria args
    def has_tags(self, tags: set[Tag]) -> bool:
        return set(tags).issubset(self.tags)

    def is_instance(self, obj_cls: Type[Self]) -> bool:
        # helper func for matches
        return isinstance(self, obj_cls)

    @classmethod
    def _fields(cls, **criteria) -> Iterator[str]:
        # in general, we use opt-out metadata flags,
        # "don't use me for something"
        #
        # But it's easy enough to add metadata key defaults per-field as well, if eventually required.
        default_annotation = True
        for n, f in cls.model_fields.items():
            for k, v in criteria.items():
                extra = f.json_schema_extra or {}
                if (getattr(f, k, default_annotation) == v or
                        extra.get(k, default_annotation) == v):
                    yield n

    def _id_hash(self) -> bytes:
        # For persistent id's, use either the uid or a field annotated as UniqueLabel
        return hashing_func(self.uid, self.__class__)

    def __hash__(self) -> int:
        return hash((self.uid, self.__class__))

    def _state_hash(self) -> bytes:
        # Data thumbprint for auditing
        state_data = self.unstructure()
        logger.debug(state_data)
        return hashing_func(state_data)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        for f in self._fields(compare=True):
            if getattr(self, f) != getattr(other, f):
                return False
        return True

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
        exclude = set(self._fields(serialize=False))
        logger.debug(f"exclude={exclude}")
        data = self.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude_defaults=True,
            exclude=exclude,
        )
        data['uid'] = self.uid
        data["obj_cls"] = self.__class__
        # The 'obj_cls' key _may_ be flattened by some serializers.  If flattened as qual name,
        # it can be unflattened with `Entity.dereference_cls_name`
        return data


VT = TypeVar("VT", bound=Entity)  # registry value type
FT = TypeVar("FT", bound=Entity)  # find type within registry

class Registry(Entity, Generic[VT]):
    data: dict[UUID, VT] = Field(default_factory=dict,
                                 json_schema_extra={'serialize': False,
                                                    'compare': False})

    def add(self, entity: VT):
        self.data[entity.uid] = entity

    def get(self, key: UUID) -> Optional[VT]:
        if isinstance(key, str):
            raise ValueError(
                f"Use find_one(label='{key}') instead of get('{key}') to get-by-label"
            )
        return self.data.get(key)

    def remove(self, key: UUID):
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
    def find(self, *predicates: Callable[[VT], bool], is_instance: FT, **criteria) -> Iterator[FT]:
        ...

    @overload
    def find(self, *predicates: Callable[[VT], bool], **criteria) -> Iterator[VT]:
        ...

    def find(self, *predicates, **criteria):
        return filter(lambda x: x.matches(*predicates, **criteria), self.values())

    def find_one(self, *predicates: Callable[[VT], bool], **criteria) -> Optional[VT]:
        return next(self.find(*predicates, **criteria), None)

    def __contains__(self, key: UUID | str | VT) -> bool:
        if isinstance(key, UUID):
            return key in self.data
        elif isinstance(key, Entity):
            return key in self.data.values()
        elif isinstance(key, str):
            return key in self.all_labels()
        raise ValueError(f"Unexpected key type for contains {type(key)}")

    def all_labels(self) -> list[str]:
        return [x.label for x in self.data.values() if x.label is not None]

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

    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    def __repr__(self) -> str:
        s = self.label or self.short_uid()
        return f"<{self.__class__.__name__}:{s}>"


class Singleton(Entity):
    # can ignore uid in comparison, but label must be unique within class
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
    def get_instance(cls, label: str) -> Optional[Self]:
        return cls._instances.find_one(label=label)

    @classmethod
    def clear_instances(cls) -> None:
        cls._instances.clear()

    def _id_hash(self) -> bytes:
        # For persistent id's, either the uid or a field annotated as UniqueLabel
        return hashing_func(self.label, self.__class__)

    def __hash__(self) -> int:
        return hash((self.label, self.__class__))

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
