"""Service38-native controller wrappers over legacy controller logic.

This module is an explicit transition layer: service38 owns endpoint metadata
(``ApiEndpoint38`` + explicit ``binds``), while implementation bodies still
delegate to legacy controller methods.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from tangl.core import BaseFragment
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.controllers.runtime_controller import RuntimeController as LegacyRuntimeController
from tangl.service.controllers.system_controller import SystemController as LegacySystemController
from tangl.service.controllers.user_controller import ApiKeyInfo
from tangl.service.controllers.user_controller import UserController as LegacyUserController
from tangl.service.controllers.world_controller import WorldController as LegacyWorldController
from tangl.service.controllers.world_controller import _dereference_world_id
from tangl.service.response import RuntimeInfo, StoryInfo
from tangl.service.response.info_response import SystemInfo, UserInfo, WorldInfo
from tangl.service.user.user import User
from tangl.story.fabula.world import World
from tangl.type_hints import Hash, Identifier, UnstructuredData
from tangl.vm.frame import Frame
from tangl.vm.ledger import Ledger
from tangl.vm38.runtime.ledger import Ledger as Ledger38

from .api_endpoint import AccessLevel, ApiEndpoint38, MethodType, ResourceBinding, ResponseType


class RuntimeController(LegacyRuntimeController):
    """Service38 runtime controller surface with explicit binding metadata."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.CONTENT,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_journal_entries(
        self,
        ledger: Ledger,
        limit: int = 0,
        *,
        current_only: bool = True,
        marker: str = "latest",
        marker_type: str = "entry",
        start_marker: str | None = None,
        end_marker: str | None = None,
    ) -> list[BaseFragment]:
        return super().get_journal_entries(
            ledger,
            limit=limit,
            current_only=current_only,
            marker=marker,
            marker_type=marker_type,
            start_marker=start_marker,
            end_marker=end_marker,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER, ResourceBinding.FRAME),
    )
    def resolve_choice(
        self,
        ledger: Ledger,
        frame: Frame,
        choice_id: UUID,
        choice_payload: Any = None,
    ) -> RuntimeInfo:
        return super().resolve_choice(
            ledger=ledger,
            frame=frame,
            choice_id=choice_id,
            choice_payload=choice_payload,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_info(self, ledger: Ledger) -> StoryInfo:
        return super().get_story_info(ledger)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def jump_to_node(self, ledger: Ledger, node_id: UUID) -> RuntimeInfo:
        return super().jump_to_node(ledger, node_id)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        binds=(ResourceBinding.USER,),
    )
    def create_story(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
        return super().create_story(user, world_id, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        binds=(ResourceBinding.USER,),
    )
    def create_story38(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
        return super().create_story38(user, world_id, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def resolve_choice38(
        self,
        ledger: Ledger38,
        choice_id: UUID,
        choice_payload: Any = None,
    ) -> RuntimeInfo:
        return super().resolve_choice38(
            ledger=ledger,
            choice_id=choice_id,
            choice_payload=choice_payload,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_update38(
        self,
        ledger: Ledger38,
        *,
        since_step: int | None = None,
        limit: int = 0,
    ) -> RuntimeInfo:
        return super().get_story_update38(
            ledger=ledger,
            since_step=since_step,
            limit=limit,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_info38(self, ledger: Ledger38) -> RuntimeInfo:
        return super().get_story_info38(ledger)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER, ResourceBinding.LEDGER),
    )
    def drop_story38(
        self,
        user: User,
        ledger: Ledger38 | None = None,
        *,
        archive: bool = False,
    ) -> RuntimeInfo:
        return super().drop_story38(
            user=user,
            ledger=ledger,
            archive=archive,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER, ResourceBinding.LEDGER),
    )
    def drop_story(
        self,
        user: User,
        ledger: Ledger | None = None,
        *,
        archive: bool = False,
    ) -> RuntimeInfo:
        return super().drop_story(
            user=user,
            ledger=ledger,
            archive=archive,
        )


class UserController(LegacyUserController):
    """Service38 user controller surface with explicit binding metadata."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        binds=(),
    )
    def create_user(self, **kwargs: Hash) -> RuntimeInfo:
        return super().create_user(**kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        binds=(ResourceBinding.USER,),
    )
    def update_user(self, user: User, **kwargs: Hash) -> RuntimeInfo:
        return super().update_user(user=user, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        binds=(ResourceBinding.USER,),
    )
    def get_user_info(self, user: User, **kwargs: Hash) -> UserInfo:
        return super().get_user_info(user=user, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        binds=(ResourceBinding.USER,),
    )
    def drop_user(self, user: User, **kwargs: Hash) -> RuntimeInfo:
        return super().drop_user(user=user, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        group="system",
        response_type=ResponseType.INFO,
        binds=(),
    )
    def get_key_for_secret(self, secret: str, **kwargs: Hash) -> ApiKeyInfo:
        return super().get_key_for_secret(secret=secret, **kwargs)


class WorldController(LegacyWorldController):
    """Service38 world controller surface with explicit binding metadata."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        group="system",
        binds=(),
    )
    def list_worlds(self) -> list[BaseFragment]:
        return super().list_worlds()

    @ApiEndpoint38.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
        binds=(),
    )
    def get_world_info(self, world: World, **kwargs: Any) -> WorldInfo:
        return super().get_world_info(world=world, **kwargs)

    @ApiEndpoint38.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.MEDIA,
        binds=(),
    )
    def get_world_media(
        self,
        world: World,
        media: MediaRIT | Identifier,
        **kwargs: Any,
    ) -> MediaDataType:
        return super().get_world_media(world=world, media=media, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.CREATE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    def load_world(
        self,
        *,
        script_path: str | Path | None = None,
        script_data: UnstructuredData = None,
    ) -> RuntimeInfo:
        return super().load_world(script_path=script_path, script_data=script_data)

    @ApiEndpoint38.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    def unload_world(self, world: World) -> RuntimeInfo:
        return super().unload_world(world)


class SystemController(LegacySystemController):
    """Service38 system controller surface with explicit binding metadata."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
        binds=(),
    )
    @staticmethod
    def get_system_info(*args: Any, **kwargs: Any) -> SystemInfo:
        return LegacySystemController.get_system_info(*args, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    @staticmethod
    def reset_system(*args: Any, hard: bool = False, **kwargs: Any) -> RuntimeInfo:
        return LegacySystemController.reset_system(*args, hard=hard, **kwargs)


DEFAULT_CONTROLLERS = (
    RuntimeController,
    UserController,
    SystemController,
    WorldController,
)


__all__ = [
    "DEFAULT_CONTROLLERS",
    "RuntimeController",
    "SystemController",
    "UserController",
    "WorldController",
]
