from typing import Self

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.behavior import BehaviorRegistry as BehaviorRegistry, HandlerPriority as Priority
from tangl.media.type_hints import Media

on_adapt_media_spec = BehaviorRegistry(label="adapt_media_spec", default_aggregation_strategy="pipeline")
on_create_media = BehaviorRegistry(label="create_media", default_aggregation_strategy="first")


class MediaSpec(Entity):

    def adapt_spec(self, *, ref: Entity = None, ctx: StringMap = None) -> Self:
        if ref is not None:
            if ctx is None and hasattr(ref, "gather_context"):
                ctx = ref.gather_context()
        if ref is not None or ctx is not None:
            adapted_spec = on_adapt_media_spec.execute_all(ref, ctx=ctx)
            return adapted_spec
        return self

    def create_media(self, *, ref: Entity = None, ctx: StringMap = None) -> tuple[Media, Self]:
        if ref is not None:
            if ctx is None and hasattr(ref, "gather_context"):
                ctx = ref.gather_context()
        adapted_spec = self.adapt_spec(ref=ref, ctx=ctx)
        media, realized_spec = on_create_media.execute_all(adapted_spec, ctx=ctx)
        return media, realized_spec
