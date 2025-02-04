from uuid import UUID

from tangl.config import settings
from tangl.type_hints import FlatData

try:
    import pymongo
    import bson
    HAS_MONGO = True
except ImportError:
    pymongo = object
    bson = object
    HAS_MONGO = False
    if settings:
        settings.service.apis.mongo.enabled = False

class MongoStorage:

    def __init__(self, url: str = None, db: str = None, collection: str = None):
        if not settings.service.apis.mongo.enabled:
            raise RuntimeError("Mongo backend storage not enabled")
        if not HAS_MONGO:
            raise ImportError

        url = url or settings.service.apis.mongo.url
        self.client = pymongo.MongoClient(url, uuidRepresentation='standard')

        try:
            # The 'ping' command is issued here
            self.ping()
            print("MongoDB connection is alive.")
        except ConnectionError as e:
            print(f"Unable to connect to MongoDB: {e}")
            settings.service.apis.redis.enabled = False
            raise ConnectionError("Unable to connect to redis")

        self.db = self.client.get_default_database()
        self.collection = db or "storage"
        self.mongo = self.db.get_collection(self.collection)

    def clear(self):
        self.db.drop_collection(self.collection)

    def ping(self) -> bool:
        return self.client.admin.command('ping')

    def __contains__(self, key: UUID) -> bool:
        return bool( self.mongo.find_one({'_id': key}) )

    def __getitem__(self, key: UUID) -> FlatData:
        val = self.mongo.find_one({'_id': key})
        return val

    def __setitem__(self, key: UUID, value: FlatData):
        if isinstance(value, bytes):
            # pre-encoded data
            value = bson.raw_bson.RawBSONDocument(value)
        # Insert doesn't work, it will throw a duplicate key error on overwrite
        # res = self.mongo.insert_one(value).inserted_id
        res = self.mongo.replace_one({'_id': key}, value, upsert=True)
        assert res.matched_count or res.upserted_id == key

    def __delitem__(self, key):
        if not self.mongo.find_one({'_id': key}):
            raise KeyError
        self.mongo.delete_one({'_id': key})

    def __len__(self) -> int:
        return self.mongo.estimated_document_count()

    def __bool__(self) -> bool:
        return len(self) != 0
