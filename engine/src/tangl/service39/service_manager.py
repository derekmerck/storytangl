from __future__ import annotations
from typing import Mapping, Any, Optional, Protocol
from enum import IntEnum
from uuid import UUID
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass

from pydantic import Field, BaseModel

from tangl.type_hints import Identifier, HasUid
from tangl.utils.app_uptime import app_uptime
from tangl.utils.hash_secret import key_for_secret
from tangl.core39 import Entity
from .job_type import JobType
from .response_types import WorldInfoResponse, StoryInfoResponse, SystemInfoResponse, UserInfoResponse, RuntimeResponse, MediaResponse, ContentResponse

# todo: Instead of using uid or label everywhere, should use "get_label" which will result in the shortcode for most objects

class Acl(IntEnum):
    PUBLIC = ANYONE =  0
    USER            = 10
    ADMIN  = DEV    = 20

WorldId = str
UserId = str | UUID
StoryId = UUID

class World(HasUid):
    label: WorldId
    def create_story(self, **_) -> HasUid: ...
    def get_info(self, **_) -> dict: ...
    @classmethod
    def drop_instance(cls, world_id: WorldId) -> Any: ...
    @classmethod
    def get_instance(cls, world_id: WorldId) -> World: ...
    @classmethod
    def compile_bundle(cls, bundle: Any) -> World: ...

@dataclass
class User(HasUid):
    secret: str
    acl: int = Acl.USER
    current_story_id: Optional[StoryId] = None
    def get_info(self, **_) -> dict: ...

@dataclass
class StoryLedger(HasUid):
    story: HasUid
    user: User | UserId
    def set_dirty(self): ...
    def get_journal(self, which = -1, **_) -> dict: ...
    def get_info(self, **_) -> dict: ...
    def do_choice(self, *, item_id: UUID, **_): ...

class RuntimeOp(Protocol):
    @classmethod
    def eval(cls, expr: str, ns: dict ) -> Any: ...
    @classmethod
    def exec(cls, expr: str, ns: dict ): ...

class ServiceManager:
    """
    ServiceManager:
    - owns persistence
    - pre-processes requests and converts id's to user/stories
    - invokes domain controllers
    - post-processes and formats responses
    """

    # Use an IndirectMapping wrapper for api-keys
    storage: Mapping[UserId|StoryId, User|StoryLedger] = Field(default_factory=dict)

    @contextmanager
    def _open_user(self, user_id: UserId, wb: bool = False, acl: int = Acl.USER):
        user = self.storage[user_id]
        if acl < user.acl:
            raise PermissionError("User not allowed")
        yield user
        if wb:
            self.storage[user_id] = user

    @contextmanager
    def _open_story_ledger(self, user_id: UserId, wb: bool = False, acl: int = Acl.USER):
        with self._open_user(user_id, wb, acl) as user:
            story_id = user.current_story_id       # type: StoryId
            story_ledger = self.storage[story_id]  # type: StoryLedger
            # link user authority
            story_ledger.user = user
            yield story_ledger  # type: StoryLedger
            if wb:
                # unlink user authority
                story_ledger.user = user.uid
                self.storage[story_id] = story_ledger

    @contextmanager
    def _open_world(self, world_id: Identifier):
        yield World.get_instance(world_id)

class ServiceEndpoint(Entity):
    label: str
    acl: Acl
    job_type: JobType
    req_story: bool = False
    req_world: bool = False

def service_endpoint(job_type: JobType, acl: Acl = Acl.PUBLIC, func = None, **kwargs):
    return func

