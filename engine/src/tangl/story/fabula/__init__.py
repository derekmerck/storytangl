"""
Fabula runtime exports and helpers.

The fabula is the latent, unrealized space of all possible stories. The
:class:`~tangl.story.fabula.world.World` class manages story templates, custom
classes, assets, and resources derived from a compiled bundle.

Typical usage
-------------

.. code-block:: python

    from tangl.story.fabula.world_loader import build_world_from_bundle

    world, graphs = build_world_from_bundle("demo_world")
    graph = graphs["demo_story"]
    start_node = graph.get(graph.initial_cursor_id)

Extension points
----------------

- Register new :class:`tangl.compilers.loaders.base.ScriptLoader` instances via
  :func:`tangl.compilers.loaders.registry.register_loader`.
- Describe bundle layouts with :class:`tangl.compilers.world_config.WorldConfig`
  and :class:`tangl.compilers.world_config.ScriptConfig` entries.
"""

from .world import World
from .world_bundle import WorldBundle
from .world_loader import WorldLoader, build_world_from_bundle
from .world_manifest import WorldManifest
