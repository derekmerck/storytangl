from __future__ import annotations
from uuid import UUID

from .type_hints import StringMap
from .entity import Entity, TaskHandler
from .graph import Graph

# ----------------
# Persistence-related Type Hints
# ----------------
StructuredData = Entity
UnstructuredData = StringMap
SerializedData = str | bin


# ----------------
# Persistence
# ----------------

class StructuringHandler(TaskHandler):
    def unstructure_graph(self, graph: Graph) -> UnstructuredData: ...
    def structure_graph(self, data: UnstructuredData) -> Graph: ...
    def unstructure_entity(self, entity: Entity) -> UnstructuredData: ...
    def structure_entity(self, data: UnstructuredData) -> Entity: ...

class SerializationHandler(TaskHandler):
    def serialize_data(self, data: UnstructuredData) -> SerializedData: ...
    def deserialize_data(self, data: SerializedData) -> UnstructuredData: ...

class PersistenceManager(TaskHandler, dict[UUID, SerializedData]):
    serialization_handler: SerializationHandler
    structuring_handler: StructuringHandler
    def __getitem__(self, key: UUID) -> StructuredData: ...
    def __setitem__(self, key: UUID, value: StructuredData) -> None: ...

