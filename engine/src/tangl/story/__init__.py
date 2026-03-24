"""
.. currentmodule:: tangl.story

Story-domain layer for authored narrative graphs, runtime story instances, and
journal-ready output.

Conceptual layers
-----------------

1. Fabula

   - :class:`StoryCompiler` validates and normalizes authored scripts into a
     compiled template bundle.
   - :class:`WorldBuilder` assembles world adjuncts around a compiled bundle.
   - :class:`StoryMaterializer` wires story-specific topology and runtime hooks
     as a helper behind :class:`World`.
   - :class:`World` is the singleton story authority and main external entry
     point for creating story runs.
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

   - :class:`StoryGraph` carries story locals, template lineage, and a
     compatibility world alias over its bound factory for runtime resolution.
   - :class:`ContentFragment`, :class:`ChoiceFragment`, and
     :class:`MediaFragment` are re-exported journal output types.

5. Dispatch

   - :obj:`story_dispatch` is the shared story behavior registry.
   - :func:`on_gather_ns` registers story-level namespace contribution handlers.
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
    AuthoredRef,
    CompileIssue,
    CompileSeverity,
    GraphInitializationError,
    InitMode,
    InitReport,
    ResolutionError,
    ResolutionFailureReason,
    StoryCompiler,
    StoryInitResult,
    StoryMaterializer,
    UnresolvedDependency,
    WorldBuilder,
    World,
)
from .analysis import (
    ProjectedEdge,
    ProjectedGraph,
    ProjectedGroup,
    ProjectedNode,
    ScriptGraphEdge,
    ScriptGraphNode,
    ScriptGraphReport,
    attach_media_preview,
    build_script_report,
    cluster_by_scene,
    episode_only_selector,
    episode_plus_concepts_selector,
    mark_node_styles,
    project_story_graph,
    project_world_graph,
    projected_graph_to_dict,
    render_basic_svg,
    render_dot,
    report_to_dict,
    structural_selector,
    to_dot,
)
from .story_graph import StoryGraph
from .dispatch import on_compose_journal, on_gather_ns, on_journal, story_dispatch
from .fragments import ChoiceFragment, ContentFragment, MediaFragment

# Register story-level journal handlers.
from . import system_handlers  # noqa: F401

__all__ = [
    "Action",
    "Actor",
    "AuthoredRef",
    "Block",
    "ProjectedEdge",
    "ProjectedGraph",
    "ProjectedGroup",
    "ProjectedNode",
    "ScriptGraphEdge",
    "ScriptGraphNode",
    "ScriptGraphReport",
    "ChoiceFragment",
    "CompileIssue",
    "CompileSeverity",
    "ContentFragment",
    "EntityKnowledge",
    "GraphInitializationError",
    "HasNarratorKnowledge",
    "InitMode",
    "InitReport",
    "Location",
    "MenuBlock",
    "ResolutionError",
    "ResolutionFailureReason",
    "Role",
    "Scene",
    "Setting",
    "StoryCompiler",
    "StoryGraph",
    "StoryInitResult",
    "StoryMaterializer",
    "UnresolvedDependency",
    "WorldBuilder",
    "World",
    "attach_media_preview",
    "build_script_report",
    "cluster_by_scene",
    "episode_only_selector",
    "episode_plus_concepts_selector",
    "get_narrator_key",
    "mark_node_styles",
    "on_compose_journal",
    "on_gather_ns",
    "on_journal",
    "project_story_graph",
    "project_world_graph",
    "projected_graph_to_dict",
    "render_basic_svg",
    "render_dot",
    "report_to_dict",
    "structural_selector",
    "story_dispatch",
    "to_dot",
    "MediaFragment",
]
