from __future__ import annotations
from uuid import UUID, uuid4
from typing import Optional, Self, Iterator, Type, Callable
import logging
from enum import Enum

from pydantic import BaseModel, Field, field_validator
import shortuuid

from tangl.type_hints import StringMap, Tag, Predicate, Identifier
from tangl.utils.hashing import hashing_func
from tangl.utils.base_model_plus import BaseModelPlus
from tangl.utils.sanitize_str import sanitise_str

logger = logging.getLogger(__name__)
match_logger = logging.getLogger(__name__ + '.match')
match_logger.setLevel(logging.WARNING)

def is_identifier(func: Callable) -> Callable:
    setattr(func, '_is_identifier', True)
    return func

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
    uid: UUID = Field(default_factory=uuid4, json_schema_extra={'is_identifier': True})
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

    @is_identifier
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

    def get_identifiers(self) -> set[Identifier]:
        result = set()
        for f in self._fields(is_identifier=(True, False)):
            value = getattr(self, f)
            if value is not None:
                result.add(value)
        for ff in self.__class__.__dict__.values():
            if callable(ff) and getattr(ff, '_is_identifier', False):
                value = ff(self)
                if value is not None:
                    result.add(value)
        return result

    def has_alias(self, alias: Identifier) -> bool:
        return alias in self.get_identifiers()

    def has_tags(self, *tags: Tag) -> bool:
        # Normalize args to set[Tag]
        if len(tags) == 1 and isinstance(tags[0], set):
            tags = tags[0]  # already a set of tags
        else:
            tags = set(tags)
        match_logger.debug(f"Comparing query tags {tags} against {self.tags}")
        return tags.issubset(self.tags)

    def is_instance(self, obj_cls: Type[Self]) -> bool:
        # helper func for matches
        return isinstance(self, obj_cls)

    @is_identifier
    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    is_dirty_: bool = Field(default=False, alias="is_dirty")
    # audit indicator that the entity has been tampered with, invalidates certain debugging

    @property
    def is_dirty(self):
        return self.is_dirty_

    def __repr__(self) -> str:
        s = self.label or self.short_uid()
        return f"<{self.__class__.__name__}:{s}>"

    @is_identifier
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
            # exclude_unset=True,  # too many things are mutated after being initially unset
            exclude_none=True,
            exclude_defaults=True,
            # exclude=exclude,
        )
        data['uid'] = self.uid  # uid is considered Unset initially
        data["obj_cls"] = self.__class__
        # The 'obj_cls' key _may_ be flattened by some serializers.  If flattened as qual name,
        # it can be unflattened with `Entity.dereference_cls_name`
        return data


class Conditional(BaseModel):
    predicate: Optional[Predicate] = None

    def available(self, ns: StringMap) -> bool:
        return self.predicate is None or self.predicate(ns) is True
