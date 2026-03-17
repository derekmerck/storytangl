.. currentmodule:: tangl.story

tangl.story.fabula
==================

Compilation and materialization APIs for turning authored scripts into runtime
story graphs.

.. rubric:: Related design docs

- :doc:`../../design/story/compilers`
- :doc:`../../design/planning/TEMPLATE_SCOPE`
- :doc:`../../design/traversal/ENTRY_RESOLUTION`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`
- :doc:`../../notes/audits/vm38-doc-audit`
- :doc:`../../notes/migration/script_manager_facade_migration`

Compilation
-----------

.. autoclass:: tangl.story.fabula.compiler.StoryCompiler
.. autoclass:: tangl.story.fabula.compiler.StoryTemplateBundle

Materialization
---------------

.. autoclass:: tangl.story.fabula.materializer.StoryMaterializer
.. autoclass:: tangl.story.fabula.world.World
.. autoclass:: tangl.story.fabula.script_manager.ScriptManager

Init result types
-----------------

.. autoclass:: tangl.story.fabula.types.InitMode
.. autoclass:: tangl.story.fabula.types.InitReport
.. autoclass:: tangl.story.fabula.types.StoryInitResult
.. autoclass:: tangl.story.fabula.types.GraphInitializationError
.. autoclass:: tangl.story.fabula.types.ResolutionError

Selected methods
----------------

.. automethod:: tangl.story.fabula.compiler.StoryCompiler.compile
.. automethod:: tangl.story.fabula.materializer.StoryMaterializer.create_story
