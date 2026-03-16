from __future__ import annotations

import importlib
import sys
from typing import Any

from tangl.story.fabula import StoryCompiler, World

from .bundle import WorldBundle
from .codec import CodecRegistry, DecodeResult
from .compilers import AssetCompiler, DomainCompiler, MediaCompiler, ScriptCompiler


class _WorldDomainFacet:
    """Lightweight world-domain facet for world assembly."""

    def __init__(self) -> None:
        from tangl.core import BehaviorRegistry

        self.dispatch_registry = BehaviorRegistry(label="world_domain_dispatch")
        self._authorities: list[Any] = [self.dispatch_registry]
        self.modules: list[Any] = []
        self.class_registry: dict[str, Any] = {}

    def load_domain_module(self, domain_module: str) -> None:
        module = importlib.import_module(domain_module)
        self.modules.append(module)

        get_authorities = getattr(module, "get_authorities", None)
        if callable(get_authorities):
            for authority in get_authorities() or ():
                if authority not in self._authorities:
                    self._authorities.append(authority)

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


class _WorldAssetsFacet:
    """Lightweight assets facet placeholder for world assembly."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}


class WorldCompiler:
    """Orchestrate compilation from :class:`WorldBundle` to runtime :class:`World`."""

    def __init__(
        self,
        script_compiler: ScriptCompiler | None = None,
        asset_compiler: AssetCompiler | None = None,
        domain_compiler: DomainCompiler | None = None,
        media_compiler: MediaCompiler | None = None,
        story_compiler: StoryCompiler | None = None,
        codec_registry: CodecRegistry | None = None,
    ) -> None:
        self.script_compiler = script_compiler or ScriptCompiler()
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

        decode_result = self._decode_story_data(bundle=bundle, story_key=story_key)
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

        domain_facet, assets_facet, resources_facet = self._build_world_facets(bundle)
        story_bundle = self.story_compiler.compile(
            script_data,
            source_map=decode_result.source_map,
            codec_state=decode_result.codec_state,
            codec_id=codec_id,
        )
        world = World(
            label=bundle.manifest.story_label(story_key),
            bundle=story_bundle,
            domain=domain_facet,
            templates=story_bundle.template_registry,
            assets=assets_facet,
            resources=resources_facet,
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
            world_domain_facet,
            world_assets_facet,
            world_resources_facet,
        ) = self._build_world_facets(bundle)

        worlds: dict[str, World] = {}
        for story_key in bundle.manifest.story_keys():
            decode_result = self._decode_story_data(bundle=bundle, story_key=story_key)
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
            world = World(
                label=bundle.manifest.story_label(story_key),
                bundle=story_bundle,
                domain=world_domain_facet,
                templates=story_bundle.template_registry,
                assets=world_assets_facet,
                resources=world_resources_facet,
            )
            worlds[story_key] = world

        return worlds

    def _build_world_facets(
        self,
        bundle: WorldBundle,
    ) -> tuple[Any | None, Any | None, Any]:
        domain_facet: Any | None = None
        domain_module = self._get_domain_module(bundle)
        if domain_module:
            domain_facet = _WorldDomainFacet()
            self.domain_compiler.load_into(domain_module, domain_facet)

        assets_facet: Any | None = _WorldAssetsFacet()

        resources_facet = self.media_compiler.index(
            bundle.media_dir,
            organization_hints=bundle.manifest.media_organization,
        )
        return domain_facet, assets_facet, resources_facet

    def _decode_story_data(
        self,
        *,
        bundle: WorldBundle,
        story_key: str | None,
    ) -> DecodeResult:
        """Decode source files into runtime-ready script data.

        Notes
        -----
        During migration we preserve an escape hatch for custom script compilers
        that expose ``load_from_path``. This keeps research bundles usable while
        codecs are being ported to the new explicit interface.
        """

        script_paths = bundle.get_script_paths(story_key)
        codec_id = bundle.get_story_codec(story_key)
        if hasattr(self.script_compiler, "load_from_path") and not bundle.manifest.is_story_codec_explicit(story_key):
            merged: dict[str, Any] = {}
            for script_path in script_paths:
                loaded = self.script_compiler.load_from_path(script_path)
                if not isinstance(loaded, dict):
                    msg = f"Custom script compiler returned non-mapping for {script_path}"
                    raise ValueError(msg)
                merged |= loaded
            return DecodeResult(
                story_data=merged,
                source_map={"__source_files__": []},
                codec_state={
                    "codec_id": "script_compiler_bridge",
                    "script_paths": [str(path) for path in script_paths],
                    "story_key": story_key,
                },
                warnings=[
                    "Using legacy script compiler loading bridge; "
                    "set manifest codec explicitly to disable this fallback."
                ],
            )

        try:
            codec = self.codec_registry.get(codec_id)
        except ValueError:
            if hasattr(self.script_compiler, "load_from_path"):
                merged: dict[str, Any] = {}
                for script_path in script_paths:
                    loaded = self.script_compiler.load_from_path(script_path)
                    if not isinstance(loaded, dict):
                        msg = f"Custom script compiler returned non-mapping for {script_path}"
                        raise ValueError(msg)
                    merged |= loaded
                return DecodeResult(
                    story_data=merged,
                    source_map={"__source_files__": []},
                    codec_state={
                        "codec_id": "script_compiler_bridge",
                        "script_paths": [str(path) for path in script_paths],
                        "story_key": story_key,
                    },
                    warnings=[
                        "Using legacy script compiler loading bridge; "
                        "define a manifest codec for deterministic decode semantics."
                    ],
                )
            raise

        return codec.decode(bundle=bundle, script_paths=script_paths, story_key=story_key)

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
        if bundle.manifest.domain_module is not None:
            return bundle.manifest.domain_module

        if bundle.domain_dir is None:
            return None

        if str(bundle.bundle_root) not in sys.path:
            sys.path.insert(0, str(bundle.bundle_root))

        return f"{bundle.manifest.label}.domain"
