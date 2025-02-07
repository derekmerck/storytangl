from __future__ import annotations
from typing import Iterable, Type, Optional, Any, Callable
from pathlib import Path
from uuid import UUID

from tangl.core.entity import Registry
from tangl.core.task_handler import TaskPipeline, PipelineStrategy
from .media_record import MediaRecord

from PIL import Image

DataType = Path | bytes | Image

class MediaRegistry(Registry[MediaRecord]):
    """
    A specialized registry for media assets that supports content-aware
    deduplication and flexible indexing strategies.
    """

    def __init__(self, *, label: str):
        super().__init__(label=label)
        # Set up a default indexing pipeline
        self.on_index = TaskPipeline[MediaRecord, Any](
            label=f"{label}_indexer",
            pipeline_strategy=PipelineStrategy.PIPELINE
        )

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
            record = self.on_index.execute(record, extra_handlers=extra_handlers, **context)

            # Add to registry
            self.add(record)
            results.append(record)

        return results

    def __contains__(self, item: MediaRecord | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, MediaRecord):
            return bool( self.find_one(alias=item.content_hash) )
        return super().__contains__(item)
