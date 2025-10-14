from __future__ import annotations

"""Registry for media resource inventory tags with filesystem discovery."""

from collections.abc import Iterable, Iterator, MutableMapping
from pathlib import Path
from typing import Optional
from uuid import UUID

import logging

from pydantic import ConfigDict, Field

from tangl.core.dispatch import DispatchRegistry
from tangl.core.registry import Registry
from tangl.media.enums import MediaDataType
from tangl.media.media_resource_inventory_tag import MediaResourceInventoryTag
from tangl.type_hints import Hash, Tag

logger = logging.getLogger(__name__)


on_index_media = DispatchRegistry(label="index_media")


class MediaResourceRegistry(Registry[MediaResourceInventoryTag]):
    """Registry that indexes media inventory tags and discovers filesystem assets."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    indexing_handlers: DispatchRegistry = Field(default_factory=lambda: on_index_media)

    def __init__(
        self,
        *,
        indexing_handlers: DispatchRegistry | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if indexing_handlers is not None:
            self.indexing_handlers = indexing_handlers
        self._content_hash_index: dict[Hash, UUID] = {}
        self._path_index: dict[str, UUID] = {}
        self._tag_index: dict[Tag, set[UUID]] = {}
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        for rit in self.values():
            self._index_rit(rit)

    def _index_rit(self, rit: MediaResourceInventoryTag) -> None:
        if rit.content_hash is not None:
            self._content_hash_index[rit.content_hash] = rit.uid
        if rit.path is not None:
            self._path_index[str(rit.path)] = rit.uid
        for tag in rit.tags:
            self._tag_index.setdefault(tag, set()).add(rit.uid)

    def _get_existing(self, rit: MediaResourceInventoryTag) -> Optional[MediaResourceInventoryTag]:
        if rit.content_hash is not None:
            uid = self._content_hash_index.get(rit.content_hash)
            if uid is not None:
                existing = self.get(uid)
                if existing is not None:
                    return existing
        if rit.path is not None:
            uid = self._path_index.get(str(rit.path))
            if uid is not None:
                existing = self.get(uid)
                if existing is not None:
                    return existing
        return None

    def add(
        self,
        rit: MediaResourceInventoryTag,
        *,
        run_handlers: bool = True,
    ) -> MediaResourceInventoryTag:
        existing = self._get_existing(rit)
        if existing is not None:
            return existing

        if run_handlers:
            namespace: MutableMapping[str, object] = {"rit": rit, "registry": self}
            list(self.indexing_handlers.run_all(namespace))
            rit = namespace["rit"]

        super().add(rit)
        self._index_rit(rit)
        return rit

    def discover_from_directory(
        self,
        directory: Path | str,
        *,
        recursive: bool = True,
        **default_kwargs,
    ) -> list[MediaResourceInventoryTag]:
        base = Path(directory).expanduser().resolve()
        if not base.exists():
            raise FileNotFoundError(base)
        if not base.is_dir():
            raise NotADirectoryError(base)

        pattern = "**/*" if recursive else "*"
        discovered: list[MediaResourceInventoryTag] = []

        for path in base.glob(pattern):
            if not path.is_file():
                continue

            try:
                media_type = MediaDataType.from_path(path)
            except ValueError:
                media_type = MediaDataType.UNKNOWN

            if media_type is MediaDataType.UNKNOWN:
                continue

            resolved = path.resolve()
            if str(resolved) in self._path_index:
                logger.debug("Skipping already-indexed path %s", resolved)
                continue

            rit = MediaResourceInventoryTag.from_path(resolved, **default_kwargs)
            result = self.add(rit)
            if result is rit:
                discovered.append(result)
                logger.info("Discovered media asset at %s", resolved)

        return discovered

    def find_by_tags(
        self,
        tags: set[Tag] | Tag,
        **criteria,
    ) -> Iterator[MediaResourceInventoryTag]:
        if isinstance(tags, set):
            tags_set = set(tags)
        elif isinstance(tags, Iterable) and not isinstance(tags, (str, bytes)):
            tags_set = set(tags)
        else:
            tags_set = {tags}

        if not tags_set:
            return iter(())

        candidate_uids: set[UUID] | None = None
        for tag in tags_set:
            tag_uids = self._tag_index.get(tag, set())
            if candidate_uids is None:
                candidate_uids = set(tag_uids)
            else:
                candidate_uids &= tag_uids
            if not candidate_uids:
                return iter(())

        assert candidate_uids is not None

        def _iterator() -> Iterator[MediaResourceInventoryTag]:
            for uid in candidate_uids:
                rit = self.get(uid)
                if rit is None:
                    continue
                if not tags_set.issubset(rit.tags):
                    continue
                if rit.matches(**criteria):
                    yield rit

        return _iterator()

    def find_one(self, **criteria) -> Optional[MediaResourceInventoryTag]:
        if "tags" in criteria:
            tags = criteria.pop("tags")
            results = self.find_by_tags(tags, **criteria)
        else:
            results = super().find_all(**criteria)
        return next(iter(results), None)
