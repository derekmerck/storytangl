"""Developer topic reference tools for StoryTangl contributors.

Why
---
``tangl.devref`` builds a rebuildable local index over StoryTangl's authored
docs, code symbols, tests, demos, and contributor guidance. The index is
optimized for narrow, topic-oriented retrieval rather than whole-repo dumps.

Key Features
------------
* **Rebuildable** - :func:`build_index` regenerates a SQLite index from source.
* **Topic-oriented** - :func:`search_topics` and :func:`get_topic_map` rank
  artifacts by curated developer topics instead of embeddings.
* **Agent-friendly** - :func:`build_context_pack` returns compact, ordered
  context bundles for downstream tools and MCP consumers.

API
---
- :func:`build_index` - Build or refresh the local SQLite index.
- :func:`search_topics` - Search topics and ranked artifacts.
- :func:`get_topic_map` - Show one topic with related topics and artifacts.
- :func:`build_context_pack` - Assemble a compact context pack for agents.
"""

from .builder import build_index
from .models import (
    ArtifactHit,
    BuildReport,
    ContextPack,
    ContextPackItem,
    SearchResponse,
    TopicDefinition,
    TopicHit,
    TopicMap,
)
from .query import build_context_pack, get_topic_map, search_topics
from .topics import load_topics

__all__ = [
    "ArtifactHit",
    "BuildReport",
    "ContextPack",
    "ContextPackItem",
    "SearchResponse",
    "TopicDefinition",
    "TopicHit",
    "TopicMap",
    "build_context_pack",
    "build_index",
    "get_topic_map",
    "load_topics",
    "search_topics",
]
