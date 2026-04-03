from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from importlib import import_module
from typing import Any, Self

from tangl.type_hints import StringMap
from tangl.core import BehaviorRegistry, CallReceipt, Entity, Selector
from tangl.media.media_resource.media_resource_inv_tag import MediaPersistencePolicy
from tangl.media.type_hints import Media
from tangl.utils.hashing import hashing_func

on_adapt_media_spec = BehaviorRegistry(
    label="adapt_media_spec",
    default_aggregation_strategy="pipeline",
    default_task="adapt_media_spec",
)
on_create_media = BehaviorRegistry(
    label="create_media",
    default_aggregation_strategy="first",
    default_task="create_media",
)

_SPEC_ALIAS_MAP = {
    "checker": "tangl.media.media_creators.checker_forge.checker_spec.CheckerSpec",
    "comfy": "tangl.media.media_creators.comfy_forge.comfy_spec.ComfySpec",
    "stable": "tangl.media.media_creators.stable_forge.stable_spec.StableSpec",
    "vector": "tangl.media.media_creators.svg_forge.vector_spec.VectorSpec",
    "tts": "tangl.media.media_creators.tts_forge.tts_spec.TtsSpec",
}


class MediaResolutionClass(str, Enum):
    """Execution mode for a media specification."""

    INLINE = "inline"
    FAST_SYNC = "fast_sync"
    ASYNC = "async"
    EXTERNAL = "external"


class MediaSpec(Entity):
    """Base typed recipe for context-aware media generation."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.ASYNC
    persistence_policy: MediaPersistencePolicy = MediaPersistencePolicy.CACHEABLE
    fallback_ref: str | None = None

    @classmethod
    def resolve_spec_class(cls, hint: str | type["MediaSpec"] | None) -> type["MediaSpec"] | None:
        """Resolve an authored hint into one concrete ``MediaSpec`` subclass."""
        if hint is None:
            return None
        if isinstance(hint, type):
            return hint if issubclass(hint, cls) else None

        token = str(hint).strip()
        if not token:
            return None
        fqn = _SPEC_ALIAS_MAP.get(token.casefold(), token)
        if "." in fqn:
            module_name, class_name = fqn.rsplit(".", 1)
            try:
                resolved = getattr(import_module(module_name), class_name, None)
            except (ImportError, ModuleNotFoundError):
                return None
            if isinstance(resolved, type) and issubclass(resolved, cls):
                return resolved
        return cls.dereference_cls_name(fqn)

    @classmethod
    def from_authoring(cls, value: "MediaSpec | Mapping[str, Any]") -> "MediaSpec":
        """Hydrate inline authored media-spec payloads into typed spec objects."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError(f"Expected MediaSpec or mapping, got {type(value)!r}")

        payload = dict(value)
        spec_cls = cls.resolve_spec_class(
            payload.pop("kind", None)
            or payload.pop("spec_type", None)
        )
        if spec_cls is None:
            raise ValueError("Inline media spec requires one of: kind, spec_type")
        return spec_cls.model_validate(payload)

    def normalized_spec_payload(
        self,
        *,
        exclude: set[str] | None = None,
    ) -> dict[str, Any]:
        """Return identity-free data used for provenance and dedupe."""
        excluded = {"uid", "templ_hash"}
        if exclude:
            excluded.update(exclude)
        return self.model_dump(
            mode="python",
            exclude_none=True,
            exclude=excluded,
        )

    def commit_deterministic_seed(self) -> Self:
        """Assign a stable seed derived from spec content when the field exists."""
        if not hasattr(self, "seed"):
            return self
        if getattr(self, "seed", None) is not None:
            return self

        payload = {
            "spec_cls": self.__class__.__fqn__(),
            "data": self.normalized_spec_payload(exclude={"seed"}),
        }
        seed_bytes = hashing_func(payload, digest_size=4)
        setattr(self, "seed", int.from_bytes(seed_bytes[-4:], byteorder="little", signed=False))
        return self

    def spec_fingerprint(self) -> str:
        """Return a deterministic identifier for this spec's authored content."""
        self.commit_deterministic_seed()
        payload = {
            "spec_cls": self.__class__.__fqn__(),
            "data": self.normalized_spec_payload(),
        }
        return hashing_func(payload).hex()

    def adapt_spec(self, *, ref: Entity = None, ctx: StringMap = None) -> Self:
        if ref is not None:
            if ctx is None and hasattr(ref, "gather_context"):
                ctx = ref.gather_context()
        if isinstance(ctx, Mapping):
            ctx = dict(ctx)
        if ref is not None or ctx is not None:
            receipts = on_adapt_media_spec.dispatch(
                self,
                ctx=ctx,
                task=on_adapt_media_spec.default_task,
                selector=Selector(caller_kind=type(self)),
            )
            adapted_spec = CallReceipt.last_result(*receipts)
            if adapted_spec is not None:
                return adapted_spec
        return self

    def create_media(self, *, ref: Entity = None, ctx: StringMap = None) -> tuple[Media, Self]:
        if ref is not None:
            if ctx is None and hasattr(ref, "gather_context"):
                ctx = ref.gather_context()
        adapted_spec = self.adapt_spec(ref=ref, ctx=ctx)
        receipts = on_create_media.dispatch(
            adapted_spec,
            ctx=ctx,
            task=on_create_media.default_task,
            selector=Selector(caller_kind=type(adapted_spec)),
        )
        media_result = CallReceipt.first_result(*receipts)
        if media_result is None:
            creator_factory = getattr(type(adapted_spec), "get_creation_service", None)
            if callable(creator_factory):
                creator = creator_factory()
                media_result = creator.create_media(adapted_spec)
        if not isinstance(media_result, tuple) or len(media_result) != 2:
            raise ValueError("Media creator handlers must return (media, spec)")
        media, realized_spec = media_result
        return media, realized_spec
