from __future__ import annotations
from uuid import UUID, uuid4
from pathlib import Path
from typing import ClassVar, Self, TypeAlias, TypeVar, Union, Type
from functools import total_ordering
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from shortuuid import ShortUUID

from tangl.type_hints import StringMap, UnstructuredData, Hash, Identifier
from tangl.utils.hashing import hashing_func

##############################
# CORE
##############################

class HasIdentity(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    label: str = None
    tags: set[str] = Field(default_factory=set)

    def shortuid(self):
        ShortUUID.encode(self.uid)

    def get_label(self):
        return self.label or self.shortuid()

    def has_kind(self, kind: Kind) -> bool:
        return issubclass(self.__class__, kind)

    def has_tags(self, *tags: str) -> bool:
        return set(tags).issubset(self.tags)

    def has_id(self, name: Identifier):
        aliases = self.get_identifiers()
        return name in aliases

    def evolve(self, **updates) -> Self:
        return self.model_copy(update=updates)

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.get_label()}>"


Entity = HasIdentity
Kind: TypeAlias = Type[Entity]

# Entity Mixins

class Structurable(BaseModel):

    def unstructure(self) -> UnstructuredData:
        data = self.model_dump()
        data.setdefault('uid', self.uid)  # in case model_dump is ignoring UNSET
        data['kind'] = self.__class__
        return data

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        cls_ = data.pop('kind')
        return cls_(**data)

    @classmethod
    def clone_instance(cls, inst: Self, **updates) -> Self:
        data = inst.unstructure()
        data.update(updates)
        return cls.structure(data)

    def clone(self, **updates) -> Self:
        return self.clone_instance(self, **updates)

    def __sub__(self, other: Self) -> StringMap:
        """
        >>> foo = Structurable(label="foo")
        >>> bar = Structurable(label='bar')
        >>> diff = bar - foo
        { 'label': 'bar' }
        >>> assert foo.evolve(**diff) == bar
        """
        this = self.unstructure()
        that = other.unstructure()
        return dict_diff(this, that)

    @property
    def state_hash(self) -> Hash:
        data = self.unstructure()
        return hashing_func(data)

    def __eq__(self, other: Self) -> bool:
        # eq by state
        return self.unstructure() == other.unstructure()

class HasContent(BaseModel):
    content: str | bytes | Path | StringMap = None

    def get_content(self):
        return self.content

    @property
    def content_hash(self):
        return hashing_func(self.content)

    def __eq__(self, other: Self) -> bool:
        return self.content_hash == other.content_hash

class HasState(BaseModel):
    locals: StringMap = Field(default_factory=dict)


@total_ordering
class HasOrder(BaseModel):

    # This is broken into two pieces b/c creation-order is runtime reset
    # and ts may be shared
    _creation_order: ClassVar[int] = 0
    ts: datetime = Field(default_factory=datetime.now)
    creation_order: int = None

    @field_validator("creation_order")
    @classmethod
    def _set_creation_order(cls, data):
        if data is None:
            cls._creation_order += 1
            return cls._creation_order
        return data

    def sort_key(self) -> tuple:
        return self.ts, self.creation_order
