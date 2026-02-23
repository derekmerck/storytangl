from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .compiler import StoryCompiler38, StoryTemplateBundle
from .materializer import StoryMaterializer38
from .script_manager38 import ScriptManager38
from .types import InitMode, StoryInitResult


@dataclass(slots=True)
class World38:
    """Story38 world entrypoint over compiled template bundles."""

    label: str
    bundle: StoryTemplateBundle
    script_manager: ScriptManager38 | None = None
    domain: Any | None = None
    templates: Any | None = None
    assets: Any | None = None
    resources: Any | None = None

    def __post_init__(self) -> None:
        if self.templates is None:
            self.templates = self.bundle.template_registry
        if self.script_manager is None:
            self.script_manager = ScriptManager38(
                template_registry=self.bundle.template_registry,
                world_scope_provider=self._world_template_scope_groups,
            )

    @property
    def metadata(self) -> dict[str, Any]:
        return self.bundle.metadata

    def create_story(
        self,
        story_label: str,
        *,
        init_mode: InitMode = InitMode.EAGER,
    ) -> StoryInitResult:
        materializer = StoryMaterializer38()
        return materializer.create_story(
            bundle=self.bundle,
            story_label=story_label,
            init_mode=init_mode,
            world=self,
        )

    def get_authorities(self) -> list[object]:
        """Return optional domain/world behavior registries."""
        domain = self.domain
        if domain is None:
            return []

        authorities: list[object] = []
        get_authorities = getattr(domain, "get_authorities", None)
        if callable(get_authorities):
            for authority in get_authorities() or ():
                if authority not in authorities:
                    authorities.append(authority)
        return authorities

    def get_template_scope_groups(
        self,
        *,
        caller: Any = None,
        graph: Any = None,
    ) -> list[Iterable[Any]]:
        """Optional world-authoritative template groups for runtime provisioning."""
        template_facet = self.templates
        if template_facet is None or template_facet is self.bundle.template_registry:
            return []

        get_scope_groups = getattr(template_facet, "get_template_scope_groups", None)
        if callable(get_scope_groups):
            groups = get_scope_groups(caller=caller, graph=graph)
            return list(groups or [])

        values = getattr(template_facet, "values", None)
        if callable(values):
            return [list(values())]
        return []

    def _world_template_scope_groups(
        self,
        *,
        caller: Any = None,
        graph: Any = None,
    ) -> list[Iterable[Any]]:
        return list(self.get_template_scope_groups(caller=caller, graph=graph) or [])

    def find_template(self, reference: str) -> Any | None:
        """Find one template via script manager lookup semantics."""
        if self.script_manager is None:
            return None
        return self.script_manager.find_template(reference)

    def find_templates(self, selector=None) -> list[Any]:
        """Find all templates matching selector via script manager."""
        if self.script_manager is None:
            return []
        return self.script_manager.find_templates(selector=selector)

    @classmethod
    def from_script_data(
        cls,
        *,
        script_data: dict[str, Any],
        compiler: StoryCompiler38 | None = None,
        domain: Any | None = None,
        templates: Any | None = None,
        assets: Any | None = None,
        resources: Any | None = None,
    ) -> "World38":
        compiler = compiler or StoryCompiler38()
        bundle = compiler.compile(script_data)
        return cls(
            label=script_data.get("label") or "story38_world",
            bundle=bundle,
            domain=domain,
            templates=templates,
            assets=assets,
            resources=resources,
        )
