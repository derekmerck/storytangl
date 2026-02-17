from __future__ import annotations

import sys
from typing import Any

from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story38.fabula import StoryCompiler38, World38

from .bundle import WorldBundle
from .codec import CodecRegistry, DecodeResult
from .compilers import AssetCompiler, DomainCompiler, MediaCompiler, ScriptCompiler


class WorldCompiler:
    """Orchestrate compilation from :class:`WorldBundle` to runtime :class:`World`."""

    def __init__(
        self,
        script_compiler: ScriptCompiler | None = None,
        asset_compiler: AssetCompiler | None = None,
        domain_compiler: DomainCompiler | None = None,
        media_compiler: MediaCompiler | None = None,
        story38_compiler: StoryCompiler38 | None = None,
        codec_registry: CodecRegistry | None = None,
    ) -> None:
        self.script_compiler = script_compiler or ScriptCompiler()
        self.asset_compiler = asset_compiler or AssetCompiler()
        self.domain_compiler = domain_compiler or DomainCompiler()
        self.media_compiler = media_compiler or MediaCompiler()
        self.story38_compiler = story38_compiler or StoryCompiler38()
        self.codec_registry = codec_registry or CodecRegistry()

    def compile(
        self,
        bundle: WorldBundle,
        story_key: str | None = None,
        *,
        runtime_version: str = "37",
    ) -> World | World38:
        base_metadata = bundle.manifest.metadata.copy()

        decode_result = self._decode_story_data(bundle=bundle, story_key=story_key)
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

        if runtime_version == "38":
            story38_bundle = self.story38_compiler.compile(
                script_data,
                source_map=decode_result.source_map,
                codec_state=decode_result.codec_state,
                codec_id=codec_id,
            )
            world38 = World38(label=bundle.manifest.story_label(story_key), bundle=story38_bundle)
            return world38

        script_manager = self.script_compiler.compile(script_data)

        domain_manager = DomainManager()
        domain_module = self._get_domain_module(bundle)
        if domain_module:
            self.domain_compiler.load_into(domain_module, domain_manager)

        asset_manager = AssetManager()
        self.asset_compiler.setup_defaults(asset_manager)

        resource_manager = self.media_compiler.index(
            bundle.media_dir,
            organization_hints=bundle.manifest.media_organization,
        )

        world_metadata = base_metadata.copy()
        world_metadata.update(script_manager.get_story_metadata())

        world = World(
            label=bundle.manifest.story_label(story_key),
            script_manager=script_manager,
            domain_manager=domain_manager,
            asset_manager=asset_manager,
            resource_manager=resource_manager,
            metadata=world_metadata,
        )
        world._bundle = bundle  # noqa: SLF001
        return world

    def compile_anthology(
        self,
        bundle: WorldBundle,
        *,
        runtime_version: str = "37",
    ) -> dict[str, World | World38]:
        if not bundle.manifest.is_anthology:
            msg = f"{bundle.manifest.label} is not an anthology"
            raise ValueError(msg)

        base_metadata = bundle.manifest.metadata.copy()

        domain_manager = DomainManager()
        domain_module = self._get_domain_module(bundle)
        if domain_module:
            self.domain_compiler.load_into(domain_module, domain_manager)

        resource_manager = self.media_compiler.index(
            bundle.media_dir,
            organization_hints=bundle.manifest.media_organization,
        )

        worlds: dict[str, World | World38] = {}
        for story_key in bundle.manifest.story_keys():
            decode_result = self._decode_story_data(bundle=bundle, story_key=story_key)
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

            if runtime_version == "38":
                story38_bundle = self.story38_compiler.compile(
                    script_data,
                    source_map=decode_result.source_map,
                    codec_state=decode_result.codec_state,
                    codec_id=codec_id,
                )
                worlds[story_key] = World38(
                    label=bundle.manifest.story_label(story_key),
                    bundle=story38_bundle,
                )
                continue

            script_manager = self.script_compiler.compile(script_data)
            asset_manager = AssetManager()
            self.asset_compiler.setup_defaults(asset_manager)

            world_metadata = base_metadata.copy()
            world_metadata.update(script_manager.get_story_metadata())

            world = World(
                label=bundle.manifest.story_label(story_key),
                script_manager=script_manager,
                domain_manager=domain_manager,
                asset_manager=asset_manager,
                resource_manager=resource_manager,
                metadata=world_metadata,
            )
            world._bundle = bundle  # noqa: SLF001
            worlds[story_key] = world

        return worlds

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

    def _get_domain_module(self, bundle: WorldBundle) -> str | None:
        if bundle.manifest.domain_module is not None:
            return bundle.manifest.domain_module

        if bundle.domain_dir is None:
            return None

        if str(bundle.bundle_root) not in sys.path:
            sys.path.insert(0, str(bundle.bundle_root))

        return f"{bundle.manifest.label}.domain"
