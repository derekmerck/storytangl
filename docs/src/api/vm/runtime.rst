.. currentmodule:: tangl.vm

tangl.vm.runtime
================

Phase-driven execution state used to advance a story graph one choice at a
time.

.. storytangl-topic::
   :topics: phase_ctx, frame, ledger, resolution_phase
   :facets: api
   :relation: documents

.. rubric:: Related design docs

- :doc:`../../design/traversal/NAV_DESIGN`
- :doc:`../../design/traversal/ENTRY_RESOLUTION`

.. rubric:: Related notes

- :doc:`../../notes/migration/v38-phase1-review`

Core runtime types
------------------

.. autoclass:: tangl.vm.ResolutionPhase
.. autoclass:: tangl.vm.runtime.frame.Frame
.. autoclass:: tangl.vm.runtime.ledger.Ledger
.. autoclass:: tangl.vm.VmPhaseCtx
