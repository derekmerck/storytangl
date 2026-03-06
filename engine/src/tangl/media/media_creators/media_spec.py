from typing import Self

from tangl.type_hints import StringMap
from tangl.core import BehaviorRegistry, CallReceipt, Entity
from tangl.media.type_hints import Media

on_adapt_media_spec = BehaviorRegistry(label="adapt_media_spec", default_aggregation_strategy="pipeline")
on_create_media = BehaviorRegistry(label="create_media", default_aggregation_strategy="first")


class MediaSpec(Entity):

    def adapt_spec(self, *, ref: Entity = None, ctx: StringMap = None) -> Self:
        if ref is not None:
            if ctx is None and hasattr(ref, "gather_context"):
                ctx = ref.gather_context()
        if ref is not None or ctx is not None:
            receipts = on_adapt_media_spec.dispatch(self, ctx=ctx)
            adapted_spec = CallReceipt.last_result(*receipts)
            if adapted_spec is not None:
                return adapted_spec
        return self

    def create_media(self, *, ref: Entity = None, ctx: StringMap = None) -> tuple[Media, Self]:
        if ref is not None:
            if ctx is None and hasattr(ref, "gather_context"):
                ctx = ref.gather_context()
        adapted_spec = self.adapt_spec(ref=ref, ctx=ctx)
        receipts = on_create_media.dispatch(adapted_spec, ctx=ctx)
        media_result = CallReceipt.first_result(*receipts)
        if not isinstance(media_result, tuple) or len(media_result) != 2:
            raise ValueError("Media creator handlers must return (media, spec)")
        media, realized_spec = media_result
        return media, realized_spec
