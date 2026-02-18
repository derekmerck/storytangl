from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compiler import StoryCompiler38, StoryTemplateBundle
from .materializer import StoryMaterializer38
from .types import InitMode, StoryInitResult


@dataclass(slots=True)
class World38:
    """Story38 world entrypoint over compiled template bundles."""

    label: str
    bundle: StoryTemplateBundle

    @property
    def metadata(self) -> dict[str, Any]:
        return self.bundle.metadata

    def create_story(self, story_label: str, *, init_mode: InitMode = InitMode.FULLY_SPECIFIED) -> StoryInitResult:
        materializer = StoryMaterializer38()
        return materializer.create_story(
            bundle=self.bundle,
            story_label=story_label,
            init_mode=init_mode,
            world=self,
        )

    def get_authorities(self) -> list[object]:
        """Return optional author/world behavior registries."""
        return []

    @classmethod
    def from_script_data(
        cls,
        *,
        script_data: dict[str, Any],
        compiler: StoryCompiler38 | None = None,
    ) -> "World38":
        compiler = compiler or StoryCompiler38()
        bundle = compiler.compile(script_data)
        return cls(label=script_data.get("label") or "story38_world", bundle=bundle)
