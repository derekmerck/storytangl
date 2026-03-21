from __future__ import annotations
from typing import Iterable, Type, Any, Callable, ByteString
from uuid import UUID
import logging

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
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARNING)

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

            # logger.debug(f"indexing {record!r}")

            # Check for duplicates by content
            if record in self:
                results.append(self.find_one(Selector.from_identifier(record.content_hash())))
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
            logger.debug(f"indexed {record!r}")
            self.add(record)
            results.append(record)

        return results

    def __contains__(self, item: MediaRIT | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, MediaRIT):
            return bool(self.find_one(Selector.from_identifier(item.content_hash())))
        return super().__contains__(item)
