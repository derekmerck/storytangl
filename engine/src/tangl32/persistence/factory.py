from __future__ import annotations
from pathlib import Path
from typing import Type, Literal, TypeVar

from tangl.config import settings
from tangl.type_hints import Pathlike
from .storage import InMemoryStorage, FileStorage, RedisStorage, MongoStorage
from .serializers import PickleSerializationHandler, JsonSerializationHandler, YamlSerializationHandler, BsonSerializationHandler
from .structuring import StructuringHandler

from .manager import PersistenceManager

PersistenceManagerName = Literal[
    "native_in_mem",
    "unstructured_in_mem",
    "pickle_in_mem",
    "pickle_file",
    "pickle_redis",
    "json_file",
    "yaml_file",
    "bson_file",
    "bson_mongo"
]

DEFAULT_PERSISTENCE_MGR = settings.get('service.persistence', 'native_in_mem')  # type: PersistanceManagerName
DEFAULT_USER_DATA_PATH = settings.get('service.paths.user_data', Path("~/tmp").expanduser())
DEFAULT_REDIS_URL = settings.get('service.apis.redis.url')
DEFAULT_MONGO_URL = settings.get('service.apis.mongo.url')

ManagerType = TypeVar("ManagerType", bound=PersistenceManager)


class PersistenceManagerFactory:
    """
    Factory class providing different configurations of PersistenceManager.

    Each method returns a PersistenceManager configured with specific
    storage and serialization methods suitable for various use cases.

    Supported methods include:
    - Raw in-memory storage: `raw_in_mem`
    - Binary structured data storage: `pickle_in_mem`, `pickle_file`, or `pickle_redis`
    - Text unstructured data storage: `json_file` or `yaml_file`
    - Binary unstructured data storage: `bson_file` or `bson_mongo`
    """

    @classmethod
    def create_persistence_manager(cls,
                                   manager_cls: Type[ManagerType] = PersistenceManager,
                                   manager_name: PersistenceManagerName = DEFAULT_PERSISTENCE_MGR,
                                   structuring: Type[StructuringHandler] = StructuringHandler,
                                   user_data_path: Pathlike = DEFAULT_USER_DATA_PATH,
                                   redis_url: str = DEFAULT_REDIS_URL,
                                   mongo_url: str = DEFAULT_MONGO_URL) -> ManagerType:
        """
        Use the project settings defaults to instantiate a persistence manager, optionally using the
        given StructuringHandler, if one is both provided and required.
        """

        user_data_path = Path(user_data_path)

        if user_data_path and user_data_path.exists():
            _kwargs = {"user_data_path": user_data_path}
        else:
            _kwargs = {}

        match manager_name:

            # Structured data
            case "native_in_mem":
                return cls.native_in_mem(manager_cls=manager_cls)
            case "unstructured_in_mem":
                return cls.unstructured_in_mem(manager_cls=manager_cls)
            case "pickle_in_mem":
                # generally only useful for testing pickle serializer
                return cls.pickle_in_mem(manager_cls=manager_cls)
            case "pickle_file":
                return cls.pickle_file(manager_cls=manager_cls, base_path=user_data_path)
            case "pickle_redis":
                return cls.pickle_redis(manager_cls=manager_cls, url=redis_url)

            # Unstructured data
            case "json_redis":
                return cls.json_redis(manager_cls=manager_cls, structuring=structuring, url=redis_url)
            case "json_file":
                return cls.json_file(manager_cls=manager_cls, structuring=structuring, base_path=user_data_path)
            case "yaml_file":
                return cls.yaml_file(manager_cls=manager_cls, structuring=structuring, base_path=user_data_path)
            case "bson_file":
                return cls.bson_file(manager_cls=manager_cls, structuring=structuring, base_path=user_data_path)
            case "bson_mongo":
                return cls.bson_mongo(manager_cls=manager_cls, structuring=structuring, url=mongo_url)
            case _:
                raise ValueError(f"Unknown persistence mgr type: {manager_name}")

    # Structured in-mem, no structuring _or_ serialization handler required

    @staticmethod
    def native_in_mem(manager_cls: Type[ManagerType] = PersistenceManager) -> ManagerType:
        return manager_cls(
            storage=InMemoryStorage()
        )

    @staticmethod
    def unstructured_in_mem(manager_cls: Type[ManagerType] = PersistenceManager,
                            structuring: Type[StructuringHandler] = StructuringHandler) -> ManagerType:
        return manager_cls(
            storage=InMemoryStorage(),
            structuring=structuring
        )

    # ------------------------
    # Structured binary, no structuring handler required
    # ------------------------

    @staticmethod
    def pickle_in_mem(manager_cls: Type[ManagerType] = PersistenceManager) -> ManagerType:
        return manager_cls(
            storage=InMemoryStorage(),
            serializer=PickleSerializationHandler
        )

    @staticmethod
    def pickle_file(manager_cls: Type[ManagerType] = PersistenceManager,
                    base_path: Path = DEFAULT_USER_DATA_PATH) -> ManagerType:
        return manager_cls(
            storage=FileStorage(base_path=base_path, ext="pkl", binary_rw=True),
            serializer=PickleSerializationHandler
        )

    @staticmethod
    def pickle_redis(manager_cls: Type[ManagerType] = PersistenceManager,
                     url=DEFAULT_REDIS_URL) -> ManagerType:
        if not (settings and settings.service.apis.redis.enabled):
            raise ImportError
        return manager_cls(
            storage=RedisStorage(url=url),
            serializer=PickleSerializationHandler
        )

    # ------------------------
    # Unstructured text, requires both structuring and serialization handlers
    # ------------------------

    @staticmethod
    def json_redis(manager_cls: Type[ManagerType] = PersistenceManager,
                   url = DEFAULT_REDIS_URL,
                   structuring: Type[StructuringHandler] = StructuringHandler) -> ManagerType:
        if not settings.service.apis.redis.enabled:
            raise ImportError
        return manager_cls(
            storage=RedisStorage(url=url),
            serializer=JsonSerializationHandler,
            structuring=structuring
        )

    @staticmethod
    def json_file(manager_cls: Type[ManagerType] = PersistenceManager,
                  base_path: Path = DEFAULT_USER_DATA_PATH,
                  structuring: Type[StructuringHandler] = StructuringHandler) -> ManagerType:
        return manager_cls(
            storage=FileStorage(base_path=base_path, ext="json", binary_rw=False),
            serializer=JsonSerializationHandler,
            structuring=structuring
        )

    @staticmethod
    def yaml_file(manager_cls: Type[ManagerType] = PersistenceManager,
                  base_path: Path = DEFAULT_USER_DATA_PATH,
                  structuring: Type[StructuringHandler] = StructuringHandler) -> ManagerType:
        return manager_cls(
            storage=FileStorage(base_path=base_path, ext="yaml", binary_rw=False),
            serializer=YamlSerializationHandler,
            structuring=structuring
        )

    # ------------------------
    # Unstructured binary, requires structuring handler
    # ------------------------

    @staticmethod
    def bson_file(manager_cls: Type[ManagerType] = PersistenceManager,
                  base_path: Path = DEFAULT_USER_DATA_PATH,
                  structuring: Type[StructuringHandler] = StructuringHandler) -> ManagerType:
        if not (settings and settings.service.apis.mongo.enabled):
            raise ImportError
        return manager_cls(
            storage=FileStorage(base_path=base_path, ext="bson", binary_rw=True),
            serializer=BsonSerializationHandler,
            structuring=structuring
        )

    @staticmethod
    def bson_mongo(manager_cls: Type[ManagerType] = PersistenceManager,
                   url=DEFAULT_MONGO_URL,
                   structuring: Type[StructuringHandler] = StructuringHandler) -> ManagerType:
        if not (settings and settings.service.apis.mongo.enabled):
            raise ImportError
        return manager_cls(
            storage=MongoStorage(url=url),
            serializer=BsonSerializationHandler,
            structuring = structuring
        )
