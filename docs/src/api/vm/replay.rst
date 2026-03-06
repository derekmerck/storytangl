.. currentmodule:: tangl.vm

tangl.vm.replay
===============

Replay records and engines used to persist, diff, and roll back runtime state.

.. rubric:: Related design docs

- :doc:`../../design/traversal/NAV_DESIGN`

.. rubric:: Related notes

- :doc:`../../notes/migration/cutover-log`

Replay artifacts
----------------

.. autoclass:: tangl.vm.replay.patch.Event
.. autoclass:: tangl.vm.replay.patch.Patch
.. autoclass:: tangl.vm.replay.records.StepRecord
.. autoclass:: tangl.vm.replay.records.CheckpointRecord
.. autoclass:: tangl.vm.replay.records.RollbackRecord

Replay engines
--------------

.. autoclass:: tangl.vm.replay.contracts.ReplayEngine
.. autoclass:: tangl.vm.replay.engine.DiffReplayEngine
