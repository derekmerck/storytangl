from __future__ import annotations

"""Utilities for indexing and serving media resources within a world."""

from pathlib import Path
from typing import Optional
import logging

from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

logger = logging.getLogger(__name__)


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

    def __init__(self, resource_path: Path) -> None:
        self.resource_path = resource_path
        self.registry = MediaResourceRegistry(label="world_media")

    def index_directory(self, subdir: str = "images") -> list[MediaRIT]:
        """Index all files in ``subdir`` relative to :attr:`resource_path`."""
        path = self.resource_path / subdir
        if not path.exists():
            logger.debug("Resource directory %s does not exist", path)
            return []

        files = [item for item in path.iterdir() if item.is_file()]
        records = self.registry.index(files)
        for record, source in zip(records, files):
            if not record.label:
                record.label = source.name
        return records

    def get_rit(self, alias: str) -> Optional[MediaRIT]:
        """Return the resource tagged by ``alias`` or ``None`` if missing."""
        rit = self.registry.find_one(label=alias)
        if rit is not None:
            return rit
        rit = self.registry.find_one(has_identifier=alias)
        if rit is not None:
            return rit
        return next(
            (
                record
                for record in self.registry.values()
                if record.path and record.path.name == alias
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
