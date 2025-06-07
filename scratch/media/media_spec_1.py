from __future__ import annotations
from abc import abstractmethod
from typing import Protocol, Optional, TypeVar, Self

from tangl.core.entity import Node, HasContext, HandlerPipeline, PipelineStrategy
from .type_hints import Media

on_create_media = HandlerPipeline[Node, tuple[Media, Optional[Self]]](
    label="create_media",
    pipeline_strategy=PipelineStrategy.PIPELINE)

class MediaSpec(HasContext, Node):

    @abstractmethod
    def realize(self, **context) -> Self:
        # invoke whatever adapters are required to turn this node or its parent into a forge-appropriate spec
        ...

    @abstractmethod
    def get_creation_service(cls) -> MediaCreator:
        ...

    @on_create_media.register()
    def _call_class_creation_service(self, **context):
        forge = self.get_creation_service()
        return forge.create_media(spec=self, **context)

    def create_media(self, **context) -> tuple[Media, Optional[Self]]:
        # Returns a media object and an optional revised spec, if settings
        # were added on the creation side
        context = context or self.gather_context()
        return on_create_media.execute(self, **context)



MediaSpecT = TypeVar("MediaSpecT", bound=MediaSpec)

class MediaCreator(Protocol):

    def create_media(self, *, spec: MediaSpecT, **context) -> (Media, Optional[MediaSpecT]):
        # Returns a media object and an optional revised spec, if settings
        # were added on the creation side
        ...