class WorldController(ServiceManager):
    """
    user: new_story, get_journal, get_info, do, drop_story
    dev: check, apply, goto, inspect
    """
    @service_endpoint(acl=Acl.DEV, job_type=JobType.CREATE)
    # Acl.DEV -> user is required for privilege, but not passed in
    def load_world(self, *, bundle_path: Path) -> RuntimeResponse:
        bundle = World.bundle_from_path(bundle_path)
        world = World.compile_bundle(bundle)
        return RuntimeResponse.Ok(
            job="world/r.load_world",
            job_type=JobType.CREATE,
            result={
                "path": bundle_path,
                "world": world.label,
            }
        )

    @service_endpoint(acl=Acl.DEV)
    # Acl.DEV -> user is required for privilege, but not passed in
    # doesn't need to dereference world either
    def unload_world(self, *, world_id: WorldId) -> RuntimeResponse:
        World.drop_instance(world_id)
        return RuntimeResponse.Ok(
            job="world/r.unload_world",
            job_type=JobType.DELETE,
            result={
                "world": world_id,
            }
        )

    @service_endpoint(acl=Acl.PUBLIC, job_type=JobType.READ, req_world=True)
    def get_world_info(self, *, world: World) -> WorldInfoResponse:
        data = world.get_info()
        return WorldInfoResponse(**data)

    @service_endpoint(acl=Acl.PUBLIC, job_type=JobType.READ, req_world=True)
    def get_world_media(self, *, world: World, item_id: UUID) -> MediaResponse:
        raise NotImplementedError()

class UserController(ServiceManager):
    """
    public: new_user
    user: get_info, update_secret, drop_user
    """
    @service_endpoint(acl=Acl.PUBLIC, job_type=JobType.CREATE)
    def create_user(self, *, secret: str = None) -> RuntimeResponse:
        user = User(secret=secret)
        self.storage[user.uid] = user
        return RuntimeResponse.Ok(
            job_type=JobType.CREATE,
            job="user.create_user",
            result={
                "user": user.uid,
                "secret": user.secret,
                "api_key": key_for_secret(user.secret)
            }
        )

    @service_endpoint(acl=Acl.USER, job_type=JobType.READ)
    def get_user_info(self, user: User) -> UserInfoResponse:
        data = user.unstructure(exclude={"secret"})
        return UserInfoResponse(**data)

    @service_endpoint(acl=Acl.USER, mode=JobType.UPDATE)
    def update_secret(self, *, user: User, new_secret: str) -> RuntimeResponse:
        user.secret = new_secret
        return RuntimeResponse.Ok(
            job_type=JobType.UPDATE,
            job="user.update_secret",
            result = {
                "user": user.uid,
                "secret": user.secret,
                "api_key": key_for_secret(user.secret)
            }
        )

    @service_endpoint(acl=Acl.USER, job_type=JobType.DELETE)
    def drop_user(self, *, user: User) -> RuntimeResponse:
        del self.storage[user.uid]
        return RuntimeResponse.Ok(
            job="user.drop_user",
            job_type=JobType.DELETE,
            result={
                "user": user.uid,
            }
        )

class SystemController(BaseModel):

    @service_endpoint(acl=Acl.USER, job_type=JobType.READ)
    def get_system_info(self) -> SystemInfoResponse:
        from tangl.info import __version__, __title__
        data = {'title': __title__, 'version': __version__, 'uptime': app_uptime()}
        return SystemInfoResponse(**data)

    @service_endpoint(acl=Acl.PUBLIC, job_type=JobType.READ)
    def get_system_media(self, *, item_id: UUID) -> MediaResponse:
        raise NotImplementedError()

    @service_endpoint(acl=Acl.PUBLIC, job_type=JobType.READ)
    def get_api_key(self, secret: str) -> RuntimeResponse:
        return RuntimeResponse.Ok(
            job="system.get_api_key",
            job_type=JobType.READ,
            result={
                "secret": secret,
                "api_key": key_for_secret(secret)
            }
        )


