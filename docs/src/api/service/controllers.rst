.. currentmodule:: tangl.service

tangl.service manager
=====================

The canonical service surface is the explicit :class:`tangl.service.ServiceManager`.

Its public methods are the source of truth for service behavior. See
:doc:`operations` for the generated method catalog derived from
:func:`tangl.service.service_method` metadata.

.. rubric:: Related design docs

- :doc:`../../design/service/SERVICE_DESIGN`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`
- :doc:`../../notes/migration/cutover-log`

Manager
-------

.. autoclass:: tangl.service.ServiceManager
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ServiceSession
   :members:
   :member-order: bysource
