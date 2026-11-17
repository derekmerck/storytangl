Presentation API
================

Domain-neutral interaction intent, display values, and advisory rendering
hints. These values describe a client-facing syntax; they do not authorize
actions or own transport. Projected-state values and transient guidance are
also presentation-owned; Service envelopes carry them without defining them.

The package design notes below are kept beside the code in
``engine/src/tangl/presentation`` and included here unchanged. They are the long form of
the package docstring: purpose, contracts and status. They connect the conceptual
and planning pages under *Design* to the reference that follows.

.. toctree::
   :maxdepth: 1
   :caption: Package design notes

   PRESENTATION_DESIGN

.. automodule:: tangl.presentation.intent
   :members:

.. automodule:: tangl.presentation.values
   :members:

.. automodule:: tangl.presentation.hints
   :members:

.. automodule:: tangl.presentation.events
   :members:

.. automodule:: tangl.presentation.projection
   :members:

.. automodule:: tangl.presentation.dispatch
   :members:
