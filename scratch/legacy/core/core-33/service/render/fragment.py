from dataclasses import dataclass
from uuid import UUID

from ...entity import Entity

@dataclass(kw_only=True)
class Fragment(Entity):
    node_uid: UUID
    text: str
    media: str | None = None
