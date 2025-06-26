from __future__ import annotations
from typing import Iterable, Type, Any, Callable, ByteString
from uuid import UUID

from pydantic import model_validator

from tangl.core.entity import Registry
from tangl.core.dispatch import HandlerRegistry, Handler
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

class MediaResourceRegistry(Registry[MediaRIT]):
    """
    A specialized registry for media assets that supports content-aware
    deduplication and flexible indexing strategies.
    """
    on_index: HandlerRegistry[MediaRIT] = None
    mrt_cls: Type[MediaRIT] = MediaRIT

    @model_validator(mode="after")
    def _default_on_index(self):
        if not self.on_index:
            self.on_index = HandlerRegistry (
            label=f"{self.label}_indexer",
            aggregation_strategy="gather"
        )
        return self

    def index(self,
              items: Iterable,
              mrt_cls: Type[MediaRIT] = None,
              extra_handlers: list[Handler] = None) -> list[MediaRIT]:
        """
        Index a collection of data resources, deduplicating by content hash
        and running through the indexing pipeline.
        """
        mrt_cls = mrt_cls or self.mrt_cls

        results = []
        for item in items:
            # Initial record creation
            record = mrt_cls.from_source(item)

            # Check for duplicates by content
            if record in self:
                results.append(self.find_one(alias=record.content_hash))
                continue

            # Run through indexing pipeline
            self.on_index.execute_all_for(record, ctx=None, extra_handlers=extra_handlers)

            # Add to registry
            self.add(record)
            results.append(record)

        return results

    def __contains__(self, item: MediaRIT | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, MediaRIT):
            return bool( self.find_one(alias=item.content_hash) )
        return super().__contains__(item)
