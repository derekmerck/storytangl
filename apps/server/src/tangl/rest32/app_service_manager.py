import asyncio
from collections import defaultdict
from uuid import UUID

from tangl.service import ServiceManager

service_manager = ServiceManager()

def get_service_manager() -> ServiceManager:
    return service_manager

# Could use redis-lock for this if scaling to use multiple servers
user_locks = defaultdict(lambda: asyncio.Lock())

def get_user_locks() -> dict[UUID, asyncio.Lock]:
    return user_locks
