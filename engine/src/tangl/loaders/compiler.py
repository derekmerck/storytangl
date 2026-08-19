from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING, Any, Callable

from tangl.story.fabula import StoryCompiler, World, WorldBuilder
from tangl.story.fabula.compiler import StoryTemplateBundle

from .bundle import WorldBundle
from .codec import CodecRegistry, DecodeResult, EncodeResult, StoryCodec
from .compilers import AssetCompiler, DomainCompiler, MediaCompiler

if TYPE_CHECKING:
    from tangl.media.media_resource.resource_manager import ResourceManager


class _WorldDomainAdjuncts:
    """Collected domain-side adjuncts used during world assembly."""

    def __init__(self) -> None:
        from tangl.core import BehaviorRegistry

        self.dispatch_registry = BehaviorRegistry(label="world_domain_dispatch")
        self._authorities: list[Any] = [self.dispatch_registry]
        self._story_info_projector_factories: list[Callable[[], Any]] = []
        self.modules: list[Any] = []
        self.class_registry: dict[str, Any] = {}
        self.story_codecs: dict[str, StoryCodec] = {}

    def load_domain_module(self, domain_module: str) -> None:
        module = importlib.import_module(domain_module)
        self.modules.append(module)

        get_authorities = getattr(module, "get_authorities", None)
        if callable(get_authorities):
            for authority in get_authorities() or ():
                if authority not in self._authorities:
                    self._authorities.append(authority)

        get_story_info_projector = getattr(module, "get_story_info_projector", None)
        if callable(get_story_info_projector):
            self._story_info_projector_factories.append(get_story_info_projector)

        get_story_codecs = getattr(module, "get_story_codecs", None)
        if callable(get_story_codecs):
            self.story_codecs.update(get_story_codecs())

        try:
            from tangl.core import Entity
        except Exception:
            Entity = object  # type: ignore[assignment]

        for name, value in vars(module).items():
            if not isinstance(value, type):
                continue
            if value is Entity:
                continue
            if issubclass(value, Entity):
                self.class_registry[name] = value

    def get_authorities(self) -> list[Any]:
        return list(self._authorities)

    def get_story_info_projector(self) -> Any | None:
        for factory in self._story_info_projector_factories:
            projector = factory()
            if projector is not None:
                return projector
        return None


