"""
.. currentmodule:: tangl.story

Story-domain layer for authored narrative graphs, runtime story instances, and
journal-ready output.

Conceptual layers
-----------------

1. Fabula

   - :class:`StoryCompiler` validates and normalizes authored scripts into a
     :class:`StoryTemplateBundle`.
   - :class:`StoryMaterializer` instantiates story graphs from compiled
     templates.
   - :class:`World` is the main external entry point for creating story runs.
   - :class:`ScriptManager` resolves template lookups across lineage-aware
     scope groups.

2. Episode vocabulary

   - :class:`Block` is the primary interactive cursor node.
   - :class:`Scene` groups blocks and maintains container traversal contracts.
   - :class:`Action` links choices and continuation edges between blocks.

3. Story concepts

   - :class:`Actor` and :class:`Location` are named providers published into
     render namespaces.
   - :class:`Role` and :class:`Setting` are story-specific dependency edges
     that bind those providers into scene and block scopes.
   - :class:`EntityKnowledge` and :class:`HasNarratorKnowledge` carry
     narrator-facing epistemic bookkeeping directly on story concept carriers.

4. Runtime graph and journal output

   - :class:`StoryGraph` carries story locals, template lineage, and world
     references for runtime resolution.
   - :class:`StoryRuntimeCtx` defines the context accessors expected by story
     runtime helpers.
   - :class:`Fragment`, :class:`ContentFragment`, :class:`ChoiceFragment`, and
     :class:`MediaFragment` represent journal output.

5. Dispatch

   - :obj:`story_dispatch` is the shared story behavior registry.
   - :func:`on_journal` registers raw JOURNAL-phase handlers.
   - :func:`on_compose_journal` registers post-merge JOURNAL composition handlers.

Design intent
-------------
``tangl.story`` owns narrative policy: the story-facing entity vocabulary,
script-to-template compilation, and JOURNAL rendering. Traversal and
provisioning mechanisms remain in :mod:`tangl.vm`.
"""

from .concepts import (
    Actor,
    EntityKnowledge,
    HasNarratorKnowledge,
    Location,
    Role,
    Setting,
    get_narrator_key,
)
from .episode import Action, Block, MenuBlock, Scene
from .fabula import (
    GraphInitializationError,
    InitMode,
    InitReport,
    ResolutionError,
    ResolutionFailureReason,
    ScriptManager,
    StoryCompiler,
    StoryInitResult,
    StoryMaterializer,
    StoryTemplateBundle,
    UnresolvedDependency,
    WorldAssetsFacet,
    WorldDomainFacet,
    WorldResourcesFacet,
    WorldTemplatesFacet,
    World,
)
from .story_graph import StoryGraph
from .dispatch import on_compose_journal, on_journal, story_dispatch
from .fragments import ChoiceFragment, ContentFragment, Fragment, MediaFragment
from .ctx import StoryRuntimeCtx

# Register story-level journal handlers.
from . import system_handlers  # noqa: F401

__all__ = [
    "Action",
    "Actor",
    "Block",
    "ChoiceFragment",
    "ContentFragment",
    "EntityKnowledge",
    "Fragment",
    "GraphInitializationError",
    "HasNarratorKnowledge",
    "InitMode",
    "InitReport",
    "Location",
    "MenuBlock",
    "ResolutionError",
    "ResolutionFailureReason",
    "ScriptManager",
    "Role",
    "Scene",
    "Setting",
    "StoryRuntimeCtx",
    "StoryCompiler",
    "StoryGraph",
    "StoryInitResult",
    "StoryMaterializer",
    "StoryTemplateBundle",
    "UnresolvedDependency",
    "WorldAssetsFacet",
    "WorldDomainFacet",
    "WorldResourcesFacet",
    "WorldTemplatesFacet",
    "World",
    "get_narrator_key",
    "on_compose_journal",
    "on_journal",
    "story_dispatch",
    "MediaFragment",
]
