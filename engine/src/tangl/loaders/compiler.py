from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World

from .bundle import WorldBundle
from .compilers import AssetCompiler, DomainCompiler, MediaCompiler, ScriptCompiler


class WorldCompiler:
    """Orchestrate compilation from :class:`WorldBundle` to runtime :class:`World`."""

    def __init__(
        self,
        script_compiler: ScriptCompiler | None = None,
        asset_compiler: AssetCompiler | None = None,
        domain_compiler: DomainCompiler | None = None,
        media_compiler: MediaCompiler | None = None,
    ) -> None:
        self.script_compiler = script_compiler or ScriptCompiler()
        self.asset_compiler = asset_compiler or AssetCompiler()
        self.domain_compiler = domain_compiler or DomainCompiler()
        self.media_compiler = media_compiler or MediaCompiler()

    def compile(self, bundle: WorldBundle, story_key: str | None = None) -> World:
        base_metadata = bundle.manifest.metadata.copy()

        script_paths = bundle.get_script_paths(story_key)
        script_data = self._load_and_merge_scripts(script_paths)

        script_metadata = script_data.setdefault("metadata", {})
        for key, value in base_metadata.items():
            script_metadata.setdefault(key, value)

        default_title = script_metadata.get("title") or script_data.get("label") or bundle.manifest.label
        if story_key is not None and default_title == bundle.manifest.label:
            default_title = f"{bundle.manifest.label}_{story_key}"
        script_metadata.setdefault("title", default_title)

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

        label = bundle.manifest.label if story_key is None else f"{bundle.manifest.label}_{story_key}"

        world = World(
            label=label,
            script_manager=script_manager,
            domain_manager=domain_manager,
            asset_manager=asset_manager,
            resource_manager=resource_manager,
            metadata=world_metadata,
        )
        world._bundle = bundle  # noqa: SLF001
        return world

    def compile_anthology(self, bundle: WorldBundle) -> dict[str, World]:
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

        worlds: dict[str, World] = {}
        for story_key in bundle.manifest.story_keys():
            script_paths = bundle.get_script_paths(story_key)
            script_data = self._load_and_merge_scripts(script_paths)

            script_metadata = script_data.setdefault("metadata", {})
            for key, value in base_metadata.items():
                script_metadata.setdefault(key, value)

            default_title = script_metadata.get("title") or script_data.get("label") or bundle.manifest.label
            if default_title == bundle.manifest.label:
                default_title = f"{bundle.manifest.label}_{story_key}"
            script_metadata.setdefault("title", default_title)

            script_manager = self.script_compiler.compile(script_data)
            asset_manager = AssetManager()
            self.asset_compiler.setup_defaults(asset_manager)

            world_metadata = base_metadata.copy()
            world_metadata.update(script_manager.get_story_metadata())

            world = World(
                label=f"{bundle.manifest.label}_{story_key}",
                script_manager=script_manager,
                domain_manager=domain_manager,
                asset_manager=asset_manager,
                resource_manager=resource_manager,
                metadata=world_metadata,
            )
            world._bundle = bundle  # noqa: SLF001
            worlds[story_key] = world

        return worlds

    def _load_and_merge_scripts(self, script_paths: list[Path]) -> dict[str, Any]:
        script_data: dict[str, Any] = {}

        for script_path in script_paths:
            with open(script_path, encoding="utf-8") as script_file:
                data = yaml.safe_load(script_file) or {}

            if not isinstance(data, dict):
                msg = f"Script at {script_path} must be a mapping"
                raise ValueError(msg)

            script_data |= data

        return script_data

    def _get_domain_module(self, bundle: WorldBundle) -> str | None:
        if bundle.manifest.domain_module is not None:
            return bundle.manifest.domain_module

        if bundle.domain_dir is None:
            return None

        if str(bundle.domain_dir) not in sys.path:
            sys.path.insert(0, str(bundle.domain_dir))

        return f"{bundle.manifest.label}.domain"
