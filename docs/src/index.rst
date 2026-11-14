StoryTangl
==========

StoryTangl models interactive narrative as a graph of interdependent
possibilities that collapses into a specific story through traversal. It is a
research platform and reference implementation for studying narrative
structure, not a production game engine.

Where to start
--------------

1. :doc:`design/story/philosophy` explains why the system is shaped as it is.
2. :doc:`design/glossary` maps the vocabulary onto the implementation.
3. `ARCHITECTURE.md <https://github.com/derekmerck/storytangl/blob/main/ARCHITECTURE.md>`_
   is the cross-layer type map and its invariants.
4. The `world catalog <https://github.com/derekmerck/storytangl/blob/main/worlds/README.md>`_
   lists the runnable examples, one idea at a time.

The rest of the documentation is reference material for the ``tangl.core``,
``tangl.vm``, ``tangl.story`` and ``tangl.service`` layers and the packages
around them.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/index
   mechanics/index
   design/index
   world-designs/index
   notes/index
   contrib/index
