from .concepts import Actor, Location, Role, Setting
from .episode import Action, Block, Scene
from .fabula import (
    GraphInitializationError,
    InitMode,
    InitReport,
    ResolutionError,
    ResolutionFailureReason,
    ScriptManager,
    ScriptManager38,
    StoryCompiler,
    StoryCompiler38,
    StoryInitResult,
    StoryMaterializer,
    StoryMaterializer38,
    StoryTemplateBundle,
    UnresolvedDependency,
    WorldAssetsFacet,
    WorldDomainFacet,
    WorldResourcesFacet,
    WorldTemplatesFacet,
    World,
    World38,
)
from .story_graph import StoryGraph, StoryGraph38
from .dispatch import on_journal, story_dispatch
from .fragments import ChoiceFragment, ContentFragment, Fragment, MediaFragment
from .ctx import StoryRuntimeCtx

# Register story-level journal handlers.
from . import system_handlers  # noqa: F401

# Legacy compatibility alias retained during naming cutover.
LegacyStoryGraph = StoryGraph38

__all__ = [
    "Action",
    "Actor",
    "Block",
    "ChoiceFragment",
    "ContentFragment",
    "Fragment",
    "GraphInitializationError",
    "InitMode",
    "InitReport",
    "Location",
    "ResolutionError",
    "ResolutionFailureReason",
    "ScriptManager",
    "Role",
    "ScriptManager38",
    "Scene",
    "Setting",
    "StoryRuntimeCtx",
    "StoryCompiler",
    "StoryCompiler38",
    "StoryGraph",
    "StoryGraph38",
    "StoryInitResult",
    "StoryMaterializer",
    "StoryMaterializer38",
    "StoryTemplateBundle",
    "UnresolvedDependency",
    "WorldAssetsFacet",
    "WorldDomainFacet",
    "WorldResourcesFacet",
    "WorldTemplatesFacet",
    "World",
    "World38",
    "LegacyStoryGraph",
    "on_journal",
    "story_dispatch",
    "MediaFragment",
]
