from __future__ import annotations
from typing import Iterable, Type, Any, Callable, ByteString
from uuid import UUID

from pydantic import model_validator

from tangl.core.entity import Registry
from tangl.core.handler import HandlerRegistry, BaseHandler
from .media_registry_tag import MediaRegistryTag as MRT

class MediaRegistry(Registry[MRT]):
    """
    A specialized registry for media assets that supports content-aware
    deduplication and flexible indexing strategies.
    """
    on_index: HandlerRegistry[MRT] = None
    mrt_cls: Type[MRT] = MRT

    @model_validator(mode="after")
    def _default_on_index(self):
        if not self.on_index:
            self.on_index = HandlerRegistry (
            label=f"{self.label}_indexer",
            default_aggregation_strategy="gather"
        )
        return self

    def index(self,
              items: Iterable,
              mrt_cls: Type[MRT] = None,
              extra_handlers: list[BaseHandler] = None) -> list[MRT]:
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
            self.on_index.execute_all(record, ctx=None, extra_handlers=extra_handlers)

            # Add to registry
            self.add(record)
            results.append(record)

        return results

    def __contains__(self, item: MRT | UUID) -> bool:
        """Find existing record with matching content hash"""
        if isinstance(item, MRT):
            return bool( self.find_one(alias=item.content_hash) )
        return super().__contains__(item)
