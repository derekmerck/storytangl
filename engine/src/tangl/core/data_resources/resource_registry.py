from __future__ import annotations
from typing import Iterable, Type, Any, Callable, ByteString
from uuid import UUID

from pydantic import model_validator

from ..registry import Registry
from ..handler_pipeline import HandlerPipeline, PipelineStrategy
from .resource_tag import ResourceInventoryTag as RIT

# DataType = Path | ByteString | Image

class ResourceRegistry(Registry[RIT]):
    """
    A specialized registry for media assets that supports content-aware
    deduplication and flexible indexing strategies.
    """
    on_index: HandlerPipeline[RIT, Any] = None
    rit_cls: Type[RIT] = RIT

    @model_validator(mode="after")
    def _default_on_index(self):
        if not self.on_index:
            self.on_index = HandlerPipeline (
            label=f"{self.label}_indexer",
            pipeline_strategy=PipelineStrategy.GATHER
        )
        return self

    def index(self,
              items: Iterable,
              rit_cls: Type[RIT] = None,
              extra_handlers: Callable = None,
              **context) -> list[RIT]:
        """
        Index a collection of media items, deduplicating by content hash
        and running through the indexing pipeline.
        """
        rit_cls = rit_cls or self.rit_cls

        results = []
        for item in items:
            # Initial record creation
            record = rit_cls.from_source(item)

            # Check for duplicates by content
            if record in self:
                results.append(self.find_one(alias=record.content_hash))
                continue

            # Run through indexing pipeline
            self.on_index.execute(record, extra_handlers=extra_handlers, **context)

            # Add to registry
            self.add(record)
            results.append(record)

        return results

    def __contains__(self, item: RIT | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, RIT):
            return bool( self.find_one(alias=item.content_hash) )
        return super().__contains__(item)
