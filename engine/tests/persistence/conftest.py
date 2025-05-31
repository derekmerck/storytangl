from pathlib import Path

import pytest

try:
    from tangl.config import settings
except ImportError:
    settings = {}
from tangl.persistence.serializers import *
from tangl.persistence.storage import *
from tangl.persistence.structuring import StructuringHandler

serializers = [NoopSerializationHandler,
               PickleSerializationHandler,
               JsonSerializationHandler,
               YamlSerializationHandler,
               BsonSerializationHandler]

def get_serializer(serializer_cls):
    if serializer_cls is BsonSerializationHandler and not (settings and settings.service.apis.mongo.enabled):
        pytest.skip("Skipping BSON")
    return serializer_cls

@pytest.fixture(params=serializers)
def serializer(request):
    return get_serializer(request.param)

storage_backends = [InMemoryStorage, FileStorage, RedisStorage, MongoStorage]

def get_storage(storage_cls, base_path: Path = None, is_binary: bool = False):
    if storage_cls is RedisStorage:
        if not settings or not settings.service.apis.redis.enabled:
            pytest.skip("Skipping Redis")
        else:
            storage = storage_cls(db=15)
            storage.clear()
            return storage
    elif storage_cls is MongoStorage:
        if not settings or not settings.service.apis.mongo.enabled:
            pytest.skip("Skipping Mongo")
        else:
            storage = storage_cls(db="test")
            storage.clear()
            return storage
    elif storage_cls is FileStorage:
        return storage_cls(base_path=base_path, binary_rw=is_binary)
    else:
        return storage_cls()

@pytest.fixture(params=storage_backends)
def storage(request, tmpdir):
    # don't bother with binary storage unless testing with pickle/bson
    return get_storage(request.param, base_path=Path(tmpdir))

manager_configs = [
    (None,                       None,               InMemoryStorage),  # native_in_mem
    (None,                       StructuringHandler, InMemoryStorage),  # unstructured_in_mem
    (PickleSerializationHandler, None,               InMemoryStorage),  # pickle_in_mem
    (PickleSerializationHandler, None,               FileStorage),      # pickle_file
    (PickleSerializationHandler, None,               RedisStorage),     # pickle_redis
    (JsonSerializationHandler,   StructuringHandler, RedisStorage),     # json_redis
    (JsonSerializationHandler,   StructuringHandler, FileStorage),      # json_file
    (YamlSerializationHandler,   StructuringHandler, FileStorage),      # yaml_file
    (BsonSerializationHandler,   StructuringHandler, FileStorage),      # bson_file
    (BsonSerializationHandler,   StructuringHandler, MongoStorage)      # bson_mongo
]

@pytest.fixture(params=manager_configs)
def manager(request, tmpdir):
    serializer, structuring, storage_cls = request.param
    print( serializer.__name__ if serializer else None,
           structuring.__name__ if structuring else None,
           storage_cls.__name__ )

    if serializer in [PickleSerializationHandler, BsonSerializationHandler]:
        is_binary = True
    else:
        is_binary = False

    serializer = get_serializer(serializer)
    storage = get_storage(storage_cls, base_path=Path(tmpdir), is_binary=is_binary)

    from tangl.persistence import PersistenceManager
    pm = PersistenceManager(
        serializer=serializer,
        structuring=structuring,
        storage=storage,
    )
    return pm
    # todo: need teardown to clear test_obj if connecting to a persistent db
