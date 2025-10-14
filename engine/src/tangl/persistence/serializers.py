from typing import Protocol, ClassVar
import pickle
import json
from datetime import datetime
from uuid import UUID
import inspect
import types

try:
    from bson import BSON
    from bson.codec_options import CodecOptions, TypeRegistry, TypeEncoder, TypeDecoder, UuidRepresentation
    HAS_BSON = True
except ImportError:
    BSON = TypeEncoder = object
    TypeRegistry = CodecOptions = lambda *args, **kwargs: None
    UuidRepresentation = types.SimpleNamespace(STANDARD=None)
    HAS_BSON = False

import yaml
import tangl.utils.setup_yaml

from tangl.type_hints import FlatData, UnstructuredData, HasUid


class SerializationHandlerProtocol(Protocol):

    @classmethod
    def serialize(cls, unstructured: UnstructuredData) -> FlatData: ...

    @classmethod
    def deserialize(cls, flat: FlatData) -> UnstructuredData: ...


class NoopSerializationHandler:
    # This is an identity serializer that can use pythonic mapping as
    # storage, like an in-memory dict.

    @classmethod
    def serialize(cls, unstructured: UnstructuredData) -> UnstructuredData:
        return unstructured

    @classmethod
    def deserialize(cls, unstructured: UnstructuredData) -> UnstructuredData:
        return unstructured


class PickleSerializationHandler:
    # This can also accept structured data, objects need not be pre-unstructured
    # and post-structured.  It requires a binary storage backend (binary files or
    # Redis).

    @classmethod
    def serialize(cls, pickleable_data: HasUid) -> bytes:
        flat = pickle.dumps( pickleable_data )
        return flat

    @classmethod
    def deserialize(cls, flat: bytes) -> HasUid:
        pickleable_data = pickle.loads(flat)
        return pickleable_data


class JsonSerializationHandler:
    # Requires a flat text storage backend

    class MyJsonEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, set):
                return list(o)
            elif isinstance(o, type):
                return o.__name__
            elif isinstance(o, datetime):
                return o.isoformat()
            elif isinstance(o, UUID):
                return o.hex
            try:
                return super().default(o)  # Attempt to serialize using super class
            except TypeError:
                return str(o)  # Fallback to converting to string if not serializable

    @classmethod
    def serialize(cls, unstructured: UnstructuredData) -> str:
        flat = json.dumps(unstructured, cls=JsonSerializationHandler.MyJsonEncoder)
        return flat

    @staticmethod
    def decode_object_hook(obj):
        for key, value in obj.items():
            try:
                obj[key] = datetime.fromisoformat(value)
            except (TypeError, ValueError):
                try:
                    obj[key] = UUID(value)
                except (ValueError, AttributeError, TypeError):
                    pass
        return obj

    @classmethod
    def deserialize(self, flat: str) -> UnstructuredData:
        unstructured = json.loads(flat, object_hook=JsonSerializationHandler.decode_object_hook)
        return unstructured


class YamlSerializationHandler:
    # Requires a flat text storage backend

    @classmethod
    def serialize(cls, unstructured: UnstructuredData) -> str:
        flat = yaml.dump(unstructured)
        return flat

    @classmethod
    def deserialize(cls, flat: str) -> UnstructuredData:
        unstructured = yaml.load(flat, Loader=yaml.FullLoader)
        return unstructured


class BsonSerializationHandler:
    # Requires a binary storage backend (binary files or mongodb).
    # When using pymongo, data is de-serialized automatically.

    class SetEncoder(TypeEncoder):
        python_type = set  # the Python type acted upon by this type codec

        def transform_python(self, value):
            return list(value)

    @staticmethod
    def fallback_encoder(value):  # pragma: no cover
        # Check if the value is a class encode it by name
        if inspect.isclass(value):
            return value.__name__
        return value

    bson_codec_options: ClassVar = CodecOptions(
        type_registry=TypeRegistry([SetEncoder()],
                                   fallback_encoder=fallback_encoder),
        uuid_representation=UuidRepresentation.STANDARD)

    @classmethod
    def serialize(cls, unstructured: UnstructuredData) -> bytes:
        if not HAS_BSON:
            raise ImportError
        # Need to include key at encoding for pymongo
        unstructured['_id'] = unstructured['uid']
        # if 'obj_cls' in unstructured:
        #     unstructured['obj_cls'] = unstructured['obj_cls'].__name__
        return BSON.encode(unstructured, codec_options=cls.bson_codec_options)

    @classmethod
    def deserialize(cls, flat: bytes) -> UnstructuredData:
        if isinstance(flat, dict):
            return flat   # pymongo already decoded it
        if not HAS_BSON:
            raise ImportError
        return BSON(flat).decode(codec_options=cls.bson_codec_options)
