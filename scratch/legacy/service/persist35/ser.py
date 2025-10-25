# tangl/persist/ser.py
from __future__ import annotations
from typing import Any, Protocol

class Serializer(Protocol):
    def dumps(self, obj: Any) -> bytes: ...
    def loads(self, buf: bytes) -> Any: ...

class PickleSerializer:
    def dumps(self, obj: Any) -> bytes:
        import pickle; return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    def loads(self, buf: bytes) -> Any:
        import pickle; return pickle.loads(buf)