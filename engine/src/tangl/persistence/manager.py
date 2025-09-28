from contextlib import contextmanager
from logging import getLogger
from uuid import UUID
from typing import Type, ClassVar, Mapping

from tangl.type_hints import HasUid, ClassName, FlatData, UnstructuredData
from tangl.utils.is_valid_uuid import is_valid_uuid
from .storage import StorageProtocol
from .serializers import SerializationHandlerProtocol
from .structuring import StructuringHandlerProtocol

logger = getLogger(__name__)

class PersistenceManager(Mapping[UUID, HasUid]):
    """
    This is a relatively generic data persistence framework.

    It is implemented as a pipeline with three parts:
      - a _structuring_ handler that implements `structure` and `unstructure` for a class that has a `uid` field
      - a _serialization_ handler that implements `serialize` and `deserialize` for dicts, like pickle, yaml, bson
      - a flat-data _storage_ backend that implements `read` and `write` for str|bytes, like in-mem, files, redis, mongodb
    """

    obj_cls_map: ClassVar[dict[ClassName, Type[HasUid]]] = dict()

    def __init__(self,
                 structuring: StructuringHandlerProtocol = None,
                 serializer: SerializationHandlerProtocol = None,
                 storage: StorageProtocol = None):

        self.structuring = structuring
        self.serializer = serializer
        self.storage = storage

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
            structured = self.structuring.structure( unstructured, self.obj_cls_map )
        else:
            structured = unstructured

        return structured

    def save(self, structured: HasUid):
        # stash the incoming classes
        if structured.__class__.__name__ not in self.obj_cls_map:
            self.obj_cls_map[structured.__class__.__name__] = structured.__class__

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
        # todo: service layer can deal with locking the context if it's in a threaded environment

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
