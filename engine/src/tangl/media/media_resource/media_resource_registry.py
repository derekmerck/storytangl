from __future__ import annotations
from typing import Iterable, Type, Any, Callable, ByteString
from uuid import UUID
import logging
from datetime import datetime
from pathlib import Path

from pydantic import Field

from tangl.core import (
    Behavior,
    BehaviorRegistry,
    CallReceipt,
    DispatchLayer,
    Registry,
    Selector,
    resolve_ctx,
)
from .media_resource_inv_tag import MediaRITStatus, MediaResourceInventoryTag as MediaRIT

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class MediaResourceRegistry(Registry[MediaRIT]):
    """
    A specialized registry for media assets that supports content-aware
    deduplication and flexible indexing strategies.
    """
    local_behaviors: BehaviorRegistry = Field(
        default_factory=lambda: BehaviorRegistry(
            label="media.local.dispatch",
            default_dispatch_layer=DispatchLayer.LOCAL,
        ),
        exclude=True,
    )
    mrt_cls: Type[MediaRIT] = MediaRIT

    # This is derived from ``members`` rather than persisted state. Slots keep it
    # out of Pydantic's value equality as well as constructor-form persistence.
    __slots__ = ("_content_hash_members", "_dynamic_member_count")

    def model_post_init(self, context: Any) -> None:
        """Build the static content index for directly initialized members."""
        super().model_post_init(context)
        self._content_hash_members: dict[bytes, MediaRIT] = {}
        self._dynamic_member_count = 0
        for record in self.members.values():
            self._track_member(record)

    @staticmethod
    def _stored_content_hash(record: MediaRIT) -> bytes | None:
        """Return the immutable digest carried by a static resolved record."""
        if (
            record.status is MediaRITStatus.RESOLVED
            and record.preset_content_hash is not None
        ):
            return record.preset_content_hash
        return None

    def _track_member(self, record: MediaRIT) -> None:
        digest = self._stored_content_hash(record)
        if digest is None:
            self._dynamic_member_count += 1
            return
        self._content_hash_members.setdefault(digest, record)

    def _untrack_member(self, record: MediaRIT) -> None:
        digest = self._stored_content_hash(record)
        if digest is None:
            self._dynamic_member_count -= 1
            return
        if self._content_hash_members.get(digest) is not record:
            return
        self._content_hash_members.pop(digest)
        for candidate in self.members.values():
            if self._stored_content_hash(candidate) == digest:
                self._content_hash_members[digest] = candidate
                break

    def _find_by_stored_content_hash(self, record: MediaRIT) -> MediaRIT | None:
        """Return the first content match without scanning static inventory."""
        digest = self._stored_content_hash(record)
        if digest is None:
            return None
        if self._dynamic_member_count:
            return self.find_one(Selector.from_identifier(digest))
        cached = self._content_hash_members.get(digest)
        if cached is not None and self._stored_content_hash(cached) == digest:
            return cached
        return None

    def add(self, value: MediaRIT, _ctx=None) -> None:
        """Add a record and maintain the derived static content index."""
        previous = self.members.get(value.uid)
        super().add(value, _ctx=_ctx)
        stored = self.members[value.uid]
        if previous is stored:
            return
        if previous is not None and previous is not stored:
            self._untrack_member(previous)
        self._track_member(stored)

    def remove(self, key: UUID, _ctx=None) -> None:
        """Remove a record and maintain the derived static content index."""
        previous = self.members.get(key)
        super().remove(key, _ctx=_ctx)
        if previous is not None:
            self._untrack_member(previous)

    def clear(self) -> None:
        """Clear members and their derived content index."""
        super().clear()
        self._content_hash_members.clear()
        self._dynamic_member_count = 0

    def on_index(self, func: Callable[..., Any] | None = None, **kwargs):
        """Register an ``index`` handler on this registry's local behaviors."""
        return self.local_behaviors.register(func=func, task="index", **kwargs)

    def index(self,
              items: Iterable,
              mrt_cls: Type[MediaRIT] = None,
              extra_handlers: list[Behavior | Callable[..., Any]] | None = None) -> list[MediaRIT]:
        """
        Index a collection of data resources, deduplicating by content hash
        and running through the indexing pipeline.
        """
        mrt_cls = mrt_cls or self.mrt_cls

        results = []
        for item in items:
            # Initial record creation
            record = mrt_cls.from_source(item)

            logger.debug("initial mrit %r", record)

            # Check for duplicates by content
            if existing := self._find_by_stored_content_hash(record):
                results.append(existing)
                continue

            # Run through indexing pipeline
            receipts = BehaviorRegistry.chain_execute_all(
                call_args=(record,),
                ctx=resolve_ctx(
                    authorities=(self.local_behaviors,) if self.local_behaviors.members else None,
                ),
                task="index",
                inline_behaviors=extra_handlers,
            )
            indexed_record = CallReceipt.last_result(*receipts)
            if indexed_record is not None:
                if not isinstance(indexed_record, MediaRIT):
                    raise TypeError(
                        "Media index handlers must return MediaRIT or None, "
                        f"got {type(indexed_record)!r}",
                    )
                record = indexed_record

            # Add to registry
            logger.debug("indexed %r", record)
            self.add(record)
            results.append(record)

        return results

    def __contains__(self, item: MediaRIT | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, MediaRIT):
            if self._stored_content_hash(item) is None:
                return bool(self.find_one(Selector.from_identifier(item.content_hash())))
            return self._find_by_stored_content_hash(item) is not None
        return super().__contains__(item)

    def index_paths(self, paths: list[Path]):
        if not paths:
            raise ValueError("No paths specified")

        tic = datetime.now()
        import tangl.utils.shelved2 as shelved
        logger.debug("initial shelf hits: %s/misses: %s", shelved.hit_count, shelved.miss_count)

        import re
        ignored = []
        for path in paths:
            items = list(path.glob(r"*"))
            items_ = [ item for item in items if item.is_file() and re.match(r".*\.(jpg|png|webp)", str(item)) ]
            ignored_ = [ item.name for item in items if item.is_file() and not re.match(r".*\.(jpg|png|webp)", str(item)) ]
            ignored.extend(ignored_)
            self.index(items_)

        toc = datetime.now()
        logger.debug("loaded im path in %s secs", toc-tic)
        logger.debug("ignored: %s", ignored)
        logger.debug("final shelf hits: %s/misses: %s", shelved.hit_count, shelved.miss_count)

