"""Service38 world controller backed by story38 world registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tangl.core import BaseFragment
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.api_endpoint import HasApiEndpoints
from tangl.service.response import RuntimeInfo
from tangl.service.response.info_response import WorldInfo
from tangl.service.response.info_response.world_info import WorldList
from tangl.service.world_registry import WorldRegistry
from tangl.service38.api_endpoint import (
    AccessLevel,
    ApiEndpoint38,
    MethodType,
    ResponseType,
)
from tangl.story38.fabula import World38
from tangl.type_hints import Identifier, UnstructuredData
from tangl.utils.ordered_tuple_dict import OrderedTupleDict


_MANUAL_WORLDS38: dict[str, World38] = {}


def resolve_world38(world_id: str) -> World38:
    """Resolve a world from in-memory overrides or filesystem registry."""
    if world_id in _MANUAL_WORLDS38:
        return _MANUAL_WORLDS38[world_id]
    registry = WorldRegistry()
    world = registry.get_world(world_id, runtime_version="38")
    if not isinstance(world, World38):
        raise TypeError(f"Expected story38 world for '{world_id}', got {type(world)!r}")
    return world


def _dereference_world_id(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
    world_id = kwargs.pop("world_id", None)
    if world_id is not None:
        kwargs["world"] = resolve_world38(str(world_id))
    return args, kwargs


class WorldController(HasApiEndpoints):
    """World metadata and lifecycle endpoints for story38 worlds."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        group="system",
        binds=(),
    )
    def list_worlds(self) -> list[BaseFragment]:
        registry = WorldRegistry()
        worlds = registry.list_worlds()

        if _MANUAL_WORLDS38:
            known = {item.get("label") for item in worlds}
            for label, world in _MANUAL_WORLDS38.items():
                if label in known:
                    continue
                worlds.append(
                    {
                        "label": label,
                        "metadata": world.metadata or {},
                        "is_anthology": False,
                    }
                )

        fragments: list[BaseFragment] = []
        for world in worlds:
            content = OrderedTupleDict(
                {
                    "key": (world["label"],),
                    "value": (str((world.get("metadata") or {}).get("title", world["label"])),),
                }
            )
            fragments.append(WorldList(content=content))
        return fragments

    @ApiEndpoint38.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.INFO,
        binds=(),
    )
    def get_world_info(self, world: World38, **kwargs: Any) -> WorldInfo:
        metadata = dict(world.metadata or {})
        metadata.setdefault("title", world.label)
        metadata.setdefault("author", "Unknown")
        return WorldInfo(label=world.label, **metadata, **kwargs)

    @ApiEndpoint38.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.MEDIA,
        binds=(),
    )
    def get_world_media(
        self,
        world: World38,
        media: MediaRIT | Identifier,
        **kwargs: Any,
    ) -> MediaDataType:
        if isinstance(media, MediaRIT):
            return media.get_content(**kwargs)

        media_registry = getattr(world, "media_registry", None)
        if media_registry is None or not hasattr(media_registry, "find_one"):
            raise ValueError(f"World '{world.label}' does not expose media resources")

        media_obj = media_registry.find_one(alias=media)
        if media_obj is None:
            raise ValueError(f"Media '{media}' not found for world '{world.label}'")
        return media_obj.get_content(**kwargs)

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
        if script_path is not None:
            path = Path(script_path)
            if not path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
            script_data = yaml.safe_load(path.read_text(encoding="utf-8"))

        if not isinstance(script_data, dict):
            raise ValueError("script_data is required to load a world")

        world = World38.from_script_data(script_data=script_data)
        _MANUAL_WORLDS38[world.label] = world
        return RuntimeInfo.ok(message="World loaded", world_label=world.label)

    @ApiEndpoint38.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    def unload_world(self, world: World38) -> RuntimeInfo:
        _MANUAL_WORLDS38.pop(world.label, None)
        return RuntimeInfo.ok(message="World unloaded", world_label=world.label)


__all__ = ["WorldController", "resolve_world38"]
