from __future__ import annotations
from typing import Iterable, Type, Optional, Any, Callable, ByteString
from pathlib import Path
from uuid import UUID

from pydantic import Field, model_validator
from PIL import Image

from tangl.business.core import Registry, TaskPipeline, PipelineStrategy
from .media_record import MediaRecord

DataType = Path | ByteString | Image

class MediaRegistry(Registry[MediaRecord]):
    """
    A specialized registry for media assets that supports content-aware
    deduplication and flexible indexing strategies.
    """
    on_index: TaskPipeline[MediaRecord, Any] = None

    @model_validator(mode="after")
    def _default_on_index(self):
        if not self.on_index:
            self.on_index = TaskPipeline(
            label=f"{self.label}_indexer",
            pipeline_strategy=PipelineStrategy.GATHER
        )
        return self

    def index(self,
              items: Iterable[DataType],
              record_cls: Type[MediaRecord] = MediaRecord,
              extra_handlers: Callable = None,
              **context) -> list[MediaRecord]:
        """
        Index a collection of media items, deduplicating by content hash
        and running through the indexing pipeline.
        """
        results = []
        for item in items:
            # Initial record creation
            record = record_cls.from_source(item)

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

    def __contains__(self, item: MediaRecord | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, MediaRecord):
            return bool( self.find_one(alias=item.content_hash) )
        return super().__contains__(item)