class _WorldAssetsFacet:
    """Lightweight assets facet placeholder for world assembly."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def get_token_catalogs(self, **_kwargs: Any) -> list[Any]:
        return list(self.values.values())


class WorldCompiler:
    """Orchestrate compilation from :class:`WorldBundle` to runtime :class:`World`."""

    def __init__(
        self,
        asset_compiler: AssetCompiler | None = None,
        domain_compiler: DomainCompiler | None = None,
        media_compiler: MediaCompiler | None = None,
        story_compiler: StoryCompiler | None = None,
        codec_registry: CodecRegistry | None = None,
    ) -> None:
        self.asset_compiler = asset_compiler or AssetCompiler()
        self.domain_compiler = domain_compiler or DomainCompiler()
        self.media_compiler = media_compiler or MediaCompiler()
        self.story_compiler = story_compiler or StoryCompiler()
        self.codec_registry = codec_registry or CodecRegistry()

    def compile(
        self,
        bundle: WorldBundle,
        story_key: str | None = None,
    ) -> World:
        base_metadata = bundle.manifest.metadata.copy()

        domain_adjuncts, assets_facet, resources_facet = self._build_world_facets(bundle)
        decode_result = self._decode_story_data(
            bundle=bundle,
            story_key=story_key,
            local_codecs=domain_adjuncts.story_codecs if domain_adjuncts is not None else {},
        )
        self._propagate_loss_records(decode_result)
        script_data = decode_result.story_data
        codec_id = str(decode_result.codec_state.get("codec_id") or bundle.get_story_codec(story_key))

        script_metadata = script_data.setdefault("metadata", {})
        for key, value in base_metadata.items():
            script_metadata.setdefault(key, value)
        script_metadata.setdefault("codec_id", codec_id)
        if decode_result.warnings:
            script_metadata.setdefault("codec_warnings", [])
            script_metadata["codec_warnings"].extend(decode_result.warnings)

        default_title = script_metadata.get("title") or script_data.get("label") or bundle.manifest.label
        if story_key is not None and default_title == bundle.manifest.label:
            default_title = bundle.manifest.story_label(story_key)
        script_metadata.setdefault("title", default_title)

        story_bundle = self.story_compiler.compile(
            script_data,
            source_map=decode_result.source_map,
            codec_state=decode_result.codec_state,
            codec_id=codec_id,
        )
        world = WorldBuilder().build(
            label=bundle.manifest.story_label(story_key),
            bundle=story_bundle,
            assets=assets_facet,
            resources=resources_facet,
            dispatch=domain_adjuncts.dispatch_registry if domain_adjuncts is not None else None,
            extra_authorities=domain_adjuncts.get_authorities() if domain_adjuncts is not None else None,
            class_registry=domain_adjuncts.class_registry if domain_adjuncts is not None else None,
            modules=domain_adjuncts.modules if domain_adjuncts is not None else None,
            story_info_projector=(
                domain_adjuncts.get_story_info_projector() if domain_adjuncts is not None else None
            ),
        )
        return world

    def compile_anthology(
        self,
        bundle: WorldBundle,
    ) -> dict[str, World]:
        if not bundle.manifest.is_anthology:
            msg = f"{bundle.manifest.label} is not an anthology"
            raise ValueError(msg)

        base_metadata = bundle.manifest.metadata.copy()

        (
            world_domain_adjuncts,
            world_assets_facet,
            world_resources_facet,
        ) = self._build_world_facets(bundle)

        worlds: dict[str, World] = {}
        for story_key in bundle.manifest.story_keys():
            decode_result = self._decode_story_data(
                bundle=bundle,
                story_key=story_key,
                local_codecs=(
                    world_domain_adjuncts.story_codecs
                    if world_domain_adjuncts is not None
                    else {}
                ),
            )
            self._propagate_loss_records(decode_result)
            script_data = decode_result.story_data
            codec_id = str(decode_result.codec_state.get("codec_id") or bundle.get_story_codec(story_key))

            script_metadata = script_data.setdefault("metadata", {})
            for key, value in base_metadata.items():
                script_metadata.setdefault(key, value)
            script_metadata.setdefault("codec_id", codec_id)
            if decode_result.warnings:
                script_metadata.setdefault("codec_warnings", [])
                script_metadata["codec_warnings"].extend(decode_result.warnings)

            default_title = script_metadata.get("title") or script_data.get("label") or bundle.manifest.label
            if default_title == bundle.manifest.label:
                default_title = bundle.manifest.story_label(story_key)
            script_metadata.setdefault("title", default_title)

            story_bundle = self.story_compiler.compile(
                script_data,
                source_map=decode_result.source_map,
                codec_state=decode_result.codec_state,
                codec_id=codec_id,
            )
            world = WorldBuilder().build(
                label=bundle.manifest.story_label(story_key),
                bundle=story_bundle,
                assets=world_assets_facet,
                resources=world_resources_facet,
                dispatch=(
                    world_domain_adjuncts.dispatch_registry
                    if world_domain_adjuncts is not None
                    else None
                ),
                extra_authorities=(
                    world_domain_adjuncts.get_authorities()
                    if world_domain_adjuncts is not None
                    else None
                ),
                class_registry=(
                    world_domain_adjuncts.class_registry
                    if world_domain_adjuncts is not None
                    else None
                ),
                modules=world_domain_adjuncts.modules if world_domain_adjuncts is not None else None,
                story_info_projector=(
                    world_domain_adjuncts.get_story_info_projector()
                    if world_domain_adjuncts is not None
                    else None
                ),
            )
            worlds[story_key] = world

        return worlds

    def encode(
        self,
        bundle: WorldBundle,
        story_bundle: StoryTemplateBundle,
        story_key: str | None = None,
    ) -> EncodeResult:
        """Encode one compiled story bundle without writing source files."""

        domain_adjuncts = self._load_domain_adjuncts(bundle)
        local_codecs = domain_adjuncts.story_codecs if domain_adjuncts is not None else {}
        manifest_codec_key = bundle.get_story_codec(story_key)
        codec = self._resolve_story_codec(
            manifest_codec_key,
            local_codecs=local_codecs,
        )
        if story_bundle.codec_id not in (None, manifest_codec_key, codec.codec_id):
            raise ValueError(
                "Compiled story codec "
                f"{story_bundle.codec_id!r} disagrees with manifest codec "
                f"{manifest_codec_key!r}",
            )

        return codec.encode(
            bundle=bundle,
            runtime_data=self.story_compiler.decompile(story_bundle),
            story_key=story_key,
            codec_state=story_bundle.codec_state,
        )

    def _build_world_facets(
        self,
        bundle: WorldBundle,
    ) -> tuple[
        _WorldDomainAdjuncts | None,
        _WorldAssetsFacet,
        ResourceManager | None,
    ]:
        domain_facet = self._load_domain_adjuncts(bundle)

        assets_facet = _WorldAssetsFacet()
        self.asset_compiler.load_into(
            bundle,
            assets_facet,
            domain_facet.class_registry if domain_facet is not None else {},
        )

        resources_facet = self.media_compiler.index(
            bundle.media_dir,
            organization_hints=bundle.manifest.media_organization,
        )
        return domain_facet, assets_facet, resources_facet

    def _load_domain_adjuncts(self, bundle: WorldBundle) -> _WorldDomainAdjuncts | None:
        domain_module = self._get_domain_module(bundle)
        if domain_module is None:
            return None
        domain_adjuncts = _WorldDomainAdjuncts()
        self.domain_compiler.load_into(domain_module, domain_adjuncts)
        return domain_adjuncts

    def _decode_story_data(
        self,
        *,
        bundle: WorldBundle,
        story_key: str | None,
        local_codecs: dict[str, StoryCodec] | None = None,
    ) -> DecodeResult:
        """Decode source files into runtime-ready script data."""

        script_paths = bundle.get_script_paths(story_key)
        codec_id = bundle.get_story_codec(story_key)
        codec = self._resolve_story_codec(codec_id, local_codecs=local_codecs)

        return codec.decode(bundle=bundle, script_paths=script_paths, story_key=story_key)

    def _resolve_story_codec(
        self,
        codec_id: str,
        *,
        local_codecs: dict[str, StoryCodec] | None = None,
    ) -> StoryCodec:
        return (local_codecs or {}).get(codec_id) or self.codec_registry.get(codec_id)

    @staticmethod
    def _propagate_loss_records(decode_result: DecodeResult) -> None:
        """Persist structured codec loss records into codec_state."""
        if not decode_result.loss_records:
            return

        decode_result.codec_state.setdefault(
            "loss_records",
            [
                {
                    "kind": record.kind.value,
                    "feature": record.feature,
                    "passage": record.passage,
                    "excerpt": record.excerpt,
                    "note": record.note,
                }
                for record in decode_result.loss_records
            ],
        )
        decode_result.codec_state.setdefault(
            "loss_record_count",
            len(decode_result.loss_records),
        )

    def _get_domain_module(self, bundle: WorldBundle) -> str | None:
        if str(bundle.bundle_root) not in sys.path:
            sys.path.insert(0, str(bundle.bundle_root))

        if bundle.manifest.domain_module is not None:
            return bundle.manifest.domain_module

        if bundle.domain_dir is None:
            return None

        return f"{bundle.manifest.label}.domain"
