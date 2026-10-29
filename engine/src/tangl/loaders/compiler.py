from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING, Any

from tangl.story.fabula import StoryCompiler, World, WorldBuilder
from tangl.story.fabula.compiler import StoryTemplateBundle
from tangl.story.episode import Block
from tangl.presentation.hints import StagingHints
from tangl.prose.portraits import HasPortraits
from tangl.presentation.projection import BooleanPreference, EnumPreference, UiPreferencesValue

from .bundle import WorldBundle
from .codec import CodecRegistry, DecodeResult, EncodeResult, StoryCodec
from .compilers import AssetCompiler, DomainCompiler, MediaCompiler

if TYPE_CHECKING:
    from tangl.media.media_resource.resource_manager import IndexHandler, ResourceManager


class _WorldDomainAdjuncts:
    """Collected domain-side adjuncts used during world assembly."""

    def __init__(self) -> None:
        from tangl.core import BehaviorRegistry

        self.dispatch_registry = BehaviorRegistry(label="world_domain_dispatch")
        self._authorities: list[Any] = [self.dispatch_registry]
        self.modules: list[Any] = []
        self.class_registry: dict[str, Any] = {}
        self.story_codecs: dict[str, StoryCodec] = {}
        self.media_index_handlers: list["IndexHandler"] = []

    def load_domain_module(self, domain_module: str) -> None:
        module = importlib.import_module(domain_module)
        self.modules.append(module)

        get_authorities = getattr(module, "get_authorities", None)
        if callable(get_authorities):
            for authority in get_authorities() or ():
                if all(authority is not existing for existing in self._authorities):
                    self._authorities.append(authority)

        get_story_codecs = getattr(module, "get_story_codecs", None)
        if callable(get_story_codecs):
            self.story_codecs.update(get_story_codecs())

        get_media_index_handlers = getattr(module, "get_media_index_handlers", None)
        if callable(get_media_index_handlers):
            for handler in get_media_index_handlers() or ():
                if handler not in self.media_index_handlers:
                    self.media_index_handlers.append(handler)


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
        return self._compile_story(bundle, story_key, self._build_world_facets(bundle))

    def compile_anthology(
        self,
        bundle: WorldBundle,
    ) -> dict[str, World]:
        """Compile every book, each exactly as opening it by id would.

        The books share one set of world facets, so the domain module, asset
        catalogs and media index are loaded once for the anthology; each book is
        then built by the same path ``compile(bundle, story_key=key)`` takes.
        """
        if not bundle.manifest.is_anthology:
            msg = f"{bundle.manifest.label} is not an anthology"
            raise ValueError(msg)
        facets = self._build_world_facets(bundle)
        return {
            story_key: self._compile_story(bundle, story_key, facets)
            for story_key in bundle.manifest.story_keys()
        }

    def _compile_story(
        self,
        bundle: WorldBundle,
        story_key: str | None,
        facets: tuple[_WorldDomainAdjuncts | None, _WorldAssetsFacet, ResourceManager | None],
    ) -> World:
        base_metadata = bundle.manifest.metadata.copy()

        domain_adjuncts, assets_facet, resources_facet = facets
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
            class_registry=(
                domain_adjuncts.class_registry if domain_adjuncts is not None else None
            ),
        )
        self._validate_preference_bindings(story_bundle, resources_facet)
        world = WorldBuilder().build(
            label=bundle.manifest.story_label(story_key),
            bundle=story_bundle,
            assets=assets_facet,
            resources=resources_facet,
            dispatch=domain_adjuncts.dispatch_registry if domain_adjuncts is not None else None,
            extra_authorities=domain_adjuncts.get_authorities() if domain_adjuncts is not None else None,
            class_registry=domain_adjuncts.class_registry if domain_adjuncts is not None else None,
            modules=domain_adjuncts.modules if domain_adjuncts is not None else None,
        )
        return world

    @staticmethod
    def _validate_preference_bindings(
        bundle: StoryTemplateBundle,
        resources: ResourceManager | None,
    ) -> None:
        """Check every staging binding a world declares against its world-static
        preferences, at load, wherever it is declared: a block's media, and the
        staging a speaker's packed portraits give each line's portrait. A new
        place a world declares staging hints is checked here too, so a binding
        to an undeclared preference never reaches a client's redraw."""
        declared = UiPreferencesValue.model_validate(
            {"preferences": bundle.metadata.get("ui_preferences", [])}
        )
        domains: dict[str, set[bool | str]] = {}
        for preference in declared.preferences:
            if isinstance(preference, BooleanPreference):
                domains[preference.preference_id] = {True, False}
            elif isinstance(preference, EnumPreference):
                domains[preference.preference_id] = set(preference.values)

        for template in bundle.template_registry.values():
            payload = template.payload
            if isinstance(payload, Block):
                for media in payload.media:
                    hints = StagingHints.model_validate(media.get("staging_hints") or {})
                    WorldCompiler._validate_staging_bindings(hints, domains)
                    WorldCompiler._validate_media_clips(media, hints, resources)
            if isinstance(payload, HasPortraits) and payload.portraits.staging_hints is not None:
                WorldCompiler._validate_staging_bindings(payload.portraits.staging_hints, domains)

    @staticmethod
    def _validate_staging_bindings(
        hints: StagingHints,
        domains: dict[str, set[bool | str]],
    ) -> None:
        """Refuse a visibility or clip binding to a preference or value not declared."""
        if hints.media_visibility is not None:
            WorldCompiler._validate_binding_values(
                hints.media_visibility.preference_id,
                hints.media_visibility.values,
                domains,
            )
        if hints.media_clip_binding is not None:
            for axis in hints.media_clip_binding.axes:
                if axis not in domains:
                    raise ValueError(f"Unknown ui preference {axis!r} in media clip binding")
            for row in hints.media_clip_binding.rows:
                for axis, value in zip(hints.media_clip_binding.axes, row.values, strict=True):
                    WorldCompiler._validate_binding_values(axis, [value], domains)

    @staticmethod
    def _validate_media_clips(
        media: dict[str, Any],
        hints: StagingHints,
        resources: ResourceManager | None,
    ) -> None:
        """Refuse authored clip names absent from a locally indexed still's sheets."""
        if resources is None:
            return
        clips = [clip for clip in [hints.media_clip] if clip is not None]
        if hints.media_clip_binding is not None:
            clips.extend(row.clip for row in hints.media_clip_binding.rows)
        if not clips:
            return
        name = media.get("name")
        if not isinstance(name, str):
            return
        resource = resources.get_rit(name)
        if resource is None:
            return
        available = {
            clip.name
            for sheet in resource.sprite_sheets
            for clip in sheet.manifest.clips
        }
        if not available:
            return
        unknown = sorted(set(clips) - available)
        if unknown:
            raise ValueError(f"Media {name!r} has no sprite-sheet clips: {', '.join(unknown)}")

    @staticmethod
    def _validate_binding_values(
        preference_id: str,
        values: list[bool | str],
        domains: dict[str, set[bool | str]],
    ) -> None:
        domain = domains.get(preference_id)
        if domain is None:
            raise ValueError(f"Unknown ui preference {preference_id!r} in media binding")
        for value in values:
            if value not in domain or (isinstance(value, bool) != all(isinstance(item, bool) for item in domain)):
                raise ValueError(f"Value {value!r} is outside ui preference {preference_id!r}'s domain")

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
            index_handlers=(
                domain_facet.media_index_handlers if domain_facet is not None else ()
            ),
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
