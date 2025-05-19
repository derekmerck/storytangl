from functools import cached_property
from typing import Any, Dict, List, Optional, Self, Callable, Type
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, field_serializer, ValidationInfo

from ..type_hints import Context, UnstructuredData

class Entity(BaseModel):
    """Base class for everything that exists and can be named, tagged, or serialized."""
    uid: UUID = Field(default_factory=uuid4)
    label: Optional[str] = Field(None, validate_default=True)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    predicate: Optional[Callable[[Context], bool]] = None

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
    def satisfied(self, *, ctx: Context, **kwargs) -> bool:
        if self.predicate is None:
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
