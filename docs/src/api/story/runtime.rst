.. currentmodule:: tangl.story

tangl.story.runtime
===================

Runtime graph and handler surfaces used during namespace gathering, choice
preview, and journaling.

.. rubric:: Related design docs

- :doc:`../../design/story/philosophy`
- :doc:`../../design/story/JOURNAL_COMPOSE_CONTRACT`
- :doc:`../../design/traversal/NAV_DESIGN`
- :doc:`analysis`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`

Runtime graph
-------------

.. automodule:: tangl.story.story_graph

.. autoclass:: tangl.story.story_graph.StoryGraph

Runtime context
---------------

Story runtime helpers use the VM's canonical phase context directly.

.. autoclass:: tangl.vm.runtime.frame.PhaseCtx

Journal handlers
----------------

.. automodule:: tangl.story.system_handlers
