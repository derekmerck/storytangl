from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Iterable

from .compiler import StoryCompiler, StoryTemplateBundle
from .materializer import StoryMaterializer
from .script_manager import ScriptManager
from .types import InitMode, StoryInitResult


@dataclass(slots=True)
class World:
    """World(label: str, bundle: StoryTemplateBundle)

    Primary story entry point over a compiled template bundle.

    Why
    ----
    ``World`` binds a reusable compiled story bundle to optional domain,
    template, asset, and resource facets so applications can create runtime
    stories without manually assembling materializer dependencies each time.

    Key Features
    ------------
    * Owns the compiled bundle and default :class:`ScriptManager`.
    * Delegates runtime graph creation to :class:`StoryMaterializer`.
    * Exposes optional authority and template-scope hooks from attached world
      facets.
    * Keeps a lightweight process-local instance registry for convenience
      lookup.

    API
    ---
    - :meth:`create_story` materializes one runtime graph from the compiled
      bundle.
    - :meth:`get_authorities` exposes optional world/domain dispatch
      registries.
    - :meth:`get_template_scope_groups` returns extra template groups available
      at runtime.
    - :meth:`find_template` and :meth:`find_templates` delegate template lookup
      to the configured :class:`ScriptManager`.
    - :meth:`get_instance`, :meth:`all_instances`, and :meth:`clear_instances`
      manage the lightweight process-local world registry.
    """

    label: str
    bundle: StoryTemplateBundle
    script_manager: ScriptManager | None = None
    domain: Any | None = None
    templates: Any | None = None
    assets: Any | None = None
    resources: Any | None = None
    _instances: ClassVar[dict[str, "World"]] = {}

    def __post_init__(self) -> None:
        if self.templates is None:
            self.templates = self.bundle.template_registry
        if self.script_manager is None:
            self.script_manager = ScriptManager(
                template_registry=self.bundle.template_registry,
                world_scope_provider=self._world_template_scope_groups,
            )
        self.__class__._instances[self.label] = self

    @property
    def metadata(self) -> dict[str, Any]:
        return self.bundle.metadata

    def create_story(
        self,
        story_label: str,
        *,
        init_mode: InitMode = InitMode.EAGER,
    ) -> StoryInitResult:
        materializer = StoryMaterializer()
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
        compiler: StoryCompiler | None = None,
        domain: Any | None = None,
        templates: Any | None = None,
        assets: Any | None = None,
        resources: Any | None = None,
    ) -> "World":
        compiler = compiler or StoryCompiler()
        bundle = compiler.compile(script_data)
        return cls(
            label=script_data.get("label") or "story_world",
            bundle=bundle,
            domain=domain,
            templates=templates,
            assets=assets,
            resources=resources,
        )

    @classmethod
    def get_instance(cls, label: str) -> "World | None":
        return cls._instances.get(label)

    @classmethod
    def all_instances(cls) -> list["World"]:
        return list(cls._instances.values())

    @classmethod
    def clear_instances(cls) -> None:
        cls._instances.clear()
