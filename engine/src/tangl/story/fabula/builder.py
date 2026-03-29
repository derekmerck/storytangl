from __future__ import annotations

from typing import Any

from tangl.core import BehaviorRegistry, TemplateRegistry

from .compiler import StoryTemplateBundle
from .world import World, _coerce_template_registries


def _dedupe(values: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.append(value)
    return seen


class WorldBuilder:
    """Assemble a :class:`World` from a compiled bundle plus adjunct providers."""

    @staticmethod
    def _coerce_domain(
        domain: Any | None,
        *,
        story_info_projector: Any | None,
    ) -> dict[str, Any]:
        if domain is None:
            return {}

        dispatch = getattr(domain, "dispatch_registry", None)
        authorities: list[Any] = []
        get_authorities = getattr(domain, "get_authorities", None)
        if callable(get_authorities):
            authorities = list(get_authorities() or [])

        class_registry = getattr(domain, "class_registry", None)
        modules = getattr(domain, "modules", None)

        projector = story_info_projector
        if projector is None:
            get_projector = getattr(domain, "get_story_info_projector", None)
            if callable(get_projector):
                projector = get_projector()

        return {
            "dispatch": dispatch if isinstance(dispatch, BehaviorRegistry) else None,
            "extra_authorities": authorities,
            "class_registry": dict(class_registry or {}),
            "modules": list(modules or []),
            "story_info_projector": projector,
        }

    def build(
        self,
        *,
        label: str,
        bundle: StoryTemplateBundle,
        world_type: type[World] = World,
        assets: Any | None = None,
        resources: Any | None = None,
        extra_authorities: list[Any] | None = None,
        class_registry: dict[str, Any] | None = None,
        modules: list[Any] | None = None,
        story_info_projector: Any | None = None,
        dispatch: BehaviorRegistry | None = None,
        extra_template_registries: list[TemplateRegistry] | None = None,
        domain: Any | None = None,
    ) -> World:
        if domain is not None:
            coerced = self._coerce_domain(
                domain,
                story_info_projector=story_info_projector,
            )
            if dispatch is None:
                dispatch = coerced.get("dispatch")
            if extra_authorities is None:
                extra_authorities = list(coerced.get("extra_authorities") or [])
            if class_registry is None:
                class_registry = dict(coerced.get("class_registry") or {})
            if modules is None:
                modules = list(coerced.get("modules") or [])
            if story_info_projector is None:
                story_info_projector = coerced.get("story_info_projector")

        if dispatch is None:
            dispatch = BehaviorRegistry(label=f"{label}.world_dispatch")
        authorities = _dedupe([dispatch, *(extra_authorities or [])])
        extra = [authority for authority in authorities if authority is not dispatch]
        class_registry = dict(class_registry or {})
        modules = list(modules or [])
        registries = list(extra_template_registries or [])

        world = world_type(
            label=label,
            bundle=bundle,
            dispatch=dispatch,
            templates=bundle.template_registry,
            metadata=dict(bundle.metadata),
            locals=dict(bundle.locals),
            entry_template_ids=list(bundle.entry_template_ids),
            source_map=dict(bundle.source_map),
            codec_state=dict(bundle.codec_state),
            codec_id=bundle.codec_id,
            issues=list(bundle.issues),
            extra_template_registries=registries,
            assets=assets,
            resources=resources,
            class_registry=class_registry,
            modules=modules,
            extra_authorities=extra,
            story_info_projector=story_info_projector,
        )
        return world