class StoryController(ServiceManager):

    @service_endpoint(acl=Acl.PUBLIC, job_type=JobType.CREATE, req_user=True, req_world=True)
    def create_story(self, *, user: User, world: World) -> RuntimeResponse:
        story = world.create_story()
        ledger = StoryLedger(story=story, user=user.uid)
        user.current_story_id = ledger.uid
        self.storage[ledger.uid] = ledger
        return RuntimeResponse.Ok(
            job="create_story",
            job_type=JobType.CREATE,
            result={
                "user": user.uid,
                "world": world.label,
                "story": story.uid
            }
        )

    @service_endpoint(acl=Acl.USER, job_type=JobType.READ, req_story=True)
    def get_story_info(self, story: StoryLedger, **params) -> StoryInfoResponse:
        data = story.get_info(**params)
        return StoryInfoResponse(**data)

    @service_endpoint(acl=Acl.USER, job_type=JobType.READ, req_story=True)
    def get_journal(self, story: StoryLedger, which: Any = -1, **params) -> ContentResponse:
        content = story.get_journal(which=which, **params)
        return ContentResponse(
            content=content
        )

    @service_endpoint(acl=Acl.USER, job_type=JobType.READ, req_story=True)
    def get_story_media(self, *, story: StoryLedger, item_id: UUID) -> MediaResponse:
        raise NotImplementedError()

    @service_endpoint(acl=Acl.USER, job_type=JobType.UPDATE, req_story=True)
    def do_choice(self, story: StoryLedger, **params) -> StoryInfoResponse:
        data = story.get_info(**params)
        return StoryInfoResponse(**data)

    @service_endpoint(acl=Acl.USER, job_type=JobType.DELETE, req_story=True)
    def drop_story(self, *, story: StoryLedger) -> RuntimeResponse:
        if story.user.current_story_id == story.uid:
            story.user.current_story_id = None
        del self.storage[story.uid]
        return RuntimeResponse.Ok(
            job="drop_story",
            job_type=JobType.DELETE,
            result={
                "user": story.user.uid,
                "story": story.uid,
            }
        )

    # RESTRICTED ENDPOINTS

    @service_endpoint(acl=Acl.DEV, job_type=JobType.UPDATE, req_story=True)
    # story/r  endpoints are update b/c they mark logical dirty
    def inspect_node(self, *, story: StoryLedger, node_id: Identifier) -> RuntimeResponse:
        story.set_dirty()
        node = story.graph.find_one(has_identifier=node_id)
        if node is not None:
            data = node.unstructure()
            return RuntimeResponse.Ok(
                job="story/r.inspect_node",
                job_type=JobType.READ,
                result={
                    "user": story.user.uid,
                    "story": story.uid,
                    **data
                }
            )
        else:
            return RuntimeResponse.Nok(
                job="story/r.inspect_node",
                job_type=JobType.READ,
                error=f"No such node {node_id} in story {story.uid}"
            )

    @service_endpoint(acl=Acl.DEV, job_type=JobType.UPDATE, req_story=True)
    def check_expr(self, *, story: StoryLedger, expr: str) -> RuntimeResponse:
        story.set_dirty()
        result = RuntimeOp.eval(expr, story.cursor.get_ns())
        return RuntimeResponse.Ok(
            job="story/r.check_expr",
            job_type=JobType.READ,
            result={
                "user": story.user.uid,
                "story": story.uid,
                "cursor": story.cursor.get_label(),
                "expr": expr,
                "result": result
            }
        )

    @service_endpoint(acl=Acl.DEV, job_type=JobType.UPDATE, req_story=True)
    def apply_expr(self, *, story: StoryLedger, expr: str) -> RuntimeResponse:
        story.set_dirty()
        result = RuntimeOp.exec(expr, story.cursor.get_ns())
        if result is None:
            return RuntimeResponse.Ok(
                job="story/r.apply_expr",
                job_type=JobType.UPDATE,
                result={
                    "user": story.user.uid,
                    "story": story.uid,
                    "cursor": story.cursor.get_label(),
                    "expr": expr,
                }
            )
        else:
            return RuntimeResponse.Nok(
                job="story/r.apply_expr",
                job_type=JobType.UPDATE,
                error=f"Apply {expr} failed with {result}"
            )

    @service_endpoint(acl=Acl.DEV, job_type=JobType.UPDATE, req_story=True)
    def goto_node(self, *, story: StoryLedger, node_id: Identifier) -> RuntimeResponse:
        story.set_dirty()
        story.teleport_cursor(node_id)
        return RuntimeResponse.Ok(
            job="story/r.goto_node",
            job_type=JobType.DELETE,
            result={
                "user": story.user.uid,
                "story": story.uid,
                "cursor": story.cursor.get_label()
            }
        )
