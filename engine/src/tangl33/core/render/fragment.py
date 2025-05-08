from uuid import UUID
from ..entity import Entity

class Fragment(Entity):
    node_uid: UUID
    text: str
    media: str | None = None
