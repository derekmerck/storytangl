from contextlib import contextmanager
import logging
from uuid import UUID
from typing import Type, Mapping

from tangl.type_hints import HasUid, ClassName, FlatData, UnstructuredData
from tangl.utils.is_valid_uuid import is_valid_uuid
from .storage import StorageProtocol
from .serializers import SerializationHandlerProtocol
from .structuring import StructuringHandlerProtocol

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class PersistenceManager(Mapping[UUID, HasUid]):
    """
    This is a relatively generic data persistence framework.

    It is implemented as a pipeline with three parts:
      - a _structuring_ handler that implements `structure` and `unstructure` for a class that has a `uid` field
      - a _serialization_ handler that implements `serialize` and `deserialize` for dicts, like pickle, yaml, bson
      - a flat-data _storage_ backend that implements `read` and `write` for str|bytes, like in-mem, files, redis, mongodb
    """

    def __init__(self,
                 structuring: StructuringHandlerProtocol = None,
                 serializer: SerializationHandlerProtocol = None,
                 storage: StorageProtocol = None,
                 kind_map: Mapping[ClassName, Type[HasUid]] | None = None):

        self.structuring = structuring
        self.serializer = serializer
        self.storage = storage
        self.kind_map = dict(kind_map or {})

    def register_kind(self, kind: Type[HasUid]) -> None:
        """Register one top-level class that this manager may restore."""
        self.kind_map[kind.__name__] = kind

    def register_kinds(self, *kinds: Type[HasUid]) -> None:
        """Register the top-level resource classes owned by one composition root."""
        for kind in kinds:
            self.register_kind(kind)

    def load(self, uid: UUID, data: FlatData = None) -> HasUid:

        if isinstance(uid, str) and is_valid_uuid( uid ):
            uid = UUID(uid)

        if self.storage is not None:
            flat = self.storage[uid]
        elif data:
            flat = data
        else:
            raise ValueError("Must have either uid or data param")

        if self.serializer:
            unstructured = self.serializer.deserialize( flat )
        else:
            unstructured = flat

        if self.structuring:
            structured = self.structuring.structure(unstructured, self.kind_map)
        else:
            structured = unstructured

        return structured

    def save(self, structured: HasUid):
        # stash the incoming classes
        self.register_kind(structured.__class__)

        if self.structuring:
            unstructured = self.structuring.unstructure( structured )
        else:
            unstructured = structured

        if self.serializer:
            flat = self.serializer.serialize( unstructured )
        else:
            flat = unstructured

        if self.storage is not None:
            if hasattr(structured, 'uid'):
                uid = structured.uid
            elif isinstance(structured, dict) and 'uid' in structured:
                uid = structured['uid']
            else:
                raise KeyError(f"Unable to infer key for {structured}")
            self.storage[uid] = flat
        else:
            return flat

    def remove(self, uid: UUID):
        del self.storage[uid]

    @contextmanager
    def open(self, uid: UUID, write_back: bool = False):
        """"
        Data in a context manager with optional write-back on exit
        """
        # Threaded callers own synchronization at the service boundary.

        if uid not in self:
            raise KeyError(f"Unable to find {uid}")
        structured = self.load(uid)
        yield structured
        if write_back:
            self.save(structured)

    def __contains__(self, item):

        if isinstance(item, UUID):
            pass
        elif isinstance(item, str) and is_valid_uuid( item ):
            item = UUID(item)
        elif hasattr(item, 'uid'):
            item = item.uid
        return self.storage.__contains__(item)

    # Mapping-like accessors

    def __getitem__(self, key: UUID) -> HasUid:
        return self.load(key)

    def __setitem__(self, _, value):
        self.save(value)

    def __delitem__(self, key: UUID):
        self.remove(key)

    def __len__(self) -> int:
        return len(self.storage)

    def __iter__(self):
        return iter(self.storage)

    def __bool__(self):
        return bool(self.storage)
