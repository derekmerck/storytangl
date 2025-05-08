from uuid import UUID
from ..entity import Entity
class Edge(Entity):
    src_uid: UUID
    dst_uid: UUID
    label: str | None = None