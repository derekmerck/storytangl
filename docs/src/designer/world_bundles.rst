World bundles and default formats
=================================

StoryTangl ships with a default "happy path" for authors who want to bundle a world
without writing custom loader code. This page documents the default layout, the
Simple Single File format, and the Simple Tree format so content authors can produce
compatible bundles quickly.

Default bundle layout
---------------------

A minimal bundle looks like this::

   myworld/
     world.yaml             # manifest (required)
     content/               # default content root (optional)
       demo.yaml            # simple_single_file script
     media/                 # media root(s)
     domain/                # optional domain code

``world.yaml`` is the entry point for the compiler. It declares domain hooks,
media settings, and the scripts contained in the bundle.

Simple Single File format
-------------------------

The "Simple Single File" format keeps an entire script in one YAML document. A
minimal story file might look like:

.. code-block:: yaml

   id: demo
   title: "Demo Story"
   entry: "start"

   actors:
     hero: { name: "Hero" }

   locations:
     town: { name: "Town" }

   blocks:
     start:
       text: "You wake up."
       choices:
         - to: street
           text: "Go outside"
     street:
       text: "You are in the street."

The corresponding ``world.yaml`` references this file via the builtin loader:

.. code-block:: yaml

   id: demo_world
   title: "Demo World"
   domain:
     module: tangl.demo.domain
     setup: tangl.demo.domain:register_domain

   scripts:
     - id: demo
       label: "Demo Story"
       loader: "builtin:simple_single_file"
       source:
         type: file
         path: content/demo.yaml
         entry_label: "start"

Simple Tree format
------------------

The "Simple Tree" format organizes YAML fragments by category. A bundle declares
it with the ``builtin:simple_tree`` loader and points to a directory root. Within
that root you can provide subdirectories like ``actors/`` or ``scenes/`` using the
conventions described in :mod:`tangl.compilers.world_config`. Each YAML fragment is
merged into a :class:`tangl.story.ir.StoryScript` when the world is loaded.

These defaults let authors start with a single YAML file and grow toward a more
structured tree without changing fabula runtime code.

Extension points
----------------

The builtin loaders are intentionally small so you can swap in your own
formats. Register a custom :class:`tangl.compilers.loaders.base.ScriptLoader`
with :func:`tangl.compilers.loaders.registry.register_loader` and reference it
from a script entry's ``loader`` field. If your bundle layout differs from the
defaults, extend :class:`tangl.compilers.world_config.WorldConfig` or
:class:`tangl.compilers.world_config.ScriptConfig` to capture the additional
metadata your loader needs.
