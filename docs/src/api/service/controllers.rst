.. currentmodule:: tangl.service

tangl.service.controllers
=========================

Controller entrypoints exposed through the service orchestrator.

The controller classes below are the source of truth for endpoint docstrings.
See :doc:`operations` for the generated gateway-facing catalog derived from
their :class:`tangl.service.ApiEndpoint` metadata.

.. rubric:: Related design docs

- :doc:`../../design/service/SERVICE_DESIGN`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`
- :doc:`../../notes/migration/cutover-log`

Controllers
-----------

.. autoclass:: tangl.service.controllers.runtime_controller.RuntimeController
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.controllers.world_controller.WorldController
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.controllers.user_controller.UserController
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.controllers.system_controller.SystemController
   :members:
   :member-order: bysource
