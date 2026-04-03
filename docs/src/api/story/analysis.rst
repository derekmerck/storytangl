.. currentmodule:: tangl.story

tangl.story.analysis
====================

Projection and rendering helpers for inspecting StoryTangl graphs as explicit
graph views.

These helpers are observational only. They do not participate in traversal or
become a second source of truth.

.. rubric:: Related design docs

- :doc:`../../design/story/philosophy`
- :doc:`../../design/traversal/NAV_DESIGN`

Projected graph model
---------------------

.. autoclass:: tangl.story.analysis.ProjectedNode

.. autoclass:: tangl.story.analysis.ProjectedEdge

.. autoclass:: tangl.story.analysis.ProjectedGroup

.. autoclass:: tangl.story.analysis.ProjectedGraph

Projection APIs
---------------

.. autofunction:: tangl.story.analysis.project_story_graph

.. autofunction:: tangl.story.analysis.project_world_graph

.. autofunction:: tangl.story.analysis.structural_selector

.. autofunction:: tangl.story.analysis.episode_only_selector

.. autofunction:: tangl.story.analysis.episode_plus_concepts_selector

Processors
----------

.. autofunction:: tangl.story.analysis.cluster_by_scene

.. autofunction:: tangl.story.analysis.attach_media_preview

.. autofunction:: tangl.story.analysis.annotate_runtime

.. autofunction:: tangl.story.analysis.focus_runtime_window

.. autofunction:: tangl.story.analysis.collapse_linear_chains

.. autofunction:: tangl.story.analysis.mark_runtime_styles

Rendering
---------

.. autofunction:: tangl.story.analysis.to_dot

.. autofunction:: tangl.story.analysis.render_dot

Compatibility wrappers
----------------------

.. autofunction:: tangl.story.analysis.build_script_report

.. autofunction:: tangl.story.analysis.render_basic_svg
