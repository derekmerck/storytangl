"""Utilities for indexing and serving media resources within one inventory scope."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, Optional
import logging

from tangl.core import Behavior, Selector
from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

IndexHandler = Behavior | Callable[..., Any]

class ResourceManager:
    """ResourceManager(resource_path: Path)

    Indexes media files and exposes lookup helpers for runtime usage.

    Why
    ---
    Story worlds bundle reference art, audio, and other media that scripts can
    reference by alias. The :class:`ResourceManager` inventories those assets so
    stories can resolve media identifiers to URLs when rendering output.

    Key Features
    ------------
    * **Directory indexing** – :meth:`index_directory` scans a folder and
      registers :class:`MediaRIT` entries.
    * **Index handlers** – world/local callables can retag or relabel records
      as they are indexed without subclassing the registry.
    * **Lookup helpers** – :meth:`get_rit` fetches entries by alias, hash, or
      filename.
    * **URL generation** – :meth:`get_url` derives a frontend path from the
      content hash and media type.

    API
    ---
    - :meth:`index_directory`
    - :meth:`get_rit`
    - :meth:`get_url`
    """

    def __init__(
        self,
        resource_path: Path,
        *,
        scope: str = "world",
        label: str | None = None,
        default_tags: Iterable[str] = (),
        index_handlers: Iterable[IndexHandler] = (),
    ) -> None:
        self.resource_path = resource_path
        self.scope = scope
        self.label = label or f"{scope}_media"
        self.default_tags = {f"scope:{scope}", *default_tags}
        self.index_handlers = list(index_handlers)
        self.registry = MediaResourceRegistry(label=self.label)

    def register_index_handler(self, handler: IndexHandler) -> None:
        """Register one reusable indexing handler for this manager."""
        self.index_handlers.append(handler)

    def index_directory(
        self,
        subdir: str = "images",
        *,
        tags: Iterable[str] = (),
        index_handlers: Iterable[IndexHandler] = (),
    ) -> list[MediaRIT]:
        """Index all files in ``subdir`` relative to :attr:`resource_path`."""
        path = self.resource_path / subdir
        if not path.exists():
            logger.debug("Resource directory %s does not exist", path)
            return []

        files = sorted(item for item in path.rglob("*") if item.is_file())
        handlers = [*self.index_handlers, *list(index_handlers)]
        records = self.registry.index(files, extra_handlers=handlers or None)
        for record, source in zip(records, files):
            if not record.label:
                record.label = source.name
            record.tags = set(record.tags or set()) | self.default_tags | set(tags)
        return records

    def register_file(
        self,
        path: Path,
        *,
        tags: Iterable[str] = (),
        index_handlers: Iterable[IndexHandler] = (),
    ) -> MediaRIT:
        """Index one file and apply the same default label/tag policy."""
        resolved_path = path if path.is_absolute() else (self.resource_path / path).resolve()
        if not resolved_path.is_file():
            raise FileNotFoundError(f"Cannot register missing media file: {resolved_path}")
        handlers = [*self.index_handlers, *list(index_handlers)]
        record = self.registry.index([resolved_path], extra_handlers=handlers or None)[0]
        if not record.label:
            record.label = resolved_path.name
        record.tags = set(record.tags or set()) | self.default_tags | set(tags)
        return record

    def get_rit(self, alias: str) -> Optional[MediaRIT]:
        """Return the resource tagged by ``alias`` or ``None`` if missing."""
        rit = self.registry.find_one(Selector(label=alias))
        if rit is not None:
            return rit
        rit = self.registry.find_one(Selector.from_identifier(alias))
        if rit is not None:
            return rit

        def _matches_alias(record: MediaRIT) -> bool:
            if not record.path:
                return False
            if record.path.name == alias:
                return True
            try:
                return str(record.path.relative_to(self.resource_path)) == alias
            except ValueError:
                return False

        return next(
            (
                record
                for record in self.registry.values()
                if _matches_alias(record)
            ),
            None,
        )

    def get_url(self, rit: MediaRIT) -> str:
        """Generate a deterministic URL for ``rit`` suitable for serving."""
        hash_prefix = rit.content_hash.hex()[:16]
        if rit.data_type:
            extension = rit.data_type.ext
        elif rit.path:
            extension = rit.path.suffix.removeprefix(".")
        else:
            extension = "bin"
        return f"/assets/{hash_prefix}.{extension}"
