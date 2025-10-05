.. currentmodule:: tangl.vm

tangl.vm
========
.. automodule:: tangl.vm

.. _vm-resolver:

Graph Resolution
----------------
.. autoclass:: tangl.vm.Context
.. autoclass:: tangl.vm.ResolutionPhase
.. autoclass:: tangl.vm.Frame
.. autoclass:: tangl.vm.Ledger

.. _vm-planning:

Planning
---------
.. autoclass:: tangl.vm.Requirement
.. autoclass:: tangl.vm.Dependency
.. autoclass:: tangl.vm.Affordance
.. autoclass:: tangl.vm.Provisioner
.. autoclass:: tangl.vm.Offer
.. autoclass:: tangl.vm.planning.BuildReceipt
.. autoclass:: tangl.vm.planning.PlanningReceipt

.. _vm-replay:

Event Sourced Replay
--------------------
.. autoclass:: tangl.vm.EventType
.. autoclass:: tangl.vm.Event
.. autoclass:: tangl.vm.Patch
.. autoclass:: tangl.vm.replay.WatchedEntityProxy
.. autoclass:: tangl.vm.replay.EventWatcher
