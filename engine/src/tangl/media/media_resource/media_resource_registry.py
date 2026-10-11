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
    __slots__ = (
        "_content_hash_members",
        "_dynamic_member_count",
        "_member_content_hashes",
    )

    def model_post_init(self, context: Any) -> None:
        """Build the static content index for directly initialized members."""
        super().model_post_init(context)
        self._rebuild_content_hash_index()

    def __copy__(self):
        """Copy members through Pydantic, then rebuild derived state."""
        clone = super().__copy__()
        clone._rebuild_content_hash_index()
        return clone

    def __deepcopy__(self, memo=None):
        """Deep-copy members through Pydantic, then rebuild derived state."""
        clone = super().__deepcopy__(memo)
        # A RegistryAware member can deep-copy its registry back-pointer while
        # this clone is only partially populated. The outer registry copy is the
        # one that owns the completed members mapping and rebuilds the index.
        if "members" in clone.__dict__:
            clone._rebuild_content_hash_index()
        return clone

    def __setstate__(self, state) -> None:
        """Restore derived state after Pydantic unpickles registry members."""
        super().__setstate__(state)
        self._rebuild_content_hash_index()

    @staticmethod
    def _stored_content_hash(record: MediaRIT) -> bytes | None:
        """Return the stored digest eligible for static inventory indexing."""
        if (
            record.status is MediaRITStatus.RESOLVED
            and record.preset_content_hash is not None
        ):
            return record.preset_content_hash
        return None

    def _rebuild_content_hash_index(self) -> None:
        """Rebuild the derived view from current member state."""
        self._content_hash_members: dict[bytes, MediaRIT] = {}
        self._member_content_hashes: dict[UUID, bytes | None] = {}
        self._dynamic_member_count = 0
        for record in self.members.values():
            digest = self._stored_content_hash(record)
            self._member_content_hashes[record.uid] = digest
            if digest is None:
                self._dynamic_member_count += 1
            else:
                self._content_hash_members.setdefault(digest, record)

    def _refresh_content_hash_member(self, digest: bytes) -> None:
        """Restore the first registry member recorded under ``digest``."""
        self._content_hash_members.pop(digest, None)
        for candidate in self.members.values():
            if self._member_content_hashes.get(candidate.uid) == digest:
                self._content_hash_members[digest] = candidate
                break

    def _sync_member_content_hash(self, record: MediaRIT) -> None:
        """Apply one normal add/overwrite operation to the derived view."""
        current = self._stored_content_hash(record)
        if record.uid not in self._member_content_hashes:
            self._member_content_hashes[record.uid] = current
            if current is None:
                self._dynamic_member_count += 1
            else:
                self._content_hash_members.setdefault(current, record)
            return

        previous = self._member_content_hashes[record.uid]
        if previous == current:
            return
        if previous is None:
            self._dynamic_member_count -= 1
        self._member_content_hashes[record.uid] = current
        if previous is not None:
            self._refresh_content_hash_member(previous)
        if current is None:
            self._dynamic_member_count += 1
        else:
            # An overwrite retains its dict position, so it can become the first
            # selector match for a digest already owned by a later member.
            self._refresh_content_hash_member(current)

    def _remove_member_content_hash(self, key: UUID) -> None:
        """Remove one normal registry member from the derived view."""
        if key not in self._member_content_hashes:
            return
        previous = self._member_content_hashes.pop(key)
        if previous is None:
            self._dynamic_member_count -= 1
        else:
            self._refresh_content_hash_member(previous)

    def _find_by_stored_content_hash(self, record: MediaRIT) -> MediaRIT | None:
        """Return the first content match without scanning static inventory."""
        digest = self._stored_content_hash(record)
        if digest is None:
            return None
        if self._dynamic_member_count:
            return self.find_one(Selector.from_identifier(digest))
        cached = self._content_hash_members.get(digest)
        if (
            cached is not None
            and self._member_content_hashes.get(cached.uid) == digest
            and self._stored_content_hash(cached) == digest
        ):
            return cached
        return None

    def add(self, value: MediaRIT, _ctx=None) -> None:
        """Add a record and maintain the derived static content index."""
        if resolve_ctx(_ctx) is not None:
            super().add(value, _ctx=_ctx)
            self._rebuild_content_hash_index()
            return
        super().add(value, _ctx=_ctx)
        stored = self.members[value.uid]
        self._sync_member_content_hash(stored)

    def remove(self, key: UUID, _ctx=None) -> None:
        """Remove a record and maintain the derived static content index."""
        super().remove(key, _ctx=_ctx)
        self._remove_member_content_hash(key)

    def clear(self) -> None:
        """Clear members and their derived content index."""
        super().clear()
        self._content_hash_members.clear()
        self._member_content_hashes.clear()
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
        self._rebuild_content_hash_index()

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
            if self._find_by_stored_content_hash(item) is not None:
                return True
            # Direct field mutation remains supported. Repair the derived view
            # after observing a selector match that the recorded view missed.
            found = self.find_one(Selector.from_identifier(item.content_hash()))
            if found is not None:
                self._rebuild_content_hash_index()
                return True
            return False
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

