from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class Entity(BaseModel):
    """Base class for everything that exists and can be named, tagged, or serialized."""
    uid: UUID = Field(default_factory=uuid4)
    label: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True

    def match(self, **features) -> bool:
        for k, v in features.items():
            if getattr(self, k, None) != v:
                return False
        return True

    def summary(self) -> str:
        return self.label or f"{self.__class__.__name__}<{str(self.uid)[:6]}>"