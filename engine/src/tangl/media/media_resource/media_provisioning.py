from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from PIL.Image import Image
from pydantic import ConfigDict, Field

from tangl.core import BehaviorRegistry, Priority, Record, Selector
from tangl.type_hints import UnstructuredData
from tangl.utils.sanitize_str import sanitize_str
from tangl.vm.provision.provisioner import ProvisionOffer, ProvisionPolicy
from tangl.vm.provision.requirement import Requirement

from ..media_creators.media_spec import MediaResolutionClass, MediaSpec
from ..media_data_type import MediaDataType
from ..story_media import get_story_resource_manager
from .media_resource_inv_tag import (
    MediaPersistencePolicy,
    MediaRITStatus,
    MediaResourceInventoryTag as MediaRIT,
)
from .media_inventory import MediaInventory
from .media_resource_registry import MediaResourceRegistry

on_provision_media = BehaviorRegistry(label="provision_media")


def _requirement_extra(requirement: Requirement) -> dict[str, Any]:
    extra = requirement.__pydantic_extra__
    if extra is None:
        extra = {}
        requirement.__pydantic_extra__ = extra
    return extra


def _coerce_media_type(value: Any) -> MediaDataType | None:
    if isinstance(value, MediaDataType):
        return value
    if isinstance(value, str):
        try:
            return MediaDataType(value)
        except ValueError:
            return MediaDataType._missing_(value)
    return None


def _infer_generated_media_type(media: Any, spec: MediaSpec) -> MediaDataType:
    for attr in ("data_type", "media_type"):
        value = _coerce_media_type(getattr(spec, attr, None))
        if value is not None and value is not MediaDataType.OTHER:
            return value

    if isinstance(media, Image):
        return MediaDataType.IMAGE
    if isinstance(media, str):
        return MediaDataType.VECTOR if media.lstrip().startswith("<svg") else MediaDataType.MEDIA
    if isinstance(media, tuple) and media and isinstance(media[0], (bytes, bytearray)):
        return MediaDataType.AUDIO
    if isinstance(media, (bytes, bytearray)):
        return MediaDataType.OTHER
    raise TypeError(f"Unsupported generated media payload type {type(media)!r}")


def _media_resolution_class(spec: MediaSpec) -> MediaResolutionClass:
    value = getattr(spec, "resolution_class", MediaResolutionClass.ASYNC)
    if isinstance(value, MediaResolutionClass):
        return value
    try:
        return MediaResolutionClass(str(value))
    except ValueError:
        return MediaResolutionClass.ASYNC


def _spec_payload(spec: MediaSpec | dict[str, Any] | None) -> dict[str, Any] | None:
    if spec is None:
        return None
    if isinstance(spec, MediaSpec):
        spec.commit_deterministic_seed()
        return spec.normalized_spec_payload()
    if isinstance(spec, dict):
        return dict(spec)
    return None


def _generated_extension(media: Any, *, data_type: MediaDataType) -> str:
    try:
        return data_type.ext
    except Exception:
        if isinstance(media, str) and media.lstrip().startswith("<svg"):
            return "svg"
        return "bin"


