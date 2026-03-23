.. currentmodule:: tangl.service

tangl.service bootstrap and metadata
====================================

Service bootstrapping and bounded metadata for the manager-first API.

Use :doc:`operations` for the generated service-method catalog. This page
documents the bootstrap helper and metadata types that describe the public
service surface.

.. rubric:: Related design docs

- :doc:`../../design/service/SERVICE_DESIGN`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`
- :doc:`../../notes/migration/v38-phase1-review`

Bootstrap
---------

.. autofunction:: tangl.service.build_service_manager

Metadata
--------

.. autofunction:: tangl.service.service_method

.. autoclass:: tangl.service.ServiceMethodSpec
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ServiceAccess
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ServiceContext
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ServiceWriteback
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.BlockingMode
   :members:
   :member-order: bysource

Support types
-------------

.. autoclass:: tangl.service.UserAuthInfo
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.WorldRegistry
   :members:
   :member-order: bysource
