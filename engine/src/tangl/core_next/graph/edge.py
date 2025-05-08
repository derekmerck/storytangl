from uuid import UUID
from pydantic.dataclasses import dataclass

@dataclass
class Edge:
    successor_id: UUID
    predecessor_id: UUID | None = None
    return_after: bool = False   # jump‑return
