from functools import cached_property
from typing import Any, Dict, List, Optional, Self, Callable, Type
from uuid import UUID, uuid4
import logging

from pydantic import BaseModel, Field, field_validator, field_serializer, ValidationInfo

from ..type_hints import StringMap, UnstructuredData, Predicate

logger = logging.getLogger(__name__)

class Entity(BaseModel):
    """
    Basic class for all managed entities, provides each entity with a unique identifier,
    label, tags, metadata, and optional predicate for conditional checks.

    This class provides methods for matching criteria, validating default labels,
    serializing tags, and checking whether certain conditions are satisfied or not.
    It also supports structuring and unstructuring operations for data transformation.

    :ivar uid: Unique identifier for the entity.
    :type uid: UUID
    :ivar label: Optional label string for the entity, defaults to a substring of the
        UID if not provided.
    :type label: Optional[str]
    :ivar tags: List of tags associated with the entity.
    :type tags: List[str]
    :ivar metadata: Dictionary containing metadata related to the entity.
    :type metadata: Dict[str, Any]
    :ivar predicate: Optional callable that takes a StringMap object and returns a
        boolean. Used to determine satisfaction of conditions.
    :type predicate: Optional[Callable[[StringMap], bool]]
    """
    uid: UUID = Field(default_factory=uuid4)
    label: Optional[str] = Field(None, validate_default=True)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    predicate: Optional[Predicate] = None

    @field_validator("label", mode="before")
    @classmethod
    def _default_label(cls, value, info: ValidationInfo) -> Optional[str]:
        if not value:
            value = str(info.data.get("uid"))[0:6]
        return value

    @field_serializer("tags")
    @classmethod
    def _as_list(cls, value: Any) -> List[str]:
        return list(value)

    def match(self, **criteria) -> bool:
        for k, v in criteria.items():
            if k.startswith("has_") and hasattr(self, k):
                func = getattr(self, k)
                if not func(v):
                    return False
            elif getattr(self, k, None) != v:
                return False
        return True

    # predicate gating is built-in b/c its used extensively
    def is_satisfied(self, *, ctx: StringMap, **kwargs) -> bool:
        if self.predicate is None:
            logger.debug("No predicate, return True")
            return True
        return self.predicate(ctx)

    def has_cls(self, obj_cls: Type[Self]) -> bool:
        return isinstance(self, obj_cls)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self.label}>"

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls", cls)
        return obj_cls(**data)

    def unstructure(self) -> UnstructuredData:
        data = self.model_dump()
        data['obj_cls'] = self.__class__
        return data
