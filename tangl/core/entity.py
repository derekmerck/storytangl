from __future__ import annotations
from typing import Self, Optional, Any, Iterable, Type
from uuid import UUID, uuid4
import functools
from fnmatch import fnmatch
import logging

import shortuuid
from pydantic import BaseModel, Field, model_validator, field_serializer

from tangl.type_hints import UnstructuredData, Tag, Identifier, Hash
from tangl.utils.dereference_obj_cls import dereference_obj_cls

logger = logging.getLogger(__name__)

class Entity(BaseModel):

    #: Consumed by metaclass for dereference, if necessary
    obj_cls: str | Type[Self] = Field(init_var=True, default=None)  
    uid: UUID = Field(default_factory=uuid4)
    label: str = None
    tags: set[Tag] = Field(default_factory=set)
    data_hash: Hash = None
    domain: str = None  # holder for user-defined domain of entity

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
        """Check all tags are in self.tags"""
        if len(tags) == 1 and isinstance(tags[0], (list, set)):
            tags = tags[0]
        return set(tags).issubset(self.tags)

    def get_identifiers(self) -> set[Identifier]:
        # Extend this in subclasses that want to include additional findable instance names
        return { self.uid, self.label, self.data_hash }

    def has_alias(self, *aliases: Identifier) -> bool:
        """Test if any alias is in self.identifiers"""
        if len(aliases) == 1 and isinstance(aliases[0], (list, set)):
            aliases = aliases[0]
        identifiers = self.get_identifiers()
        identifiers = { x for x in identifiers if x }  # discard empty/falsy identifiers
        return bool( set(aliases).intersection(identifiers) )

    def has_cls(self, obj_cls: str | type[Self]) -> bool:
        """Test if entity is instance of the given class"""
        cls_ = dereference_obj_cls(self.__class__, obj_cls)
        return isinstance(self, cls_)

    @classmethod
    def class_distance(cls, obj_cls: str | type[Self]) -> Optional[int]:
        """
        Get distance to class in MRO. Returns None if not in MRO.
        Distance of 0 means exact class, 1 means immediate parent, etc.
        """
        cls_ = dereference_obj_cls(cls, obj_cls)
        return cls.__mro__.index(cls_)

    def has_domain(self, domain: str) -> bool:
        if not isinstance(self.domain, str) or not isinstance(domain, str):
            return False
        if '*' in domain:
            # compare strings with * in test with fnmatch
            return fnmatch(self.domain, domain)
        return self.domain == domain

    def matches_criteria(self, **criteria) -> bool:
        # Must match all

        if not criteria:
            raise ValueError("No criteria specified, return value is undefined.")

        for criterion, value in criteria.items():
            # try any explicitly defined tests first
            if hasattr(self, f"has_{criterion}"):
                return getattr(self, f"has_{criterion}")(value)
            # if the attribute is directly available, try comparing it
            elif hasattr(self, criterion):
                return getattr(self, criterion) == value
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

