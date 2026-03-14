.. currentmodule:: tangl.service

tangl.service orchestration
===========================

Gateway and endpoint abstractions that execute controller logic against a
hydrated runtime context.

Use :doc:`operations` for the generated service-operation catalog. This page
documents the gateway, orchestrator, and endpoint metadata types that power
that catalog.

.. rubric:: Related design docs

- :doc:`../../design/service/SERVICE_DESIGN`

.. rubric:: Related notes

- :doc:`../../notes/migration/v38-phase1-review`

Orchestration
-------------

.. autoclass:: tangl.service.Orchestrator
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ApiEndpoint
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.EndpointPolicy
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ExecuteOptions
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.ServiceGateway
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.GatewayExecuteOptions
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.GatewayRequest
   :members:
   :member-order: bysource

.. autoclass:: tangl.service.GatewayRestAdapter
   :members:
   :member-order: bysource

.. autofunction:: tangl.service.build_service_gateway
