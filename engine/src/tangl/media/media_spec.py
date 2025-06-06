from typing import Self
from abc import abstractmethod

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.handler import HandlerRegistry
from .type_hints import Media

on_adapt_media_spec = HandlerRegistry(label="realize_media_spec", default_aggregation_strategy="pipeline")


class MediaSpec(Entity):

    def adapt_spec(self, entity: Entity = None, ctx: StringMap = None) -> Self:
        if ctx is None and hasattr(entity, "gather_context"):
            ctx = entity.gather_context()
        # ctx['self'] should be the entity to adapt for
        ctx.setdefault('self', entity)
        return on_adapt_media_spec.execute_all(self, ctx=ctx)

    @classmethod
    @abstractmethod
    def get_creator_service(cls):
        ...

    def create_media(self) -> tuple[Media, Self]:
        service = self.get_creation_service()
        return service.create_media(self)
