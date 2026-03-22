"""
.. currentmodule:: tangl.story.fabula

Story world construction pipeline: script -> bundle -> runtime graph.

Conceptual layers
-----------------

1. Compilation

   - :class:`StoryCompiler` validates authored script data and emits a
     :class:`StoryTemplateBundle`.

2. Materialization

   - :class:`StoryMaterializer` applies story topology, eager prelink policy,
     and runtime materialization hooks over graphs created by
     :class:`~tangl.story.World`.

3. World assembly and entry point

   - :class:`WorldBuilder` assembles world adjunct providers around a compiled
     :class:`StoryTemplateBundle`.
   - :class:`World` is the singleton story authority over runtime graph
     creation and exposes :meth:`World.create_story`.

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
Runtime graph creation belongs to :class:`World`; story-specific wiring remains
factored into :class:`StoryMaterializer`.
"""

from .compiler import StoryCompiler, StoryTemplateBundle
from .builder import WorldBuilder
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
    "WorldBuilder",
    "WorldDomainFacet",
    "WorldResourcesFacet",
    "WorldTemplatesFacet",
    "World",
]
