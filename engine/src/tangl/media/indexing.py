from __future__ import annotations

"""Default indexing handlers for media discovery."""

from collections.abc import MutableMapping
from typing import Any

from tangl.core.dispatch import HandlerPriority
from tangl.media.media_resource_registry import on_index_media


@on_index_media.register(priority=HandlerPriority.NORMAL)
def add_parent_directory_tag(ns: MutableMapping[str, Any]) -> str | None:
    """Add the parent directory name as a tag during indexing."""

    rit = ns.get("rit")
    if rit is None or getattr(rit, "path", None) is None:
        return None

    parent_name = rit.path.parent.name
    if parent_name:
        rit.tags.add(parent_name)
    return parent_name
