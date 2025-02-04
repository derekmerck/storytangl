import logging
from uuid import UUID

from tangl.config import settings

try:
    from redis import Redis
    from redis.exceptions import ConnectionError
    HAS_REDIS = True
except ImportError:
    Redis = object
    ConnectionError = RuntimeError
    HAS_REDIS = False
    if settings:
        settings.service.apis.redis.enabled = False

from tangl.type_hints import FlatData

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class RedisStorage:

    def __init__(self, url = None, db = None):
        if not settings.service.apis.redis.enabled:
            raise RuntimeError("Redis backend not enabled")
        if not HAS_REDIS:
            raise ImportError

        url = url or settings.service.apis.redis.url
        token = settings.service.apis.redis.token
        parts = url.split("/")
        if parts[-1].isdigit():
            nominal_db = int(parts[-1])
            url = "/".join( parts[:-1] )
        else:
            # db not in url, use 0
            nominal_db = 0
        db = db or nominal_db
        logger.debug( f"url={url}, token={token}, db={db}" )
        self.redis = Redis.from_url(url, password=token, db=db)  # type: Redis

        try:
            # The 'ping' command is issued here
            self.ping()
            print("Redis connection is alive.")
        except (AssertionError, ConnectionError) as e:
            print(f"Unable to connect to Redis: {e}")
            settings.service.apis.redis.enabled = False
            raise ConnectionError("Unable to connect to redis")

        logger.debug( self.redis )

    def clear(self):
        self.redis.flushdb()

    def ping(self) -> bool:
        return self.redis.ping()

    def get_key(self, key: UUID):
        if isinstance(key, UUID):
            return key.bytes
        return key

    def __contains__(self, key: UUID) -> bool:
        key = self.get_key(key)
        return self.redis.exists(key) > 0

    def __getitem__(self, key: UUID) -> FlatData:
        key = self.get_key(key)
        value = self.redis.get(key)
        if value is None:
            raise KeyError
        return value

    def __setitem__(self, key: UUID, value: FlatData):
        key = self.get_key(key)
        return self.redis.set(key, value)

    def __delitem__(self, key):
        key = self.get_key(key)
        if not self.redis.exists(key):
            raise KeyError
        self.redis.delete(key)

    def __len__(self):
        return self.redis.dbsize()

    def __bool__(self) -> bool:
        return len(self) != 0
