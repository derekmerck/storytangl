from typing import Optional, Self, Type, Protocol, Any
from uuid import UUID, uuid4
import logging

import shortuuid
from pydantic import Field, field_validator, ValidationInfo

from tangl.utils.base_model_plus import BaseModelPlus
from tangl.type_hints import UnstructuredData, Tag

logger = logging.getLogger(__name__)


class EntityP(Protocol):
    # Minimal public interface provided by Entity subclasses
    uid: UUID
    label: str
    tags: set[Tag]
    def matches(self, **criteria: Any) -> bool: ...
    @classmethod
    def structure(cls, data: UnstructuredData) -> Self: ...
    def unstructure(self) -> UnstructuredData: ...


class Entity(BaseModelPlus):
    uid: UUID = Field(default_factory=uuid4)
    label_: Optional[str] = Field(None, alias="label")
    tags: set[Tag] = Field(default_factory=set)

    # MATCHING

    def matches(self, **criteria) -> bool:
        for k, v in criteria.items():
            if k.startswith("has_") and hasattr(self, k):
                logger.debug(f"Calling has_{k}({v})")
                func = getattr(self, k)
                if not func(v):
                    return False
            elif getattr(self, k, None) != v:
                logger.debug(f"Comparing self.{k} == {v}")
                return False
        return True

    @classmethod
    def filter_by_criteria(cls, *entities, **criteria):
        return filter(lambda e: e.matches(**criteria), *entities)

    def has_cls(self, obj_cls: Type[Self]) -> bool:
        return isinstance(self, obj_cls)

    def has_tags(self, *tags: Tag) -> bool:
        logger.debug(f"Comparing query tags {tags} against {self!r} with tags={self.tags}")
        if len(tags) == 1 and tags[0] is None:
            return len(self.tags) == 0  # check for empty
        if len(tags) == 1 and isinstance(tags[0], (list, set)):
            tags = tags[0]
        return set(tags).issubset(self.tags)

    # STRUCTURING

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls", cls)
        return obj_cls(**data)

    def unstructure(self, **kwargs) -> UnstructuredData:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("exclude_defaults", True)
        kwargs.setdefault("by_alias", True)
        data = self.model_dump(**kwargs)
        data['uid'] = self.uid  # May not be included b/c it's considered default/unset
        data['obj_cls'] = self.__class__
        return data

    # UTILITIES

    @property
    def label(self) -> str:
        return self.label_ or self.short_uid

    @property
    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self.label}>"

    dirty: bool = False
    # indicator that entity has been tampered with, invalidates certain debugging
