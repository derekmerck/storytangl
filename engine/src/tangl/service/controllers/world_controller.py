"""World metadata and lifecycle endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.story.fabula import World
from tangl.type_hints import Identifier, UnstructuredData
from tangl.utils.ordered_tuple_dict import OrderedTupleDict
from tangl.utils.sanitize_str import sanitize_str

from ..api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResponseType,
)
from ..response import RuntimeInfo, WorldInfo, WorldList
from ..world_registry import WorldRegistry


_MANUAL_WORLDS: dict[str, World] = {}


def _legacy_world_label(script_data: dict[str, Any]) -> str | None:
    metadata = script_data.get("metadata")
    if isinstance(metadata, dict):
        title = metadata.get("title")
        if isinstance(title, str) and title.strip():
            return sanitize_str(title).lower()

    raw_label = script_data.get("label")
    if isinstance(raw_label, str) and raw_label.strip():
        return sanitize_str(raw_label).lower()
    return None


def resolve_world(world_id: str) -> World:
    """Resolve a world from in-memory overrides or filesystem registry."""
    if world_id in _MANUAL_WORLDS:
        return _MANUAL_WORLDS[world_id]

    registry = WorldRegistry()
    world = registry.get_world(world_id)

    if not isinstance(world, World):
        raise TypeError(f"Expected Story world for '{world_id}', got {type(world)!r}")
    return world


def _dereference_world_id(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
    world_id = kwargs.pop("world_id", None)
    if world_id is not None:
        kwargs["world"] = resolve_world(str(world_id))
    return args, kwargs


class WorldController(HasApiEndpoints):
    """World metadata and lifecycle endpoints."""

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        group="system",
        binds=(),
    )
    def list_worlds(self) -> list[WorldList]:
        registry = WorldRegistry()
        worlds = registry.list_worlds()

        if _MANUAL_WORLDS:
            known = {item.get("label") for item in worlds}
            for label, world in _MANUAL_WORLDS.items():
                if label in known:
                    continue
                worlds.append(
                    {
                        "label": label,
                        "metadata": world.metadata or {},
                        "is_anthology": False,
                    }
                )

        fragments: list[WorldList] = []
        for world in worlds:
            content = OrderedTupleDict(
                {
                    "key": (world["label"],),
                    "value": (str((world.get("metadata") or {}).get("title", world["label"])),),
                }
            )
            fragments.append(WorldList(content=content))
        return fragments

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.INFO,
        binds=(),
    )
    def get_world_info(self, world: World, **kwargs: Any) -> WorldInfo:
        metadata = dict(world.metadata or {})
        metadata.pop("label", None)
        info_kwargs = dict(kwargs)
        info_kwargs.pop("label", None)
        metadata.setdefault("title", world.label)
        metadata.setdefault("author", "Unknown")
        return WorldInfo(label=world.label, **metadata, **info_kwargs)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.MEDIA,
        binds=(),
    )
    def get_world_media(
        self,
        world: World,
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

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
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

        world = World.from_script_data(script_data=script_data)
        legacy_label = _legacy_world_label(script_data)
        if legacy_label:
            world.label = legacy_label
        _MANUAL_WORLDS[world.label] = world
        return RuntimeInfo.ok(message="World loaded", world_label=world.label)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.USER,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    def unload_world(self, world: World) -> RuntimeInfo:
        removed = _MANUAL_WORLDS.pop(world.label, None)
        if removed is None:
            return RuntimeInfo.error(
                code="WORLD_NOT_MANUAL",
                message="No manual world to unload",
                world_label=world.label,
            )
        return RuntimeInfo.ok(message="World unloaded", world_label=world.label)


__all__ = ["WorldController", "resolve_world"]