def _write_generated_media(media: Any, *, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(media, Image):
        media.save(output_path)
        return
    if isinstance(media, str):
        output_path.write_text(media, encoding="utf-8")
        return
    if isinstance(media, tuple) and media and isinstance(media[0], (bytes, bytearray)):
        output_path.write_bytes(bytes(media[0]))
        return
    if isinstance(media, (bytes, bytearray)):
        output_path.write_bytes(bytes(media))
        return
    raise TypeError(f"Unsupported generated media payload type {type(media)!r}")


def _story_media_base_name(
    *,
    spec: MediaSpec | None,
    requirement: Requirement,
) -> str:
    extra = _requirement_extra(requirement)
    base_name = str(
        getattr(spec, "label", None)
        or getattr(requirement, "media_basename", None)
        or extra.get("media_basename")
        or "media"
    )
    return sanitize_str(base_name).strip("_") or "media"


def _write_story_media(
    media: Any,
    *,
    manager: Any,
    base_name: str,
    fingerprint: str,
    data_type: MediaDataType,
) -> Path:
    extension = _generated_extension(media, data_type=data_type)
    output_path = manager.resource_path / f"{base_name}-{fingerprint[:12]}.{extension}"
    _write_generated_media(media, output_path=output_path)
    manager.register_file(output_path)
    return output_path


def _resolve_media_parent(requirement: Requirement, *, _ctx: Any = None) -> Any | None:
    graph = getattr(_ctx, "graph", None)
    ref_id = getattr(requirement, "media_ref_id", None) or _requirement_extra(requirement).get("media_ref_id")
    if graph is None or not isinstance(ref_id, UUID):
        return getattr(_ctx, "cursor", None)
    return graph.get(ref_id)


def _resolve_media_namespace(parent: Any | None, *, _ctx: Any = None) -> dict[str, Any] | None:
    if parent is None:
        return None
    get_ns = getattr(_ctx, "get_ns", None)
    if not callable(get_ns):
        return None
    return dict(get_ns(parent))


def _story_media_manager(*, _ctx: Any = None):
    graph = getattr(_ctx, "graph", None)
    if graph is None:
        return None

    manager = getattr(graph, "story_resources", None)
    if manager is None and getattr(graph, "story_id", None) is not None:
        manager = get_story_resource_manager(graph.story_id, create=True)
        if manager is not None:
            graph.story_resources = manager
    return manager


def _graph_media_by_identifier(graph: Any, identifier: str | None) -> MediaRIT | None:
    if graph is None or not identifier:
        return None
    found = graph.find_one(Selector(has_kind=MediaRIT, has_identifier=identifier))
    return found if isinstance(found, MediaRIT) else None


def materialize_rit_from_spec(
    spec: MediaSpec,
    *,
    requirement: Requirement,
    derivation_spec: MediaSpec | None = None,
    _ctx: Any = None,
) -> MediaRIT:
    """Materialize a story-scoped ``MediaRIT`` from one already-adapted spec."""
    graph = getattr(_ctx, "graph", None)
    if graph is None:
        raise RuntimeError("Media spec materialization requires graph context")

    extra = _requirement_extra(requirement)
    fingerprint = extra.get("has_identifier")
    if not isinstance(fingerprint, str) or not fingerprint:
        fingerprint = spec.spec_fingerprint()
        extra["has_identifier"] = fingerprint

    existing = _graph_media_by_identifier(graph, fingerprint)
    if existing is not None:
        return existing

    parent = _resolve_media_parent(requirement, _ctx=_ctx)
    ctx_ns = _resolve_media_namespace(parent, _ctx=_ctx)
    derivation_payload = _spec_payload(derivation_spec) or _spec_payload(spec)
    adapted_payload = _spec_payload(spec)
    source_step_id = getattr(_ctx, "cursor_id", None)
    scope_tag = "story"
    manager = _story_media_manager(_ctx=_ctx)
    if manager is not None:
        scope_tag = getattr(manager, "scope", scope_tag) or scope_tag

    if _media_resolution_class(spec) not in (
        MediaResolutionClass.INLINE,
        MediaResolutionClass.FAST_SYNC,
    ):
        data_type = _coerce_media_type(getattr(spec, "data_type", None) or getattr(spec, "media_type", None))
        return MediaRIT(
            label=_story_media_base_name(spec=spec, requirement=requirement),
            data_type=data_type,
            tags={f"scope:{scope_tag}"},
            status=MediaRITStatus.PENDING,
            persistence_policy=getattr(
                spec,
                "persistence_policy",
                MediaPersistencePolicy.CACHEABLE,
            ),
            derivation_spec=derivation_payload,
            adapted_spec=adapted_payload,
            adapted_spec_hash=fingerprint,
            source_step_id=source_step_id,
        )

    if manager is None:
        raise RuntimeError("Story media manager is not available")

    media, realized_spec = spec.create_media(
        ref=parent,
        ctx=ctx_ns,
    )
    realized_spec = realized_spec or spec

    existing = _graph_media_by_identifier(graph, fingerprint)
    if existing is not None:
        return existing

    data_type = _infer_generated_media_type(media, realized_spec)
    safe_base = _story_media_base_name(spec=realized_spec, requirement=requirement)
    output_path = _write_story_media(
        media,
        manager=manager,
        base_name=safe_base,
        fingerprint=fingerprint,
        data_type=data_type,
    )

    execution_payload = _spec_payload(realized_spec) if isinstance(realized_spec, MediaSpec) else None
    execution_hash = (
        realized_spec.spec_fingerprint()
        if isinstance(realized_spec, MediaSpec)
        else None
    )
    return MediaRIT(
        path=output_path,
        data_type=data_type,
        label=output_path.name,
        tags={f"scope:{manager.scope}"},
        status=MediaRITStatus.RESOLVED,
        persistence_policy=getattr(
            spec,
            "persistence_policy",
            MediaPersistencePolicy.CACHEABLE,
        ),
        adapted_spec=adapted_payload,
        adapted_spec_hash=fingerprint,
        derivation_spec=derivation_payload,
        execution_spec=execution_payload,
        execution_spec_hash=execution_hash,
        source_step_id=source_step_id,
    )


class MediaDependencyOffer(ProvisionOffer):
    """Compatibility offer wrapper used by media provisioning tests."""

    provider_id: UUID | None = None

    def accept(self, ctx: Any = None) -> Any:
        callback = self.callback
        if callback is None:
            return None
        try:
            return callback(_ctx=ctx)
        except TypeError:
            return callback(ctx)


class MediaProvisioner(Record):
    """Provision media dependencies from existing registry entries or inline templates."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirement: Requirement
    registries: list[MediaResourceRegistry] = Field(default_factory=list)

    @staticmethod
    def _requirement_identifier(requirement: Requirement) -> str | None:
        extra = requirement.__pydantic_extra__ or {}
        identifier = extra.get("has_identifier") or extra.get("identifier")
        return str(identifier) if isinstance(identifier, str) and identifier else None

    @staticmethod
    def _requirement_template(requirement: Requirement) -> UnstructuredData:
        extra = requirement.__pydantic_extra__ or {}
        template = extra.get("template")
        return template if isinstance(template, dict) else {}

    @staticmethod
    def _requirement_policy(requirement: Requirement) -> ProvisionPolicy:
        value = getattr(requirement, "provision_policy", ProvisionPolicy.ANY)
        if isinstance(value, ProvisionPolicy):
            return value
        try:
            return ProvisionPolicy(value)
        except Exception:
            return ProvisionPolicy.ANY

    def _resolve_existing(self, requirement: Requirement) -> MediaRIT | None:
        identifier = self._requirement_identifier(requirement)
        for registry in self.registries:
            if identifier:
                existing = registry.find_one(has_identifier=identifier)
                if existing is not None:
                    return existing
        return None

    def _resolve_create(self, provider_template: UnstructuredData) -> MediaRIT:
        if "data" not in provider_template:
            raise ValueError("Media CREATE requires template.data")
        provider = MediaRIT(
            data=provider_template["data"],
            data_type=provider_template.get("data_type", MediaDataType.OTHER),
        )
        if self.registries:
            self.registries[0].add(provider)
        return provider

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        policy = self._requirement_policy(requirement)
        if not (policy & ProvisionPolicy.ANY):
            return

        existing = self._resolve_existing(requirement)
        if existing is not None and (policy & ProvisionPolicy.EXISTING):
            yield MediaDependencyOffer(
                origin_id=self.uid,
                policy=ProvisionPolicy.EXISTING,
                callback=lambda *_, _existing=existing, **__: _existing,
                priority=Priority.NORMAL,
                distance_from_caller=0,
                candidate=existing,
                provider_id=existing.uid,
            )
            return

        template = self._requirement_template(requirement)
        if template and (policy & ProvisionPolicy.CREATE):
            yield MediaDependencyOffer(
                origin_id=self.uid,
                policy=ProvisionPolicy.CREATE,
                callback=lambda *_, _templ=template, **__: self._resolve_create(_templ),
                priority=Priority.LATE,
                distance_from_caller=1,
            )

    def generate_offers(self, *, ctx: Any = None) -> list[ProvisionOffer]:
        _ = ctx
        return list(self.get_dependency_offers(self.requirement))


@dataclass
class MediaInventoryProvisioner:
    """Offer EXISTING media providers discovered through authority inventories."""

    inventories: list[MediaInventory]

    @staticmethod
    def _graph_local_copy(candidate: MediaRIT, *, _ctx: Any = None) -> MediaRIT:
        graph = getattr(_ctx, "graph", None)
        if graph is candidate.registry:
            return candidate
        if graph is not None:
            existing = graph.get(candidate.uid)
            if isinstance(existing, MediaRIT):
                return existing
            for identifier in (
                getattr(candidate, "spec_fingerprint", None),
                candidate.get_content_hash().hex(),
            ):
                existing = _graph_media_by_identifier(graph, identifier)
                if isinstance(existing, MediaRIT):
                    return existing

        provider = type(candidate).model_validate(candidate.model_dump(mode="python"))
        provider.bind_registry(None)
        return provider

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        if not self.inventories:
            return

        selector = Selector(predicate=requirement.satisfied_by)
        for candidate in MediaInventory.chain_find_all(*self.inventories, selector=selector):
            yield ProvisionOffer(
                origin_id="MediaInventoryProvisioner",
                policy=ProvisionPolicy.EXISTING,
                priority=Priority.NORMAL,
                distance_from_caller=0,
                candidate=candidate,
                callback=lambda *_, _candidate=candidate, **kw: self._graph_local_copy(
                    _candidate,
                    _ctx=kw.get("_ctx"),
                ),
            )


@dataclass
class MediaSpecProvisioner:
    """Offer EXISTING or CREATE providers from dependency-carried media specs."""

    graph: Any | None = None

    @staticmethod
    def _requirement_policy(requirement: Requirement) -> ProvisionPolicy:
        return MediaProvisioner._requirement_policy(requirement)

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        _ctx: Any = None,
    ) -> Iterator[ProvisionOffer]:
        policy = self._requirement_policy(requirement)
        if not (policy & ProvisionPolicy.ANY):
            return

        extra = _requirement_extra(requirement)
        base_spec = getattr(requirement, "media_spec", None) or extra.get("media_spec")
        if not isinstance(base_spec, MediaSpec):
            return

        parent = _resolve_media_parent(requirement, _ctx=_ctx)
        ctx_ns = _resolve_media_namespace(parent, _ctx=_ctx)
        adapted_spec = base_spec.model_copy(deep=True).adapt_spec(ref=parent, ctx=ctx_ns)
        fingerprint = adapted_spec.spec_fingerprint()
        extra["has_identifier"] = fingerprint
        extra.setdefault("authored_path", fingerprint)
        extra["adapted_spec"] = adapted_spec.normalized_spec_payload()

        graph = self.graph or getattr(_ctx, "graph", None)
        existing = _graph_media_by_identifier(graph, fingerprint)
        if existing is not None and (policy & ProvisionPolicy.EXISTING):
            yield ProvisionOffer(
                origin_id="MediaSpecProvisioner",
                policy=ProvisionPolicy.EXISTING,
                priority=Priority.NORMAL,
                distance_from_caller=0,
                candidate=existing,
                callback=lambda *_, _existing=existing, **__: _existing,
            )
            return

        if policy & ProvisionPolicy.CREATE:
            resolution_class = _media_resolution_class(adapted_spec)
            yield ProvisionOffer(
                origin_id="MediaSpecProvisioner",
                policy=ProvisionPolicy.CREATE,
                priority=Priority.NORMAL if resolution_class in {
                    MediaResolutionClass.INLINE,
                    MediaResolutionClass.FAST_SYNC,
                } else Priority.LATE,
                distance_from_caller=1 if resolution_class in {
                    MediaResolutionClass.INLINE,
                    MediaResolutionClass.FAST_SYNC,
                } else 2,
                candidate=adapted_spec,
                callback=lambda *_, _spec=adapted_spec, _base_spec=base_spec, _requirement=requirement, **kw: materialize_rit_from_spec(
                    _spec,
                    requirement=_requirement,
                    derivation_spec=_base_spec,
                    _ctx=kw.get("_ctx"),
                ),
            )
