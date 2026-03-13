.. currentmodule:: tangl.rest

tangl.rest
==========

The REST server is the transport-facing wrapper around
:class:`tangl.service.ServiceGateway`.

- :mod:`tangl.rest.app` is the outer FastAPI application.
- :mod:`tangl.rest.api_server` is mounted at ``/api/v2``.
- The mounted API's OpenAPI document is served at ``/api/v2/openapi.json``.
- Use :doc:`../service/operations` for gateway/controller semantics; use this
  page for HTTP route inventory and app bootstrap details.

.. rubric:: Related design docs

- :doc:`../../design/service/SERVICE_DESIGN`

Routes
------

.. rest-route-catalog::

Application bootstrap
---------------------

.. automodule:: tangl.rest.app
   :members:
   :member-order: bysource

.. automodule:: tangl.rest.api_server
   :members:
   :member-order: bysource

.. automodule:: tangl.rest.dependencies_gateway
   :members:
   :member-order: bysource
