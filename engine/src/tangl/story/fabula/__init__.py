"""
.. currentmodule:: tangl.story.fabula

Story world construction pipeline: script -> bundle -> runtime graph.

Conceptual layers
-----------------

1. Compilation

   - :class:`StoryCompiler` validates authored script data and emits a
     :class:`StoryTemplateBundle`.

2. Materialization

   - :class:`StoryMaterializer` walks the compiled template registry and
     instantiates concrete runtime entities inside a :class:`~tangl.story.StoryGraph`.

3. World entry point

   - :class:`World` packages a compiled bundle with optional world facets and
     exposes :meth:`World.create_story`.

4. Runtime script lookup

   - :class:`ScriptManager` resolves lineage-aware template scope groups for
     runtime provisioning.

5. Init result types

   - :class:`InitMode`, :class:`InitReport`, and :class:`StoryInitResult`
     describe materialization depth, diagnostics, and final outputs.

Design intent
-------------
Compilation is intentionally separate from materialization so one validated
bundle can produce many independent story graphs without reparsing script data.
"""

from .compiler import StoryCompiler, StoryTemplateBundle
from .materializer import StoryMaterializer
from .script_manager import ScriptManager
from .types import (
    AuthoredRef,
    CompileIssue,
    CompileSeverity,
    GraphInitializationError,
    InitMode,
    InitReport,
    ResolutionError,
    ResolutionFailureReason,
    StoryInitResult,
    UnresolvedDependency,
    WorldAssetsFacet,
    WorldDomainFacet,
    WorldResourcesFacet,
    WorldTemplatesFacet,
)
from .world import World

__all__ = [
    "AuthoredRef",
    "CompileIssue",
    "CompileSeverity",
    "GraphInitializationError",
    "InitMode",
    "InitReport",
    "ResolutionError",
    "ResolutionFailureReason",
    "ScriptManager",
    "StoryCompiler",
    "StoryInitResult",
    "StoryMaterializer",
    "StoryTemplateBundle",
    "UnresolvedDependency",
    "WorldAssetsFacet",
    "WorldDomainFacet",
    "WorldResourcesFacet",
    "WorldTemplatesFacet",
    "World",
]
